#!/bin/bash
# Setup MCP Servers for AI Road Trip Storyteller

set -e

echo "🚀 Setting up MCP Servers for Roadtrip Project"
echo "=============================================="

# Get project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
MCP_DIR="$PROJECT_ROOT/.mcp-servers"

# Create MCP servers directory
mkdir -p "$MCP_DIR"
cd "$MCP_DIR"

# 1. Setup GitHub MCP Server
echo
echo "📦 1. Setting up GitHub MCP Server..."
if [ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
    echo "⚠️  Please set GITHUB_PERSONAL_ACCESS_TOKEN environment variable"
    echo "   Create a token at: https://github.com/settings/tokens"
    echo "   Then run: export GITHUB_PERSONAL_ACCESS_TOKEN='your-token'"
else
    claude mcp add github npx -y @modelcontextprotocol/server-github || {
        echo "GitHub server may already be configured"
    }
    echo "✅ GitHub MCP server configured"
fi

# 2. Setup PostgreSQL MCP Server
echo
echo "📦 2. Setting up PostgreSQL MCP Server..."
if [ ! -d "postgresql-mcp-server" ]; then
    git clone https://github.com/HenkDz/postgresql-mcp-server.git
    cd postgresql-mcp-server
    npm install
    cd ..
fi

# Get database connection from .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -E '^DATABASE_URL=' "$PROJECT_ROOT/.env" | xargs)
fi

if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL not found in .env"
    echo "   Using default: postgresql://roadtrip:roadtrip_dev@localhost:5432/roadtrip"
    export DATABASE_URL="postgresql://roadtrip:roadtrip_dev@localhost:5432/roadtrip"
fi

claude mcp add postgresql-server node "$MCP_DIR/postgresql-mcp-server/index.js" || {
    echo "PostgreSQL server may already be configured"
}
echo "✅ PostgreSQL MCP server configured"

# 3. Setup GCP MCP Server
echo
echo "📦 3. Setting up Google Cloud MCP Server..."
if [ ! -d "google-cloud-mcp" ]; then
    git clone https://github.com/krzko/google-cloud-mcp.git
    cd google-cloud-mcp
    npm install
    cd ..
fi

# Check for GCP credentials
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "⚠️  GOOGLE_APPLICATION_CREDENTIALS not set"
    echo "   Set it to your service account JSON path"
else
    claude mcp add gcp-server node "$MCP_DIR/google-cloud-mcp/index.js" || {
        echo "GCP server may already be configured"
    }
    echo "✅ GCP MCP server configured"
fi

# 4. Create MCP configuration file
echo
echo "📝 Creating MCP configuration..."
cat > "$PROJECT_ROOT/.mcp-config.json" << EOF
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN:-YOUR_TOKEN_HERE}"
      }
    },
    "postgresql": {
      "command": "node",
      "args": ["$MCP_DIR/postgresql-mcp-server/index.js"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}"
      }
    },
    "gcp": {
      "command": "node", 
      "args": ["$MCP_DIR/google-cloud-mcp/index.js"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "${GOOGLE_APPLICATION_CREDENTIALS:-/path/to/credentials.json}",
        "GCP_PROJECT_ID": "${GCP_PROJECT_ID:-roadtrip-460720}"
      }
    }
  }
}
EOF

echo "✅ MCP configuration saved to .mcp-config.json"

# 5. List configured servers
echo
echo "📋 Configured MCP Servers:"
claude mcp list

echo
echo "🎉 MCP Setup Complete!"
echo
echo "📌 Next Steps:"
echo "1. Set missing environment variables:"
echo "   export GITHUB_PERSONAL_ACCESS_TOKEN='your-token'"
echo "   export GOOGLE_APPLICATION_CREDENTIALS='/path/to/credentials.json'"
echo "   export GCP_PROJECT_ID='roadtrip-460720'"
echo
echo "2. Test the servers:"
echo "   - GitHub: I can now access your repositories with @github"
echo "   - PostgreSQL: I can query your database with @postgresql"
echo "   - GCP: I can manage your cloud resources with @gcp"
echo
echo "3. Example usage:"
echo "   'Show me recent commits' (uses @github)"
echo "   'What tables are in the database?' (uses @postgresql)"
echo "   'List my Cloud Run services' (uses @gcp)"