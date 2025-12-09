# AWS Bedrock Agent Integration - Quick Start Guide

This project integrates AWS Bedrock Agent with Facebook Messenger, Instagram DM, and WhatsApp Business API.

## 📦 Project Structure

```
AI-Agent/
├── functions/
│   ├── main.py           # API endpoints and webhook handlers
│   ├── common.py         # Firestore and messaging utilities
│   ├── bedrock_utils.py  # AWS Bedrock Agent integration
│   ├── requirements.txt  # Python dependencies
│   └── .env.example      # Environment variables template
└── firebase.json         # Firebase configuration
```

## 🚀 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agent_invoke` | POST | Direct API to invoke Bedrock Agent |
| `/webhook_facebook` | GET/POST | Facebook Messenger webhook |
| `/webhook_instagram` | GET/POST | Instagram DM webhook |
| `/webhook_whatsapp` | GET/POST | WhatsApp Business webhook |
| `/users_list` | GET | Get users by platform |
| `/chat_history` | GET | Get chat history by user |

## ⚙️ Configuration (Required)

Set these as **Environment Variables** in Firebase Cloud Functions:

```bash
# AWS Bedrock
AWS_ACCESS_KEY=<your-aws-access-key>
AWS_SECRET_KEY=<your-aws-secret-key>
AWS_REGION=us-east-1
AWS_BEDROCK_AGENT_ID=<your-agent-id>
AWS_BEDROCK_AGENT_ALIAS_ID=<your-agent-alias-id>

# Facebook Messenger
FACEBOOK_PAGE_ACCESS_TOKEN=<your-page-token>
FACEBOOK_VERIFY_TOKEN=<your-verify-token>
FACEBOOK_APP_ID=<your-app-id>
FACEBOOK_APP_SECRET=<your-app-secret>

# Instagram (can use Facebook token or separate)
INSTAGRAM_PAGE_ACCESS_TOKEN=<your-instagram-token>
INSTAGRAM_VERIFY_TOKEN=<your-verify-token>

# WhatsApp Business
WHATSAPP_PHONE_NUMBER_ID=<your-whatsapp-phone-id>
WHATSAPP_ACCESS_TOKEN=<your-whatsapp-token>
WHATSAPP_VERIFY_TOKEN=<your-verify-token>
```

## 📊 Firestore Collections

### User Details
- `ss_facebook_user_details`
- `ss_instagram_user_details`
- `ss_whatsapp_user_details`

### Chat History
- `ss_facebook_chat_history/{user_id}/messages`
- `ss_instagram_chat_history/{user_id}/messages`
- `ss_whatsapp_chat_history/{user_id}/messages`

## 🛠️ Deployment

```bash
# Install dependencies
cd functions
pip install -r requirements.txt

# Deploy to Firebase
firebase deploy --only functions
```

## 🔗 Configure Webhooks

After deployment, add these webhook URLs to your Facebook Developer App:

- **Facebook**: `https://<region>-<project>.cloudfunctions.net/webhook_facebook`
- **Instagram**: `https://<region>-<project>.cloudfunctions.net/webhook_instagram`
- **WhatsApp**: `https://<region>-<project>.cloudfunctions.net/webhook_whatsapp`

## 💡 How It Works

1. User sends message on Facebook/Instagram/WhatsApp
2. Webhook receives the message
3. System saves user details and message to Firestore
4. Previous chat history is retrieved for context
5. AWS Bedrock Agent generates response
6. Response is sent back to user
7. Conversation is saved for future continuity

## 📝 Example Usage

### Test Agent Invoke
```bash
curl -X POST https://your-function-url/agent_invoke \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test123",
    "message": "Hello AI!"
  }'
```

### Get Chat History
```bash
curl "https://your-function-url/chat_history?user_id=test123&platform=facebook&limit=10"
```

## 🎯 Features

✅ AWS Bedrock Agent integration  
✅ Multi-platform support (Facebook, Instagram, WhatsApp)  
✅ Conversational context preservation  
✅ Automatic user management  
✅ Complete chat history storage  
✅ Webhook verification  
✅ Error handling and logging  

## 📚 Documentation

For detailed implementation plan, see: [implementation_plan.md](.gemini/antigravity/brain/*/implementation_plan.md)