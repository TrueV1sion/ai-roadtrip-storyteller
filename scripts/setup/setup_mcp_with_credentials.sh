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
echo "🔐 Saving GCP service account credentials..."
cat > "$CREDS_DIR/roadtrip-backend-sa.json" << 'EOF'
{
  "type": "service_account",
  "project_id": "roadtrip-460720",
  "private_key_id": "f1a0e38a23b55e01b5ba1b1779d5c43dcb5169a1",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCvZLuEocCd4Ihy\ngtFLbekh2Di0Jrhuzp6f3C3dn3JnYUoejH7+PcCgVV8SuRYDoT9ohauehmCtNQtE\nG0TiZ/C4FrN9wDLZVb/Jv7QJwSGFLbeUMOGw63xCQCCZKDV0q1mhZzCs/vQx2urV\n57J+cpt8X+VOUpIYc4IVy7hFWzHF4DnuFnS/+085OZ+OPnK10ufb9JU76vGxLe/f\nNar60+vvWxWXmDpGzxuRQU+XhxCNAZXT0tsij5yibRUyIQqc6qvdsl2biDzZvAJj\nYCsjdYHKIywX8LfXGJnA9sOB/EjZ8i2mJEPXKBSQUa/+6UciJ6FI468EHLmx/HHQ\nFesvOC0pAgMBAAECggEARhEizEBmF2vsdnqGK/Dzkl6zgFx7j2Chg9FMzV12MZBv\nMLcFwIFg42xXd75S6g5Pq2zC+6hJFMi9AG84XI4TXydKezD9307fODSKMt9hibeS\nv/OrJaddU4YUv7qNaFdPjigQDPwpB4WiDOPrrZIRRWV10I0x6eyzCgwBSEu/HYHk\nECfQ8reCOzYLGu5RFdV8/V4z8q/FivRMBXEGfIijjWXIEM6zQauWEIEyVvu2hDfd\n1LDLCAqeAlvZw+ZqAHyNM7nN+3qLXrQdvrxCCIIUoQvXXlPDhMYQ0HHKIoVZZXrQ\nVThv6uMheovZV9NMz1Q+bMpQn+rtBTPCTwDWXoYiFQKBgQDzkEQy+ESHlLa2WhWc\nkW1bCpYat0g2sQlgc34STDQ7e2bgVj0Q/MQYHv+kdMdBKIo2bHqqj9yiKiKDJ6V8\nIgCxSd71qrpwCMz1iSIeijKVMGWB4BFado/UYHty+2enqer/HYUzZr7GSKYf813R\nZNiS1WtAehXd+Peq7B3pwmINSwKBgQC4WWIccTPrlu/L7azKpETTFaXEewlM4ekZ\nlm/p+z5d/neNcCWCIRgM3JmzvRsGZRQdZ+zRvy7dwHv318+Uoas8ZBlSeZgZreJn\nGw0uPNF8wfGaHzN8s2hXVE/V5U5Q9cmo73WumK/SXY9iIWH5nsB0jbAiK4kpYQcg\n4WpOxqmq2wKBgFUN3iMGe7f1ANExKDbiuhN+4Og3dOpUbHfYHQB6yAq1jzlsJCsY\necoKmS9u8F4asBlNTJDfaCbhG+g9Ihb1MNS4fTnBAxY4nIpp9xY/IGbk3a2695Rl\nrth1UObYUFxGhB/OyUMn8BsCJ7EkpXCIDPFJwghkGdrIJIT1q4SEMwV9AoGAVHRe\nhjk2WA/l+77/Ejb/cNTSBJl5QUedyqMo0kDP6a/ShXGDPYJ7yiimIbnYz60u8enS\njKTRi7XLFVhBOQ53rEsPbsFV9S28MxApka07K7SOQtVYeSCYBKoTiSJsJprzr/lE\nKKC6q91A+uvgPsOD1+Gxd3YKeHKDGYUrdrt8r1ECgYEA1n29BsMY2y7KD6gKtFxV\nrpJQ71diOryhCrflHJOtCxPNeltiiMjCPtjCkDmljwTOOHYQp9v7+CMwQdZ29g0B\nOJloKQYFU9bDLC9d5lu5Y9NI1MyLOtBp6bnpQ5Byz9/q2aH6aVhDoi9AA6S+Gqd9\nIstlaViYyPPIMyB4vep7b8I=\n-----END PRIVATE KEY-----\n",
  "client_email": "roadtrip-backend@roadtrip-460720.iam.gserviceaccount.com",
  "client_id": "101305540990922176055",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/roadtrip-backend%40roadtrip-460720.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
EOF
chmod 600 "$CREDS_DIR/roadtrip-backend-sa.json"

# Set environment variables
export GITHUB_PERSONAL_ACCESS_TOKEN="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"
export GOOGLE_APPLICATION_CREDENTIALS="$CREDS_DIR/roadtrip-backend-sa.json"
export GCP_PROJECT_ID="roadtrip-460720"

# Create .env.mcp for MCP-specific credentials
cat > "$PROJECT_ROOT/.env.mcp" << EOF
# MCP Server Credentials
GITHUB_PERSONAL_ACCESS_TOKEN=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
GOOGLE_APPLICATION_CREDENTIALS=$CREDS_DIR/roadtrip-backend-sa.json
GCP_PROJECT_ID=roadtrip-460720
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