# The real values are set by hand with the AWS CLI (see README), so they never appear in
# Terraform code or state. Terraform creates placeholders and then ignores the value.
locals {
  ssm_prefix = "/${var.app_name}"
}

resource "aws_ssm_parameter" "database_url" {
  name  = "${local.ssm_prefix}/DATABASE_URL"
  type  = "SecureString"
  value = "set-me-with-the-aws-cli"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "jwt_secret" {
  name  = "${local.ssm_prefix}/JWT_SECRET"
  type  = "SecureString"
  value = "set-me-with-the-aws-cli"

  lifecycle {
    ignore_changes = [value]
  }
}
