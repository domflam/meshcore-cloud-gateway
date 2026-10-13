locals {
  required_apis = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
  ])
}

resource "google_project_service" "apis" {
  for_each           = local.required_apis
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = "meshcore"
  description   = "MeshCore Cloud Gateway containers"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

resource "google_bigquery_dataset" "telemetry" {
  project                    = var.project_id
  dataset_id                 = var.dataset_id
  location                   = var.region
  description                = "MeshCore telemetry data"
  delete_contents_on_destroy = false
  depends_on                 = [google_project_service.apis]
}

resource "google_bigquery_table" "telemetry" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.telemetry.dataset_id
  table_id            = "telemetry"
  deletion_protection = true

  require_partition_filter = true
  time_partitioning {
    type  = "DAY"
    field = "observed_at"
  }
  clustering = ["node_id"]
  schema = jsonencode([
    { name = "event_id", type = "STRING", mode = "REQUIRED" },
    { name = "node_id", type = "STRING", mode = "REQUIRED" },
    { name = "observed_at", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "received_at", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "voltage_v", type = "FLOAT", mode = "NULLABLE" },
    { name = "temperature_c", type = "FLOAT", mode = "NULLABLE" },
    { name = "source", type = "STRING", mode = "NULLABLE" }
  ])
}

resource "google_service_account" "ingestion" {
  project      = var.project_id
  account_id   = "meshcore-ingestion"
  display_name = "MeshCore telemetry ingestion runtime"
  depends_on   = [google_project_service.apis]
}

resource "google_bigquery_dataset_iam_member" "ingestion_writer" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.telemetry.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_secret_manager_secret" "ingest_token" {
  project   = var.project_id
  secret_id = "meshcore-ingest-token"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "ingestion_secret_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.ingest_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_cloud_run_v2_service" "ingestion" {
  count    = var.deploy_service ? 1 : 0
  project  = var.project_id
  name     = "meshcore-ingestion"
  location = var.region
  ingress  = var.allow_public_ingress ? "INGRESS_TRAFFIC_ALL" : "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.ingestion.email
    scaling {
      max_instance_count = 2
    }
    containers {
      image = var.container_image
      env {
        name  = "BQ_TABLE"
        value = "${var.project_id}.${var.dataset_id}.telemetry"
      }
      env {
        name = "INGEST_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.ingest_token.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_bigquery_dataset_iam_member.ingestion_writer,
    google_secret_manager_secret_iam_member.ingestion_secret_access,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count    = var.deploy_service && var.allow_public_ingress ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ingestion[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
