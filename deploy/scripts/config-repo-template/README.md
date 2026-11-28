# races-git-config — Private Configuration Repository

This repository holds the encrypted secrets and concrete configuration values
for the `races-git` (cabici) Django application.

## Prerequisites

- [SOPS](https://github.com/getsops/sops) >= 3.8
- An Age key pair (`age-keygen -o ~/.config/sops/age/keys.txt`)

## Files

```
.
├── .sops.yaml                          # SOPS configuration (public key)
├── terraform/
│   ├── backend.tf                      # Plain: Terraform backend configuration
│   └── terraform.tfvars.sops           # Encrypted: DO token, SSH key name, etc.
└── ansible/
    └── group_vars/
        └── all.yml.sops                # Encrypted: Django secrets, DB password, etc.
```

## File Types

### Encrypted files (`.sops`)
These contain sensitive values and are encrypted with SOPS:
- `terraform.tfvars.sops`
- `ansible/group_vars/all.yml.sops`

### Plain files
These are deployment-specific but contain no secrets:
- `terraform/backend.tf` — Terraform remote state backend configuration

## Encrypting Files

You don't normally edit these files directly. Instead:

1. Place the **plaintext** versions in the main repo's `deploy/` directory
2. Run the push script from the main repo:
   ```bash
   cd ../races-git
   ./deploy/scripts/sops-push.sh
   ```

The push script will encrypt `.tfvars` and `.yml` files with SOPS, and copy
`backend.tf` as plaintext.

Or, to edit an existing encrypted file:

```bash
sops terraform.tfvars.sops
```

## Decrypting Files

To pull decrypted files back into the main repo for deployment:

```bash
cd ../races-git
./deploy/scripts/sops-pull.sh
```

## Security Notes

- **Never commit plaintext secrets** to this repo or the main repo.
- The `.sops.yaml` file contains only the **public** Age key. It is safe to commit.
- Your **private** Age key lives in `~/.config/sops/age/keys.txt`. Keep it safe and back it up.
- Add the private key to your password manager or encrypted backup.
