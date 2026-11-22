#!/usr/bin/env bash
#
# Pull encrypted files from the private config repo and decrypt them
# into the main repo's deploy directories.
#
# Usage:
#   ./deploy/scripts/sops-pull.sh
#
# The private config repo path is read from CABICI_CONFIG_DIR (env var)
# or defaults to ../races-git-config.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPLOY_DIR="${REPO_ROOT}/deploy"

CONFIG_DIR=${1:-"${REPO_ROOT}/../races-git-config"}

echo "Config repo: ${CONFIG_DIR}"

# Encrypted files in config repo -> decrypted targets in main repo
ENCRYPTED_FILES=(
  "${CONFIG_DIR}/terraform/terraform.tfvars.sops:${DEPLOY_DIR}/terraform/terraform.tfvars"
  "${CONFIG_DIR}/ansible/group_vars/all.yml.sops:${DEPLOY_DIR}/ansible/group_vars/all.yml"
)

# Plain files to copy back
PLAIN_FILES=(
  "${CONFIG_DIR}/terraform/backend.tf:${DEPLOY_DIR}/terraform/backend.tf"
)

for entry in "${ENCRYPTED_FILES[@]}"; do
  src="${entry%%:*}"
  dst="${entry##*:}"

  if [[ ! -f "${src}" ]]; then
    echo "[SKIP] Encrypted source file does not exist: ${src}"
    continue
  fi

  echo "[DECRYPT] ${src} -> ${dst}"
  mkdir -p "$(dirname "${dst}")"
  sops --decrypt "${src}" > "${dst}"
done

for entry in "${PLAIN_FILES[@]}"; do
  src="${entry%%:*}"
  dst="${entry##*:}"

  if [[ ! -f "${src}" ]]; then
    echo "[SKIP] Plain source file does not exist: ${src}"
    continue
  fi

  echo "[COPY] ${src} -> ${dst}"
  mkdir -p "$(dirname "${dst}")"
  cp "${src}" "${dst}"
done

echo "[DONE] Files are ready for deployment."
echo ""
echo "Run Terraform + Ansible when ready:"
echo "  cd ${DEPLOY_DIR}/terraform && terraform apply"
echo "  cd ${DEPLOY_DIR}/ansible && ansible-playbook -i inventory.ini playbook.yml"
