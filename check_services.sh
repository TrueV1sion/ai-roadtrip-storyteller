#!/bin/bash
echo "🏥 Service Health Check"
echo "======================"

# Knowledge Graph
echo -n "Knowledge Graph: "
curl -s http://localhost:8000/api/health > /dev/null 2>&1 && echo "✅ Running" || echo "❌ Not running"

# Redis (if available)
echo -n "Redis: "
redis-cli ping > /dev/null 2>&1 && echo "✅ Running" || echo "⚠️  Not available"

# Show running Python processes
echo ""
echo "Python processes:"
ps aux | grep python3 | grep -v grep
