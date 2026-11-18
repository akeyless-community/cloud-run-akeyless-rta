terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_service_account" "rta" {
  account_id   = var.service_account_name
  display_name = "Akeyless RTA (Cloud Run)"
}

resource "google_cloud_run_v2_service" "rta" {
  name                = var.service_name
  location            = var.region
  ingress             = var.ingress
  deletion_protection = false

  template {
    service_account = google_service_account.rta.email
    timeout         = "300s"

    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"
      network_interfaces {
        network    = var.network
        subnetwork = var.subnet
      }
    }

    containers {
      image = var.image

      ports {
        container_port = 8080
      }

      env {
        name  = "AKEYLESS_GATEWAY_URL"
        value = var.akeyless_gateway_url
      }
      env {
        name  = "AKEYLESS_ACCESS_ID"
        value = var.akeyless_access_id
      }
      env {
        name  = "AKEYLESS_ACCESS_TYPE"
        value = "gcp"
      }
      env {
        name  = "AKEYLESS_GCP_AUDIENCE"
        value = var.akeyless_gcp_audience
      }
      dynamic "env" {
        for_each = var.akeyless_default_secret_name == "" ? [] : [var.akeyless_default_secret_name]
        content {
          name  = "AKEYLESS_DEFAULT_SECRET_NAME"
          value = env.value
        }
      }
    }
  }
}

# No allUsers / allAuthenticatedUsers binding: callers must hold roles/run.invoker.
resource "google_cloud_run_v2_service_iam_member" "invokers" {
  for_each = toset(var.invoker_members)

  name     = google_cloud_run_v2_service.rta.name
  location = google_cloud_run_v2_service.rta.location
  role     = "roles/run.invoker"
  member   = each.value
}
