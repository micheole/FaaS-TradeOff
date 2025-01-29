# Define the GCP project
variable "gcp_project" {
  description = "The GCP project to deploy resources to"
  type        = string
  default     = "monte_carlo_project"  # Default value
}

# Define the GCP region
variable "gcp_region" {
  description = "The region to deploy the resources in"
  type        = string
  default     = "europe-west3"
}

# Storage bucket settings
variable "bucket_name" {
  description = "The name of the GCP Storage bucket for the function"
  type        = string
  default     = "monte_carlo_bucket_name"
}

variable "force_destroy_bucket" {
  description = "Force destroy the bucket when deleting"
  type        = bool
  default     = true
}

# Cloud Function settings
variable "function_name" {
  description = "The name of the GCP Cloud Function"
  type        = string
  default     = "monte_carlo_function_name"
}

variable "function_description" {
  description = "Description of the GCP Cloud Function"
  type        = string
  default     = "monte_carlo_function_description"
}

variable "function_runtime" {
  description = "The runtime environment for the GCP Cloud Function"
  type        = string
  default     = "nodejs20"
}

variable "function_memory_mb" {
  description = "The amount of memory (in MB) allocated to the GCP Cloud Function"
  type        = number
  default     = 128
}

variable "service_account_name" {
  description = "The name of the service account for the Cloud Function"
  type        = string
  default     = "function-service-account"
}

variable "service_account_display_name" {
  description = "The display name of the service account"
  type        = string
  default     = "Service Account for Cloud Function"
}
