output "gke_cluster_name" {
    description = "The name of the GKE cluster"
    value = google_container_cluster.service-cluster.name
}

output "gke_cluster_location" {
    description = "The location of the GKE cluster"
    value = google_container_cluster.service-cluster.location
}

output "gke_cluster_endpoint" {
    description = "The endpoint of the GKE cluster"
    value = google_container_cluster.service-cluster.endpoint
    sensitive = true
}

output "sql_instance_connection_name" {
    value = google_sql_database_instance.service-db.connection_name
}

output "application_gsa_email" {
    value = google_service_account.app_gsa.email
}

output "gke_node_service_account_email" {
    value = google_service_account.gke_service_account.email
}

# output "image_bucket_name" {
#     description = "The name of the image storage bucket"
#     value = google_storage_bucket.gig-worker-bucket.name
# }

