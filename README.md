# Uni Deadline Tracker API

[![CI](https://github.com/macroer16/uni-deadline-tracker-api/actions/workflows/ci.yml/badge.svg)](https://github.com/macroer16/uni-deadline-tracker-api/actions/workflows/ci.yml)

A REST API for keeping track of university coursework deadlines. You add modules and deadlines, it tells you what's overdue or due soon, and it gives you a private calendar link so every deadline shows up in Google, Outlook or Apple Calendar with a reminder the day before.

Built with Python and FastAPI, tested against SQLite and real PostgreSQL, packaged with Docker, with AWS infrastructure written in Terraform (Lambda, API Gateway, CloudWatch alarms, a budget alert and keyless GitHub deploys).

![Interactive API documentation showing the auth, modules, deadlines, calendar and health endpoints](docs/api-docs.png)

## Why I built it

In my first term I had deadlines spread across several modules, each announced in a different place. I wanted one place that answers "what do I need to do next?", plus deadlines that appear in the calendar I already check. It's also the project where I practise building a back end properly: authentication, data isolation between users, tests, containers and infrastructure as code.

## What it does

| Feature | How |
|---|---|
| Accounts | Register and log in. Passwords are hashed with **Argon2id**, and logins return a **JWT** that expires after 30 minutes. |
| Modules | Create, rename and delete modules. Codes are unique per user. Deleting a module keeps its deadlines. |
| Deadlines | Full create, read, update and delete, with title, due time, weight (%), status (`todo`, `in_progress`, `submitted`) and notes. Filter by status or module. |
| What's urgent | `GET /deadlines/upcoming` lists everything not submitted that is overdue or due soon, labelled `overdue`, `due_soon` (within 48 h), `this_week` or `later`. |
| Calendar feed | `POST /me/calendar-link` creates a private `.ics` link you can subscribe to. Each deadline becomes a calendar event with a reminder the day before. |
| Account deletion | `DELETE /me` removes the account and all its data. |
| Health checks | `/health` checks the database; `/health/live` only checks the app is running. |

Interactive docs are at `/docs` when it's running.

## Security decisions

- **Users can only ever reach their own data.** Every query is filtered by the signed-in user. Asking for someone else's deadline returns `404`, not `403`, so you can't even tell it exists. There are dedicated tests for this (`tests/test_isolation.py`).
- **Logins don't leak which emails exist.** A wrong password and an unknown email get the same response and take the same time, because unknown emails are checked against a dummy hash.
- **JWTs are verified strictly.** The algorithm is pinned to HS256, so `alg: none` and tokens signed with another key are rejected (both tested). Tokens expire, and a deleted user's token stops working.
- **The calendar link is a secret, stored as a hash.** Calendar apps can't send a login token, so the link contains a long random token instead. Only its SHA-256 hash is stored, so a database leak wouldn't expose working links. Rotating the link breaks the old one.
- **Times are always UTC with a timezone.** A due date without a timezone, like `2026-11-01T12:00`, is rejected as ambiguous. A custom SQLAlchemy type stores everything in UTC, because SQLite would otherwise lose the timezone.
- **No secrets in code or Terraform.** Locally they come from `.env` (git-ignored). In AWS they're encrypted in SSM Parameter Store and set by hand, so they never appear in Terraform state.
- **The container runs as a non-root user**, which CI checks.

## Architecture on AWS

```
                  HTTPS                                    SSM Parameter Store
 Client ──▶ API Gateway (HTTP API) ──▶ Lambda (container) ──▶ DATABASE_URL, JWT_SECRET
            rate limit 10 req/s        FastAPI via Lambda
            access logs                Web Adapter            ──▶ PostgreSQL (Supabase or Neon, free tier)
                                            │
                     CloudWatch alarms ◀────┘──▶ SNS ──▶ email
                     AWS Budget ($5) ──────────────────▶ email

 GitHub Actions ──OIDC──▶ IAM deploy role (main branch only) ──▶ push to ECR, update Lambda
```

The same Docker image runs locally, in Docker Compose and on Lambda. The [AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter) translates Lambda events into normal HTTP requests, so the app needs no Lambda-specific code.

I chose Lambda over always-on hosting like ECS or App Runner because a personal API is idle most of the time, and Lambda costs nothing while idle.

### Estimated monthly cost

For personal use (a few thousand requests a month) in `eu-west-2`:

| Service | Cost |
|---|---|
| Lambda | Free (always-free tier: 1M requests and 400,000 GB-seconds a month) |
| API Gateway HTTP API | Free for the first 12 months (1M calls a month), then about $1 per million requests |
| ECR (around 150 MB of images, 10 kept) | Free for the first 12 months (500 MB), then about $0.02 |
| CloudWatch logs and 2 alarms, SNS email, SSM standard parameters, 1 budget | Free tier |
| PostgreSQL (Supabase or Neon) | Free tier |
| **Total** | **About $0 to $0.05 a month** |

The $5 budget alert and the API Gateway rate limit are there in case that estimate turns out to be wrong.

## Run it locally

You need Python 3.12 or newer.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # then set JWT_SECRET (the command to generate one is in the file)
uvicorn app.main:app --reload   # open http://127.0.0.1:8000/docs
```

Or with PostgreSQL in Docker:

```bash
docker compose up --build       # http://localhost:8000/docs
```

## Tests

```bash
pytest                          # 44 tests on in-memory SQLite
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/db pytest   # the same tests on PostgreSQL
ruff check . && ruff format --check .
```

CI runs on every push and has three jobs:
1. Lint, then the full test suite twice: once on SQLite and once on a real PostgreSQL service.
2. Build the Docker image, start it with Docker Compose and Postgres, call the running API with `curl` (register, log in, create and list a deadline), and check the container isn't running as root.
3. `terraform fmt`, `init` and `validate`.

## Deploy to AWS

> This creates real AWS resources. Check the cost table above, and run `terraform destroy` when you're finished.

1. **Database:** create a free Supabase (or Neon) project. Copy its **session pooler** connection string and change `postgresql://` to `postgresql+psycopg://`.
2. **Infrastructure:**
   ```bash
   cd infra
   cp example.tfvars terraform.tfvars        # set alert_email
   terraform init
   terraform apply -target=aws_ecr_repository.api   # the registry has to exist before an image can go in it
   ```
3. **First image:** push it with the tag `bootstrap`:
   ```bash
   REPO=$(terraform output -raw ecr_repository_url)
   aws ecr get-login-password | docker login --username AWS --password-stdin "${REPO%/*}"
   docker build --provenance=false -t "$REPO:bootstrap" .. && docker push "$REPO:bootstrap"
   ```
4. **Secrets:** they're set by hand so they never touch Terraform:
   ```bash
   aws ssm put-parameter --name /uni-deadline-tracker/DATABASE_URL --type SecureString --overwrite --value 'postgresql+psycopg://...'
   aws ssm put-parameter --name /uni-deadline-tracker/JWT_SECRET  --type SecureString --overwrite \
     --value "$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
   ```
5. **Everything else:** run `terraform apply`, then confirm the two subscription emails from AWS. `terraform output api_url` gives the live URL.
6. **Automatic deploys:** in GitHub, go to Settings → Secrets and variables → Actions → **Variables** and add `AWS_DEPLOY_ROLE_ARN` with the value of `terraform output -raw deploy_role_arn`. Then **Actions → Deploy to AWS → Run workflow** builds, pushes and deploys, and checks `/health`. No AWS keys are stored in GitHub.

**Tear down:** `cd infra && terraform destroy`, then delete the two SSM parameters if you set them outside Terraform.

## Project layout

```
app/
  main.py           app, routers, health checks
  config.py         settings from env vars or SSM
  db.py             engine, sessions, the UTC datetime type
  models.py         User, Module, Deadline (SQLAlchemy 2)
  schemas.py        request and response validation (Pydantic 2)
  security.py       Argon2 hashing, JWTs, current-user dependency
  urgency.py        overdue, due soon or this week (pure function)
  ics.py            iCalendar feed (RFC 5545 escaping and line folding)
  routers/          auth, modules, deadlines, calendar
tests/              44 tests: auth, isolation, deadlines, urgency, calendar, config
infra/              Terraform: ECR, Lambda, API Gateway, SSM, alarms, budget, GitHub OIDC
Dockerfile          multi-stage, non-root, health check, Lambda-ready
docker-compose.yml  API and PostgreSQL for local use
```

## Limitations

- Tables are created at start-up with `create_all`. Changing the schema of a live database would need migrations (Alembic), which is the next thing to add.
- There's no login rate limiting per account, only the overall API Gateway limit. Repeated wrong passwords from one IP aren't blocked.
- No refresh tokens: you log in again after 30 minutes.
- The calendar feed is read-only, so ticking something off in your calendar doesn't update the API.
- I haven't left it deployed, because a public demo would need abuse protection and a database I'm happy to keep running.

## What I learned

TODO: in my own words.

## Next steps

- Alembic migrations
- Per-account login throttling
- A small front end (or a Discord bot) that uses this API
- Email reminders through Amazon SES
