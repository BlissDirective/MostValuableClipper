#!/bin/bash
# Deploy MVC backend to Fly.io

set -e

echo "🚀 Deploying MVC Backend to Fly.io..."

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "❌ fly CLI not found. Install from https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

# Check if logged in
if ! fly auth whoami &> /dev/null; then
    echo "❌ Not logged in to Fly.io. Run: fly auth login"
    exit 1
fi

# Create app if it doesn't exist
if ! fly status &> /dev/null; then
    echo "📦 Creating Fly.io app..."
    fly apps create mvc-backend
fi

# Set secrets from .env file
if [ -f .env ]; then
    echo "🔐 Setting secrets..."
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ $key =~ ^#.*$ ]] && continue
        [[ -z $key ]] && continue
        
        # Trim whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        
        if [ -n "$value" ]; then
            fly secrets set "$key=$value"
        fi
    done < .env
fi

# Deploy
echo "🚀 Deploying..."
fly deploy

echo "✅ Deployment complete!"
echo "🌐 App URL: https://mvc-backend.fly.dev"
