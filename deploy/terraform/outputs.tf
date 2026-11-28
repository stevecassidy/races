output "droplet_ip" {
  description = "Public IP address of the Droplet"
  value       = digitalocean_droplet.app.ipv4_address
}

output "droplet_id" {
  description = "ID of the Droplet"
  value       = digitalocean_droplet.app.id
}

output "volume_id" {
  description = "ID of the persistent volume"
  value       = digitalocean_volume.data.id
}

output "volume_device" {
  description = "Block device path of the attached volume on the Droplet"
  value       = digitalocean_volume.data.filesystem_label != "" ? "/dev/disk/by-id/scsi-0DO_Volume_${digitalocean_volume.data.name}" : "/dev/sda"
}

output "domain_name" {
  description = "Domain name associated with the Droplet"
  value       = var.domain_name != "" ? var.domain_name : null
}
