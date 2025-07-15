#!/bin/bash
# Setup MCP Servers with Credentials for AI Road Trip Storyteller

set -e

echo "🚀 Setting up MCP Servers with your credentials"
echo "=============================================="

# Get project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
MCP_DIR="$PROJECT_ROOT/.mcp-servers"

# Create secure credentials directory
CREDS_DIR="$PROJECT_ROOT/.credentials"
mkdir -p "$CREDS_DIR"
chmod 700 "$CREDS_DIR"

# Save GCP service account securely
echo "🔐 Creating placeholder for GCP service account credentials..."
cat > "$CREDS_DIR/roadtrip-backend-sa.json" << 'EOF'
{
  "type": "service_account",
  "project_id": "YOUR_PROJECT_ID",
  "private_key_id": "YOUR_PRIVATE_KEY_ID",
  "private_key": "YOUR_PRIVATE_KEY",
  "client_email": "YOUR_SERVICE_ACCOUNT_EMAIL",
  "client_id": "YOUR_CLIENT_ID",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "YOUR_CERT_URL",
  "universe_domain": "googleapis.com"
}
EOF
chmod 600 "$CREDS_DIR/roadtrip-backend-sa.json"

# Set environment variables
export GITHUB_PERSONAL_ACCESS_TOKEN="YOUR_GITHUB_TOKEN"
export GOOGLE_APPLICATION_CREDENTIALS="$CREDS_DIR/roadtrip-backend-sa.json"
export GCP_PROJECT_ID="YOUR_PROJECT_ID"

# Create .env.mcp for MCP-specific credentials
cat > "$PROJECT_ROOT/.env.mcp" << EOF
# MCP Server Credentials
GITHUB_PERSONAL_ACCESS_TOKEN=YOUR_GITHUB_TOKEN
GOOGLE_APPLICATION_CREDENTIALS=$CREDS_DIR/roadtrip-backend-sa.json
GCP_PROJECT_ID=YOUR_PROJECT_ID
DATABASE_URL=postgresql://roadtrip:roadtrip_dev@localhost:5432/roadtrip
EOF
chmod 600 "$PROJECT_ROOT/.env.mcp"

# Update .gitignore to ensure credentials are never committed
if ! grep -q ".credentials/" "$PROJECT_ROOT/.gitignore" 2>/dev/null; then
    echo -e "\n# MCP Credentials - NEVER COMMIT\n.credentials/\n.env.mcp\n.mcp-servers/" >> "$PROJECT_ROOT/.gitignore"
fi

# Now run the original setup script
echo
echo "🚀 Running MCP setup with your credentials..."
# Source the env file properly
set -a
source "$PROJECT_ROOT/.env.mcp"
set +a
"$PROJECT_ROOT/scripts/setup/setup_mcp_servers.sh"

echo
echo "⚠️  SECURITY REMINDER:"
echo "   - Your credentials are saved in $CREDS_DIR"
echo "   - These files are restricted to your user only (chmod 600)"
echo "   - They are added to .gitignore"
echo "   - NEVER share these credentials publicly"
echo "   - Consider rotating your GitHub token since it was exposed"
echo
echo "🔒 To rotate your GitHub token:"
echo "   1. Go to https://github.com/settings/tokens"
echo "   2. Delete the exposed token"
echo "   3. Create a new token with the same permissions"
echo "   4. Update .env.mcp with the new token"