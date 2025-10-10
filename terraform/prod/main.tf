# Define the required Terraform version and Google provider version
terraform {
    required_providers {
        google = {
            source  = "hashicorp/google"
            version = "4.80.0"
        }
    }
    required_version = "1.5.6"
}

provider "google" {
    project = var.project_id
    region  = var.region
}

#--------GKE cluster---------------
resource "google_container_cluster" "service-cluster" {
    name = "${var.project_id}-service-cluster"
    location = var.region

    network = google_compute_network.vpc_network.id
    subnetwork = google_compute_subnetwork.service_subnet.id

    remove_default_node_pool = true
    initial_node_count = 1

    workload_identity_config {
        workload_pool = "${var.project_id}.svc.id.goog"
    }

    ip_allocation_policy {
        cluster_secondary_range_name = google_compute_subnetwork.service_subnet.secondary_ip_range[0].range_name
        services_secondary_range_name = google_compute_subnetwork.service_subnet.secondary_ip_range[1].range_name
    }
}

#-----------Node pool for GKE cluster----------------
resource "google_container_node_pool" "primary_nodes" {
    name = "${var.project_id}-np"
    location = var.region
    cluster = google_container_cluster.service-cluster.name
    node_count = 1

    node_config {
        machine_type = "e2-small"
        # spot = true
        disk_size_gb = 30
        service_account = google_service_account.gke_service_account.email
        oauth_scopes = [
            "https://www.googleapis.com/auth/cloud-platform",
        ]
    }
}

#--------Google Cloud SQL---------------
resource "google_sql_database_instance" "service-db" {
    name = "${var.project_id}-service-db"
    database_version = "POSTGRES_14"
    region = var.region

    deletion_protection = false

    settings {
        tier = "db-f1-micro"

        ip_configuration {
            ipv4_enabled = false
            private_network = google_compute_network.vpc_network.id
        }
    }
    depends_on = [google_service_networking_connection.default]
}

#---------Service account for GKE nodes----------------
resource "google_service_account" "gke_service_account" {
    account_id = "gke-nodes-sa"
    display_name = "Service account for GKE nodes"
}

#---------Service account for application----------------
resource "google_service_account" "app_gsa" {
    account_id   = "api-gateway-gsa"
    display_name = "GSA for API Gateway Application"
}


#--------Provide Cloud SQL Client role to the service account----------------
resource "google_project_iam_member" "app_gsa_sql_client" {
    project = var.project_id
    role = "roles/cloudsql.client"
    member = "serviceAccount:${google_service_account.app_gsa.email}"
}

resource "google_service_account_iam_member" "app_gsa_workload_identity_user" {
  service_account_id = google_service_account.app_gsa.name
  role = "roles/iam.workloadIdentityUser"
  member = "serviceAccount:${var.project_id}.svc.id.goog[service-dev/ksa-api-gateway]"
}


#---------Google Cloud Storage----------------
# resource "google_storage_bucket" "gig-worker-bucket" {
#     name     = var.bucket
#     location = var.region
#     force_destroy = true

#     uniform_bucket_level_access = true
# }