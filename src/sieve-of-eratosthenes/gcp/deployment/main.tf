provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

data "archive_file" "function_code" {
  type        = "zip"
  source_dir  = "${path.module}/../src" 
  output_path = "${path.module}/function.zip"
}

resource "google_storage_bucket" "function_bucket" {
  name     = var.bucket_name
  location = var.gcp_region
  force_destroy = var.force_destroy_bucket
}

resource "google_storage_bucket_object" "function_zip" {
  name   = "function.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.function_code.output_path
}

resource "google_service_account" "function_sa" {
  account_id   = var.service_account_name
  display_name = var.service_account_display_name
}

resource "google_cloudfunctions_function_iam_member" "public_invoker" {
  project        = var.gcp_project
  region         = var.gcp_region
  cloud_function = google_cloudfunctions_function.cloud_function.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

resource "google_cloudfunctions_function" "cloud_function" {
  name                  = var.function_name
  description           = var.function_description
  runtime               = var.function_runtime
  available_memory_mb   = var.function_memory_mb
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.function_zip.name
  entry_point           = "estimatePi"

  trigger_http          = true
  service_account_email = google_service_account.function_sa.email
}

output "function_url" {
  value = google_cloudfunctions_function.cloud_function.https_trigger_url
}