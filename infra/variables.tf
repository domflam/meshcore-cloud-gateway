variable "project_id" {
  type    = string
  default = "meshcore-cloud-gateway"
}

variable "region" {
  type    = string
  default = "europe-west1"
}

variable "dataset_id" {
  type    = string
  default = "meshcore"
}

variable "container_image" {
  type        = string
  description = "Full Artifact Registry image URI, e.g. europe-west1-docker.pkg.dev/PROJECT/meshcore/ingestion:TAG"
}

variable "deploy_service" {
  type        = bool
  default     = false
  description = "Set true only after the container image exists and secret version is configured."
}

variable "allow_public_ingress" {
  type        = bool
  default     = false
  description = "Explicit opt-in to public HTTP access (bearer token enforced in app)."
}
