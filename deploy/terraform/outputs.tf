output "service_url" {
  value = google_cloud_run_v2_service.rta.uri
}

output "service_account_email" {
  description = "Bind this service account in the Akeyless GCP auth method."
  value       = google_service_account.rta.email
}
