# Create VPC network
resource "google_compute_network" "vpc_network" {
    name = "${var.project_id}-vpc"
    auto_create_subnetworks = false
}

# Create subnet in VPC
resource "google_compute_subnetwork" "service_subnet" {
    name = "${var.project_id}-service-subnet"
    ip_cidr_range = "10.10.0.0/24"
    region = var.region
    network = google_compute_network.vpc_network.id

    # Create ip range for pods and services in GKE
    secondary_ip_range {
        range_name = "pods-range"
        ip_cidr_range = "10.20.0.0/16"
    }

    secondary_ip_range {
        range_name = "services-range"
        ip_cidr_range = "10.30.0.0/16"
    }
}


# Create ip alloc for private service access
resource "google_compute_global_address" "private_ip_alloc" {
    name = "private-ip-alloc-for-gcp-services"
    purpose = "VPC_PEERING"
    address_type = "INTERNAL"
    prefix_length = 16
    network = google_compute_network.vpc_network.id
}

# Establish connection between VPC and Google services
resource "google_service_networking_connection" "default" {
    network = google_compute_network.vpc_network.id
    service = "servicenetworking.googleapis.com"
    reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]
}