#!/bin/bash

# Quick script to update your API keys

echo "🔑 Quick API Key Update"
echo "======================"
echo ""

# Check current status
echo "Current configuration:"
grep -E "(RECREATION_GOV|TICKETMASTER|OPENWEATHERMAP)" .env | grep -v "#"
echo ""

# Get new keys
echo "Enter your new API keys (press Enter to skip):"
echo ""

read -p "Recreation.gov API Key: " REC_KEY
read -p "Ticketmaster API Key: " TM_KEY
read -p "OpenWeatherMap API Key: " WEATHER_KEY

# Update .env file
if [ ! -z "$REC_KEY" ]; then
    sed -i "s/RECREATION_GOV_API_KEY=.*/RECREATION_GOV_API_KEY=$REC_KEY/" .env
    echo "✅ Updated Recreation.gov key"
fi

if [ ! -z "$TM_KEY" ]; then
    sed -i "s/TICKETMASTER_API_KEY=.*/TICKETMASTER_API_KEY=$TM_KEY/" .env
    echo "✅ Updated Ticketmaster key"
fi

if [ ! -z "$WEATHER_KEY" ]; then
    sed -i "s/OPENWEATHERMAP_API_KEY=.*/OPENWEATHERMAP_API_KEY=$WEATHER_KEY/" .env
    echo "✅ Updated OpenWeatherMap key"
fi

echo ""
echo "🎉 Configuration updated!"
echo ""
echo "Test your APIs with:"
echo "python3 scripts/test_api_dashboard.py"