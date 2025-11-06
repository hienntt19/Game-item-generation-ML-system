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

variable "instance_name" {
    description = "The name of the GCE instance"
    default = "jenkins-instance"
}

variable "boot_disk_image" {
    description = "The boot disk image for the GCE instance"
    default = "ubuntu-os-cloud/ubuntu-2204-lts"
}

variable "boot_disk_size" {
  description = "boot disk size in GB"
  default     = 30
}

# variable "ssh_keys" {
#   description = "ssh keys to access the instance"
#   default     = ""
# }

variable "firewall_name" {
  description = "name of the firewall rule"
  default     = "firewall-rule"
}

variable "bucket" {
    description = "The name of the GCS bucket"
    default = "inference-worker-bucket"
}