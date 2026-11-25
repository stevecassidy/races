variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "syd1"
}

variable "droplet_size" {
  description = "Droplet size slug"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "droplet_image" {
  description = "Droplet OS image"
  type        = string
  default     = "ubuntu-24-04-x64"
}

variable "ssh_key_name" {
  description = "Name of the SSH key registered in DigitalOcean"
  type        = string
}

variable "volume_size" {
  description = "Volume size in GB"
  type        = number
  default     = 10
}

variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
  default     = "cabici"
}

variable "domain_name" {
  description = "Primary domain name for the Droplet (DNS must be delegated to DigitalOcean)"
  type        = string
  default     = ""
}

variable "domain_aliases" {
  description = "Additional full domain names to point at the Droplet (e.g. otherdomain.org). Each gets its own DNS zone and A record. Subdomains of domain_name are handled automatically (e.g. www)."
  type        = list(string)
  default     = []
}
