output "dataset" {
  value = "${var.project_id}.${google_bigquery_dataset.telemetry.dataset_id}"
}

output "artifact_repository" {
  value = google_artifact_registry_repository.images.id
}

output "runtime_service_account" {
  value = google_service_account.ingestion.email
}

output "cloud_run_url" {
  value = var.deploy_service ? google_cloud_run_v2_service.ingestion[0].uri : null
}
