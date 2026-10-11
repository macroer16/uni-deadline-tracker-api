resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.app_name}"
  retention_in_days = 14
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.app_name}-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Least privilege: the function can read only its own two parameters.
data "aws_iam_policy_document" "lambda_ssm" {
  statement {
    actions   = ["ssm:GetParameters"]
    resources = [aws_ssm_parameter.database_url.arn, aws_ssm_parameter.jwt_secret.arn]
  }
}

resource "aws_iam_role_policy" "lambda_ssm" {
  name   = "read-own-parameters"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_ssm.json
}

resource "aws_lambda_function" "api" {
  function_name = var.app_name
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"
  architectures = ["x86_64"]
  memory_size   = 512
  timeout       = 15

  environment {
    variables = {
      ENVIRONMENT                  = "production"
      SSM_PARAMETER_PREFIX         = local.ssm_prefix
      AWS_LWA_PORT                 = "8000"
      AWS_LWA_READINESS_CHECK_PATH = "/health/live"
    }
  }

  depends_on = [aws_cloudwatch_log_group.api, aws_iam_role_policy_attachment.lambda_logs]

  lifecycle {
    # GitHub Actions deploys new images; Terraform shouldn't roll them back.
    ignore_changes = [image_uri]
  }
}
