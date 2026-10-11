# Private container registry for the API image.
resource "aws_ecr_repository" "api" {
  name                 = var.app_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true # lets `terraform destroy` remove it even with images inside

  image_scanning_configuration {
    scan_on_push = true # free basic vulnerability scan of every image
  }
}

# Keep only the 10 newest images so storage costs stay near zero.
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}
