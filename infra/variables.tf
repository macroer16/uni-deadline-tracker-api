variable "region" {
  description = "AWS region. London by default."
  type        = string
  default     = "eu-west-2"
}

variable "app_name" {
  description = "Used to name every resource."
  type        = string
  default     = "uni-deadline-tracker"
}

variable "alert_email" {
  description = "Gets budget warnings and error alarms. You must confirm the subscription email from AWS."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Budget alert threshold. AWS budgets are in US dollars."
  type        = number
  default     = 5
}

variable "github_repository" {
  description = "owner/repo allowed to deploy through GitHub Actions OIDC."
  type        = string
  default     = "macroer16/uni-deadline-tracker-api"
}

variable "image_tag" {
  description = "Image tag deployed on the first apply. After that, GitHub Actions deploys new images."
  type        = string
  default     = "bootstrap"
}

variable "create_github_oidc_provider" {
  description = "Set to false if this AWS account already has the GitHub OIDC provider."
  type        = bool
  default     = true
}
