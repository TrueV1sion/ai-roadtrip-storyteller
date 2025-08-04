#!/bin/bash

# Run Context7 MCP Server for AI Road Trip Storyteller
# This provides up-to-date documentation context for development

echo "Starting Context7 MCP Server..."
echo "Project: AI Road Trip Storyteller"
echo "----------------------------------------"

# Export project context
export CONTEXT7_PROJECT="AI Road Trip Storyteller"
export CONTEXT7_FRAMEWORKS="fastapi,react-native,expo,sqlalchemy,google-cloud"
export CONTEXT7_PRIORITY="security,production-readiness,mobile-optimization"

# Run Context7 MCP
npx -y @upstash/context7-mcp@latest

echo "Context7 MCP Server is ready for use!"
echo "Add 'use context7' to your prompts to fetch documentation"