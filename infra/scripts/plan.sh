#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan -var-file=terraform.tfvars.example
