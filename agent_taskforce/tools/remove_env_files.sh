#!/bin/bash
# Emergency .env file removal script
# Purpose: Securely remove all .env files containing exposed credentials

echo "=== EMERGENCY ENV FILE REMOVAL ==="
echo "This script will remove all .env files containing exposed credentials"
echo ""

# List all .env files that will be removed
echo "Files to be removed:"
find /mnt/c/users/jared/onedrive/desktop/roadtrip -name "*.env*" -type f 2>/dev/null | grep -v node_modules | while read file; do
    echo "  - $file"
done

echo ""
read -p "Are you sure you want to remove these files? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    echo ""
    echo "Removing .env files..."
    
    # Remove specific known files with exposed credentials
    rm -f /mnt/c/users/jared/onedrive/desktop/roadtrip/.env
    rm -f /mnt/c/users/jared/onedrive/desktop/roadtrip/.env.email.backup
    rm -f /mnt/c/users/jared/onedrive/desktop/roadtrip/deploy/mvp/.env.cloud_run
    rm -f /mnt/c/users/jared/onedrive/desktop/roadtrip/infrastructure/staging/.env.staging
    rm -f /mnt/c/users/jared/onedrive/desktop/roadtrip/mobile/.env.production
    
    echo "Files removed successfully"
    echo ""
    echo "IMPORTANT: Now run these commands to clean git history:"
    echo ""
    echo "git filter-branch --force --index-filter \\"
    echo "  'git rm --cached --ignore-unmatch .env* mobile/.env* infrastructure/*/.env* deploy/*/.env*' \\"
    echo "  --prune-empty --tag-name-filter cat -- --all"
    echo ""
    echo "git push origin --force --all"
    echo "git push origin --force --tags"
else
    echo "Operation cancelled"
fi