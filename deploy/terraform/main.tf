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

# A record pointing the primary domain to the Droplet IP
resource "digitalocean_record" "app" {
  count      = var.domain_name != "" ? 1 : 0
  domain     = digitalocean_domain.app[0].name
  type       = "A"
  name       = "@"
  value      = digitalocean_droplet.app.ipv4_address
  ttl        = 300
}

# Separate out full external domains from subdomains of the primary domain.
# External domains (different registered name) get their own DNS zone.
# Subdomains of domain_name (e.g. www.example.com) are A records in the
# primary zone.
locals {
  # Full external domains: entries in domain_aliases that are NOT subdomains of domain_name
  external_domains = var.domain_name != "" ? [
    for alias in var.domain_aliases :
    alias
    if alias != var.domain_name && !endswith(alias, ".${var.domain_name}")
  ] : []

  # Subdomains of the primary domain: strip the primary domain suffix
  subdomain_aliases = var.domain_name != "" ? [
    for alias in var.domain_aliases :
    replace(alias, ".${var.domain_name}", "")
    if endswith(alias, ".${var.domain_name}") && alias != var.domain_name
  ] : []
}

# DNS zone for each external alias domain (nameservers must be delegated to DO)
resource "digitalocean_domain" "aliases" {
  for_each = toset(local.external_domains)
  name     = each.value
}

# A record @ in each external domain pointing to the Droplet
resource "digitalocean_record" "external_aliases" {
  for_each = toset(local.external_domains)
  domain   = digitalocean_domain.aliases[each.value].name
  type     = "A"
  name     = "@"
  value    = digitalocean_droplet.app.ipv4_address
  ttl      = 300
}

# A records for subdomain aliases within the primary domain (e.g. www)
resource "digitalocean_record" "subdomain_aliases" {
  for_each = toset(local.subdomain_aliases)
  domain   = digitalocean_domain.app[0].name
  type     = "A"
  name     = each.value
  value    = digitalocean_droplet.app.ipv4_address
  ttl      = 300
}
