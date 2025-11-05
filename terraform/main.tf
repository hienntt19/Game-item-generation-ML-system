# Define the required Terraform version and Google provider version
terraform {
    required_providers {
        google = {
            source  = "hashicorp/google"
            version = "4.80.0"
        }

        postgresql = {
            source  = "cyrilgdn/postgresql"
            version = "1.22.0" 
        }

        random = {
            source = "hashicorp/random"
            version = ">= 3.1.0"
        }

        time = {
            source  = "hashicorp/time"
            version = ">= 0.9.0"
        }
        
        null = {
            source  = "hashicorp/null"
            version = ">= 3.2.0"
        }
    }
    required_version = "1.5.6"
}

provider "google" {
    project = var.project_id
    region  = var.region
}

provider "postgresql" {
    host = google_sql_database_instance.service-db.private_ip_address
    port = 5432
    username = google_sql_user.app_user.name
    password = random_password.db_password.result
    # database = google_sql_database.app_db.name
    sslmode = "disable"
    superuser = false
}

# Google Cloud SQL
resource "google_sql_database_instance" "service-db" {
    name = "${var.project_id}-service-db"
    database_version = "POSTGRES_14"
    region = var.region

    deletion_protection = true

    settings {
        tier = "db-f1-micro"

        ip_configuration {
            ipv4_enabled = true
            private_network = google_compute_network.vpc_network.id
        }
    }
    depends_on = [google_service_networking_connection.default]
}


resource "random_password" "db_password" {
    length = 20
    special = false
}

resource "google_sql_user" "app_user" {
    name = "hienntt19"
    instance = google_sql_database_instance.service-db.name
    password = random_password.db_password.result
}

resource "google_sql_database" "app_db" {
    name = "image_requests"
    instance = google_sql_database_instance.service-db.name
}

resource "time_sleep" "wait_for_db" {
  depends_on = [
    google_sql_database.app_db,
    google_sql_user.app_user
  ]
  create_duration = "30s"
}

resource "null_resource" "create_db_schema" {
    depends_on = [time_sleep.wait_for_db]

    provisioner "local-exec" {
        command = <<EOT
        if [ ! -f /tmp/cloud-sql-proxy ]; then
            curl -o /tmp/cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
            chmod +x /tmp/cloud-sql-proxy
        fi
        
        # Start proxy in background
        /tmp/cloud-sql-proxy ${google_sql_database_instance.service-db.connection_name} &
        PROXY_PID=$!
        
        # Wait for proxy to be ready
        sleep 10
        
        # Execute SQL script
        PGPASSWORD="${random_password.db_password.result}" psql \
            -h 127.0.0.1 \
            -p 5432 \
            -U ${google_sql_user.app_user.name} \
            -d ${google_sql_database.app_db.name} \
            -f ${path.module}/postgres/create_table.sql
        
        # Kill proxy
        kill $PROXY_PID
        EOT
        
        interpreter = ["bash", "-c"]
    }

    triggers = {
        script_hash = filemd5("${path.module}/postgres/create_table.sql")
        db_name = google_sql_database.app_db.name
    }
}

# Google Kubernetes Engine cluster
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

# Node pool for GKE cluster
resource "google_container_node_pool" "primary_nodes" {
    name = "${var.project_id}-np"
    location = var.region
    cluster = google_container_cluster.service-cluster.name
    # node_count = 1

    version = google_container_cluster.service-cluster.master_version

    autoscaling {
        min_node_count = 1
        max_node_count = 3
    }

    node_config {
        machine_type = "e2-standard-4"
        # spot = true
        disk_size_gb = 30
        service_account = google_service_account.gke_service_account.email
        oauth_scopes = [
            "https://www.googleapis.com/auth/cloud-platform",
        ]
    }
}


# Service account for GKE nodes
resource "google_service_account" "gke_service_account" {
    account_id = "gke-nodes-sa"
    display_name = "Service account for GKE nodes"
}

# Service account for API Gateway
resource "google_service_account" "app_gsa" {
    account_id   = "api-gateway-gsa"
    display_name = "GSA for API Gateway Application"
}

# Provide Cloud SQL Client role to API Gateway service account
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

# Service account for jenkins VM (to connect google cloud services)
resource "google_service_account" "jenkins_vm_sa" {
    account_id   = "jenkins-vm-sa"
    display_name = "Service Account for Jenkins GCE VM"
}

# Provide roles to the Jenkins VM service account
# Kubernetes Engine Developer role: for deploying applications to GKE cluster
resource "google_project_iam_member" "jenkins_gke_developer" {
    project = var.project_id
    role = "roles/container.developer"
    member = "serviceAccount:${google_service_account.jenkins_vm_sa.email}"
}


# Google Compute Engine to run jenkins
resource "google_compute_instance" "jenkins_instance" {
    name = var.instance_name
    machine_type = "e2-standard-2"
    zone = var.zone
    tags = ["jenkins-master-access"]

    boot_disk {
        initialize_params {
            image = var.boot_disk_image
            size = var.boot_disk_size
        }
    }

    network_interface {
        network    = google_compute_network.vpc_network.id
        subnetwork = google_compute_subnetwork.service_subnet.id
        # network = "default"

        access_config {
            // Ephemeral IP
        }
    }

    service_account {
        email  = google_service_account.jenkins_vm_sa.email
        scopes = ["cloud-platform"]
    }

    depends_on = [
      google_project_iam_member.jenkins_gke_developer,
    ]
}

resource "google_compute_firewall" "jenkins_firewall" {
  name    = var.firewall_name
  network    = google_compute_network.vpc_network.id
#   network = "default"

  target_tags = ["jenkins-master-access"]

  allow {
    protocol = "tcp"
    ports    = ["22", "8081", "50000"]
  }

  source_ranges = ["0.0.0.0/0"] # allow all traffic
}


# Google Cloud Storage
resource "google_storage_bucket" "inference_worker_bucket" {
    name     = var.bucket
    location = var.region
    force_destroy = false

    uniform_bucket_level_access = true

    lifecycle {
        prevent_destroy = true
    }
}

# Service account for Cloud Storage
resource "google_service_account" "storage_admin_sa" {
    account_id   = "storage-admin-sa"
    display_name = "Service Account for GCS"
}

# Provide Object Admin role to the GCS service account
resource "google_storage_bucket_iam_member" "storage_admin_binding" {
    bucket = google_storage_bucket.inference_worker_bucket.name
    role = "roles/storage.objectAdmin"
    member = "serviceAccount:${google_service_account.storage_admin_sa.email}"
}

