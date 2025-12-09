#!/bin/bash

# Deployment Script for AWS Bedrock Agent Integration
# This script helps you deploy the functions to Firebase

echo "🚀 AWS Bedrock Agent - Firebase Deployment Script"
echo "=================================================="
echo ""

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    echo "❌ Firebase CLI is not installed."
    echo "Install it with: npm install -g firebase-tools"
    exit 1
fi

echo "✅ Firebase CLI found"
echo ""

# Check if logged in to Firebase
if ! firebase projects:list &> /dev/null; then
    echo "🔐 Please log in to Firebase..."
    firebase login
fi

echo "✅ Authenticated with Firebase"
echo ""

# Check if .env file exists in functions directory
if [ ! -f "functions/.env" ]; then
    echo "⚠️  No .env file found in functions/ directory"
    echo "📝 Creating .env from template..."
    cp functions/.env.example functions/.env
    echo ""
    echo "⚠️  IMPORTANT: Please edit functions/.env and add your credentials before deploying!"
    echo "Press Enter when done, or Ctrl+C to exit..."
    read
fi

echo "📦 Installing Python dependencies..."
cd functions
pip install -r requirements.txt
cd ..
echo "✅ Dependencies installed"
echo ""

# Ask user if they want to set environment variables
echo "❓ Do you want to set Firebase Functions config variables now? (y/n)"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo ""
    echo "📝 Setting up Firebase Functions configuration..."
    echo "Please provide the following values:"
    echo ""
    
    read -p "AWS Access Key: " aws_access_key
    read -p "AWS Secret Key: " aws_secret_key
    read -p "AWS Region [us-east-1]: " aws_region
    aws_region=${aws_region:-us-east-1}
    read -p "AWS Bedrock Agent ID: " bedrock_agent_id
    read -p "AWS Bedrock Agent Alias ID: " bedrock_alias_id
    read -p "Facebook Page Access Token: " fb_token
    read -p "Facebook Verify Token: " verify_token
    read -p "WhatsApp Phone Number ID: " whatsapp_id
    
    echo ""
    echo "Setting environment variables..."
    
    firebase functions:config:set \
        aws.access_key="$aws_access_key" \
        aws.secret_key="$aws_secret_key" \
        aws.region="$aws_region" \
        aws.bedrock_agent_id="$bedrock_agent_id" \
        aws.bedrock_agent_alias_id="$bedrock_alias_id" \
        facebook.page_access_token="$fb_token" \
        facebook.verify_token="$verify_token" \
        whatsapp.phone_number_id="$whatsapp_id"
    
    echo "✅ Configuration set successfully"
fi

echo ""
echo "🚀 Deploying functions to Firebase..."
firebase deploy --only functions

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deployment successful!"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Copy the function URLs from above"
    echo "2. Configure webhooks in Facebook Developer Console"
    echo "3. Test by sending a message to your page"
    echo ""
    echo "📚 See DEPLOYMENT.md for detailed instructions"
else
    echo ""
    echo "❌ Deployment failed. Check the errors above."
    exit 1
fi
