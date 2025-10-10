variable "project_id" {
    description = "The project ID to host the cluster in"
    default = "game-item-generation"
}

variable "zone" {
  description = "The specific zone to deploy GKE cluster and resources in"
  type        = string
  default     = "asia-southeast1-a"
}

variable "region" {
    description = "The region to host the cluster in"
    default = "asia-southeast1"
}

# variable "bucket" {
#     description = "The name of the GCS bucket"
#     default = "gig-worker-bucket"
# }