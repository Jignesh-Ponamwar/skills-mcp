---
name: terraform
description: >
  Write and manage infrastructure as code with HashiCorp Terraform. Covers resource definitions,
  variables, outputs, modules, state management, workspaces, provider configuration (AWS, GCP,
  Azure, Cloudflare), remote backends (S3, Terraform Cloud), data sources, locals, lifecycle rules,
  and CI/CD integration. Use when provisioning cloud infrastructure, writing Terraform modules,
  managing Terraform state, or importing existing resources.
license: Apache-2.0
metadata:
  author: hashicorp
  version: "1.0"
  tags: [terraform, iac, aws, gcp, azure, infrastructure, devops, cloud, modules]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - write Terraform
    - Terraform resource
    - infrastructure as code
    - Terraform module
    - Terraform state
    - provision AWS with Terraform
    - Terraform backend
    - Terraform variables
    - Terraform plan apply
    - IaC with Terraform
    - Terraform Cloud
---

# Terraform Infrastructure as Code Skill

## Step 1: Project Structure

```
infra/
├── main.tf              # Main resource definitions
├── variables.tf         # Input variable declarations
├── outputs.tf           # Output values
├── versions.tf          # Required providers and Terraform version
├── locals.tf            # Local values (computed names, tags)
├── backend.tf           # Remote state configuration
├── terraform.tfvars     # Variable values (gitignored for secrets)
├── terraform.tfvars.example  # Template for required vars
└── modules/
    ├── networking/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    └── compute/
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

---

## Step 2: Provider and Version Pinning

```hcl
# versions.tf
terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}
```

---

## Step 3: Variables and Locals

```hcl
# variables.tf
variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod"
  }
}

variable "app_name" {
  description = "Application name used in resource naming"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "database_password" {
  description = "Database master password"
  type        = string
  sensitive   = true  # never shown in plan/apply output
}

# locals.tf
locals {
  name_prefix  = "${var.app_name}-${var.environment}"
  is_prod      = var.environment == "prod"

  common_tags = {
    App         = var.app_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

---

## Step 4: Core Resources (AWS Examples)

```hcl
# main.tf — VPC + Subnets + EC2 + RDS pattern

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-vpc" })
}

# Public subnets (multi-AZ)
resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index}.0/24"
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-public-${count.index + 1}" })
}

# S3 bucket
resource "aws_s3_bucket" "assets" {
  bucket = "${local.name_prefix}-assets-${random_id.suffix.hex}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "main" {
  identifier        = "${local.name_prefix}-db"
  engine            = "postgres"
  engine_version    = "16.2"
  instance_class    = local.is_prod ? "db.t3.small" : "db.t3.micro"
  allocated_storage = local.is_prod ? 100 : 20

  db_name  = var.app_name
  username = "admin"
  password = var.database_password

  multi_az               = local.is_prod
  deletion_protection    = local.is_prod
  skip_final_snapshot    = !local.is_prod

  vpc_security_group_ids = [aws_security_group.database.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = local.is_prod ? 7 : 1
  storage_encrypted       = true

  tags = local.common_tags

  lifecycle {
    prevent_destroy       = false  # set true in prod
    ignore_changes        = [password]  # manage via Secrets Manager
  }
}
```

---

## Step 5: Outputs

```hcl
# outputs.tf
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "database_endpoint" {
  description = "RDS endpoint (host:port)"
  value       = "${aws_db_instance.main.endpoint}"
}

output "s3_bucket_name" {
  description = "S3 bucket name for assets"
  value       = aws_s3_bucket.assets.bucket
}
```

---

## Step 6: Remote State Backend

```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket         = "my-terraform-state-bucket"
    key            = "myapp/prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"  # for state locking
  }
}

# Create the backend resources first (bootstrap):
# aws s3api create-bucket --bucket my-terraform-state-bucket --region us-east-1
# aws dynamodb create-table --table-name terraform-locks \
#   --attribute-definitions AttributeName=LockID,AttributeType=S \
#   --key-schema AttributeName=LockID,KeyType=HASH \
#   --billing-mode PAY_PER_REQUEST
```

---

## Step 7: Reusable Modules

```hcl
# modules/networking/main.tf — reusable VPC module
variable "name_prefix" { type = string }
variable "vpc_cidr"    { type = string; default = "10.0.0.0/16" }
variable "tags"        { type = map(string); default = {} }

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  tags                 = merge(var.tags, { Name = "${var.name_prefix}-vpc" })
}

output "vpc_id"   { value = aws_vpc.this.id }
output "vpc_cidr" { value = aws_vpc.this.cidr_block }

# Calling the module:
# root main.tf
module "networking" {
  source      = "./modules/networking"
  name_prefix = local.name_prefix
  vpc_cidr    = "10.0.0.0/16"
  tags        = local.common_tags
}

# Public module from Terraform Registry:
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  name    = local.name_prefix
  cidr    = "10.0.0.0/16"
}
```

---

## Step 8: Essential Commands

```bash
# Workflow
terraform init          # download providers, init backend
terraform fmt           # format all .tf files
terraform validate      # check syntax
terraform plan          # preview changes
terraform apply         # apply changes (prompts for confirmation)
terraform destroy       # tear down all resources

# State management
terraform state list                      # list all resources in state
terraform state show aws_vpc.main         # inspect a resource
terraform import aws_vpc.main vpc-12345   # import existing resource
terraform state rm aws_s3_bucket.old      # remove from state (not from cloud)

# Workspaces (simple environment isolation)
terraform workspace new staging
terraform workspace select prod
terraform workspace list

# Targeted apply (use sparingly)
terraform apply -target=aws_db_instance.main
```

---

## Step 9: CI/CD with GitHub Actions

```yaml
# .github/workflows/terraform.yml
name: Terraform

on:
  pull_request:
    paths: ['infra/**']
  push:
    branches: [main]
    paths: ['infra/**']

jobs:
  plan:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: infra

    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: '1.7.0'
          cli_config_credentials_token: ${{ secrets.TF_API_TOKEN }}

      - name: Terraform Init
        run: terraform init

      - name: Terraform Format Check
        run: terraform fmt -check

      - name: Terraform Plan
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: terraform plan -no-color -out=tfplan
        
      - name: Post plan to PR
        uses: actions/github-script@v7
        # ... post plan output as PR comment

  apply:
    needs: plan
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production  # requires manual approval
    steps:
      - name: Terraform Apply
        run: terraform apply -auto-approve tfplan
```

---

## Common Mistakes

- **Not pinning provider versions** — always use `version = "~> 5.0"` to prevent breaking changes
- **Storing state locally** — always use remote state (S3 + DynamoDB) for team environments
- **Missing state locking** — DynamoDB table prevents concurrent applies that corrupt state
- **Sensitive values in tfvars committed to git** — use `.gitignore` for `*.tfvars`, use environment variables or Vault for secrets
- **Using `count` for resources with changing order** — use `for_each` with a map/set of unique keys instead
- **Forgetting `deletion_protection` in prod** — set on databases, critical buckets, etc.
- **`terraform destroy` in CI without protection** — use `environment` with approval gates for destructive operations
- **Not running `terraform fmt` in CI** — add format check to fail fast on unformatted code
