"""Settings come from environment variables (or a .env file when running locally)."""

import secrets
import warnings

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./deadlines.db"
    # Must be set in production. Locally a random one is made at start-up,
    # which means logins stop working after a restart, a reminder to set it.
    jwt_secret: str = ""
    token_minutes: int = 30
    environment: str = "development"
    # In AWS, secrets live in SSM Parameter Store (encrypted) rather than in environment
    # variables or Terraform, e.g. /uni-deadline-tracker/DATABASE_URL.
    ssm_parameter_prefix: str = ""

    def model_post_init(self, __context) -> None:
        if self.ssm_parameter_prefix:
            self._load_from_ssm()
        if not self.jwt_secret:
            if self.environment == "production":
                raise RuntimeError("JWT_SECRET must be set in production")
            warnings.warn("JWT_SECRET not set: using a random secret for this run only", stacklevel=2)
            self.jwt_secret = secrets.token_urlsafe(48)
        elif len(self.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 characters")

    def _load_from_ssm(self) -> None:
        import boto3  # only needed in AWS, so imported here

        prefix = self.ssm_parameter_prefix.rstrip("/")
        names = [f"{prefix}/DATABASE_URL", f"{prefix}/JWT_SECRET"]
        resp = boto3.client("ssm").get_parameters(Names=names, WithDecryption=True)
        if resp["InvalidParameters"]:
            raise RuntimeError(f"Missing SSM parameters: {resp['InvalidParameters']}")
        values = {p["Name"].rsplit("/", 1)[1]: p["Value"] for p in resp["Parameters"]}
        self.database_url = values["DATABASE_URL"]
        self.jwt_secret = values["JWT_SECRET"]


settings = Settings()
