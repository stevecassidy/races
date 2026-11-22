# Deployment Guide: Single Droplet (Django + PostgreSQL)

This directory contains **Terraform** infrastructure code and **Ansible** server configuration to deploy the cabici Django application on a single DigitalOcean Droplet with a persistent volume for data.

## Architecture

- **Droplet**: Ubuntu 24.04 running Docker + Docker Compose + Nginx
- **Database**: PostgreSQL inside a Docker container
- **Persistent Storage**: DO Volume mounted at `/mnt/cabici-data` (Postgres data + media uploads + static files)
- **Reverse Proxy**: Nginx on the host (outside Docker) proxying to Gunicorn
- **SSL**: Let's Encrypt via Certbot
- **Static/Media Files**: Nginx serves `/static/` and `/media/` directly from the volume; everything else proxied to Django

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.5
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/index.html) >= 2.15
- A DigitalOcean account and API token
- An SSH public key [uploaded to DigitalOcean](https://cloud.digitalocean.com/account/security)
- A domain or subdomain pointing at the Droplet (for Certbot / HTTPS)

## Directory Layout

```
deploy/
├── README.md
├── docker-compose.production.yml
├── terraform/
│   ├── main.tf               -- Droplet, Volume, Firewall
│   ├── variables.tf
│   ├── outputs.tf
│   ├── provider.tf
│   ├── backend.tf            -- Remote state template (optional)
│   └── terraform.tfvars      -- NOT committed; see .tfvars.example
└── ansible/
    ├── inventory.ini         -- Generated after terraform apply
    ├── inventory.ini.example
    ├── playbook.yml
    ├── requirements.yml
    ├── group_vars/
    │   ├── all.yml           -- Plain variables
    │   └── all.yml.vault     -- Encrypted secrets (not committed)
    └── roles/
        ├── base/             -- System packages
        ├── docker/           -- Docker CE + Compose plugin
        ├── volume/           -- Format & mount DO Volume
        ├── app/              -- Clone repo, env file, start containers
        ├── nginx/            -- Reverse proxy
        └── certbot/          -- SSL certificate
```

## 1. Provision Infrastructure (Terraform)

```bash
cd deploy/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your DO token, SSH key name, and domain
terraform init
terraform plan
terraform apply
```

After apply finishes, note the **droplet_ip** output.

If you set `domain_name`, Terraform will also create the DNS zone and an A record
pointing to the Droplet (your domain's nameservers must be delegated to
DigitalOcean for this to resolve).

### Remote State (Recommended)

To store state in a DO Space, create `backend.tf`:

```hcl
terraform {
  backend "s3" {
    endpoint                    = "https://syd1.digitaloceanspaces.com"
    bucket                      = "your-state-bucket"
    key                         = "cabici/terraform.tfstate"
    region                      = "us-east-1"
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
    use_path_style              = true
  }
}
```

## 2. Generate Ansible Inventory

```bash
cd deploy/terraform
terraform output -raw droplet_ip > ../ansible/inventory.ini
# Or manually create deploy/ansible/inventory.ini:
# [cabici]
# <droplet_ip>
# [cabici:vars]
# ansible_user=root
# ansible_python_interpreter=/usr/bin/python3
```

## 3. Configure Secrets (Ansible)

Edit `deploy/ansible/group_vars/all.yml` and set your domain and non-secret values.

**Sensitive values** (passwords, API keys) should be encrypted with Ansible Vault:

```bash
cd deploy/ansible
ansible-vault create group_vars/all.yml.vault
```

Key secrets to set in the vault:
- `django_secret_key` — generate with `openssl rand -base64 50`
- `db_password` — strong PostgreSQL password
- `mailersend_api_token` — if using MailerSend
- `geoposition_google_maps_api_key` — if using maps

## 4. Configure Server (Ansible)

Install required Ansible collections:

```bash
cd deploy/ansible
ansible-galaxy collection install -r requirements.yml
```

Only `ansible.posix` (for the volume mount module) is required.
The playbook uses standard `ansible.builtin` modules and raw `docker` CLI
to avoid dependency on the `community.docker` collection.

Run the playbook:

```bash
ansible-playbook -i inventory.ini playbook.yml
# If using vault:
# ansible-playbook -i inventory.ini playbook.yml --ask-vault-pass
```

This will:
1. Update system packages
2. Install Docker + Docker Compose
3. Format and mount the DO Volume at `/mnt/cabici-data`
4. Clone the application repository
5. Create the production environment file
6. Build and start the app with Docker Compose
7. Run Django migrations and collectstatic automatically
8. Install and configure Nginx as a reverse proxy
9. Obtain an SSL certificate via Certbot

## 5. Post-Deploy

After the playbook completes, the app should be available at your domain over HTTPS.

To create a superuser or run management commands:

```bash
ssh root@<droplet_ip>
cd /opt/cabici
docker compose -f deploy/docker-compose.production.yml exec web python bin/production.py createsuperuser
```

To view logs:

```bash
docker compose -f deploy/docker-compose.production.yml logs -f
```

## 6. Backing Up Data

The DO Volume holds everything persistent. You should additionally back up the database:

```bash
# On the Droplet, run via cron daily
docker compose -f /opt/cabici/deploy/docker-compose.production.yml exec -T db pg_dump -U cabici cabici > /mnt/cabici-data/backups/cabici-$(date +%Y%m%d).sql
```

## 7. Recovering / Rebuilding the Droplet

Because data lives on the Volume (not the Droplet), you can safely rebuild:

1. `terraform destroy -target digitalocean_droplet.app`
2. `terraform apply` (creates a new Droplet and re-attaches the same Volume)
3. `ansible-playbook -i inventory.ini playbook.yml`

The database, media uploads, and collected static files will remain intact.

## Updating the Application

Push code to the repository, then on the Droplet:

```bash
ssh root@<droplet_ip>
cd /opt/cabici
git pull
docker compose -f deploy/docker-compose.production.yml up -d --build
```

Or automate via GitHub Actions / CI that SSHs in and runs the same commands.
