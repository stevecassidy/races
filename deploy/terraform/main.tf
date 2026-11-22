# Data source for the SSH key registered in DO
data "digitalocean_ssh_key" "main" {
  name = var.ssh_key_name
}

# Firewall: allow SSH, HTTP, HTTPS
resource "digitalocean_firewall" "web" {
  name = "${var.project_name}-firewall"

  droplet_ids = [digitalocean_droplet.app.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "53"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

# Persistent volume for Postgres data + media uploads
resource "digitalocean_volume" "data" {
  region                  = var.region
  name                    = "${var.project_name}-data"
  size                    = var.volume_size
  initial_filesystem_type = "ext4"
  description             = "Persistent data volume for ${var.project_name}"
}

# Droplet
resource "digitalocean_droplet" "app" {
  name     = "${var.project_name}-app"
  region   = var.region
  size     = var.droplet_size
  image    = var.droplet_image
  ssh_keys = [data.digitalocean_ssh_key.main.id]
}

# Attach the volume to the droplet
resource "digitalocean_volume_attachment" "data" {
  droplet_id = digitalocean_droplet.app.id
  volume_id  = digitalocean_volume.data.id
}

# Create the DNS zone on DigitalOcean (requires nameservers pointing to DO)
resource "digitalocean_domain" "app" {
  count      = var.domain_name != "" ? 1 : 0
  name       = var.domain_name
}

# A record pointing the domain to the Droplet IP
resource "digitalocean_record" "app" {
  count      = var.domain_name != "" ? 1 : 0
  domain     = digitalocean_domain.app[0].name
  type       = "A"
  name       = "@"
  value      = digitalocean_droplet.app.ipv4_address
  ttl        = 300
}
