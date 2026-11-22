#!/usr/bin/env bash
#
# Push sensitive files from the main repo to the private config repo,
# encrypting them with SOPS.
#
# Usage:
#   ./deploy/scripts/sops-push.sh
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

# Files to encrypt and push via SOPS
ENCRYPTED_FILES=(
  "${DEPLOY_DIR}/terraform/terraform.tfvars:terraform/terraform.tfvars.sops"
  "${DEPLOY_DIR}/ansible/group_vars/all.yml:ansible/group_vars/all.yml.sops"
)

# Files to copy as plaintext (deployment-specific but not secret)
PLAIN_FILES=(
  "${DEPLOY_DIR}/terraform/backend.tf:terraform/backend.tf"
)

for entry in "${ENCRYPTED_FILES[@]}"; do
  src="${entry%%:*}"
  dst_name="${entry##*:}"
  dst="${CONFIG_DIR}/${dst_name}"

  if [[ ! -f "${src}" ]]; then
    echo "[SKIP] Source file does not exist: ${src}"
    continue
  fi

  echo "[ENCRYPT] ${src} -> ${dst}"
  mkdir -p "$(dirname "${dst}")"
  sops --config "${CONFIG_DIR}/.sops.yaml" --encrypt "${src}" > "${dst}"
done

for entry in "${PLAIN_FILES[@]}"; do
  src="${entry%%:*}"
  dst_name="${entry##*:}"
  dst="${CONFIG_DIR}/${dst_name}"

  if [[ ! -f "${src}" ]]; then
    echo "[SKIP] Source file does not exist: ${src}"
    continue
  fi

  echo "[COPY] ${src} -> ${dst}"
  mkdir -p "$(dirname "${dst}")"
  cp "${src}" "${dst}"
done

echo "[DONE] Files pushed to ${CONFIG_DIR}"
echo ""
echo "Remember to commit and push the config repo:"
echo "  cd ${CONFIG_DIR}"
echo "  git add -A && git commit -m 'Update secrets' && git push"
