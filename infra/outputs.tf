output "api_url" {
  description = "Base URL of the live API. Interactive docs are at /docs."
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "deploy_role_arn" {
  description = "Save as the AWS_DEPLOY_ROLE_ARN repository variable in GitHub."
  value       = aws_iam_role.deploy.arn
}

output "ssm_parameter_names" {
  description = "Set these with the AWS CLI before the API will start."
  value       = [aws_ssm_parameter.database_url.name, aws_ssm_parameter.jwt_secret.name]
}
