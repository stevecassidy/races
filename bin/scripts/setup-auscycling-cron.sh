#!/bin/bash
# Setup weekly cron job to validate memberships

# This script should be run to install the cron job
# It will validate memberships every Wednesday at 2 AM

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Create the cron job script
cat > "$PROJECT_DIR/scripts/validate_memberships_cron.sh" << 'EOF'
#!/bin/bash
cd /workspaces/races-git
source venv/bin/activate
python manage.py validate_memberships --months 6 >> /var/log/membership_validation.log 2>&1
EOF

chmod +x "$PROJECT_DIR/scripts/validate_memberships_cron.sh"

# Add to crontab (runs every Wednesday at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * 3 $PROJECT_DIR/scripts/validate_memberships_cron.sh") | crontab -

echo "Cron job installed successfully"
echo "Memberships will be validated every Wednesday at 2 AM"
echo "Logs will be written to /var/log/membership_validation.log"