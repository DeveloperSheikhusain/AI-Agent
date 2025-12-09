# Deployment Guide

This guide walks you through deploying the AWS Bedrock Agent integration to Firebase.

## Prerequisites

- [x] AWS Bedrock Agent created with Agent ID and Alias ID
- [x] Facebook Developer App configured
- [x] Firebase project initialized
- [x] Firebase CLI installed (`npm install -g firebase-tools`)

## Step 1: Configure Environment Variables

### Option A: Using Firebase Functions Config (Recommended for Production)

Set environment variables using Firebase CLI:

```bash
# AWS Bedrock Configuration
firebase functions:config:set aws.access_key="YOUR_AWS_ACCESS_KEY"
firebase functions:config:set aws.secret_key="YOUR_AWS_SECRET_KEY"
firebase functions:config:set aws.region="us-east-1"
firebase functions:config:set aws.bedrock_agent_id="YOUR_AGENT_ID"
firebase functions:config:set aws.bedrock_agent_alias_id="YOUR_ALIAS_ID"

# Facebook/Social Media Configuration
firebase functions:config:set facebook.page_access_token="YOUR_PAGE_TOKEN"
firebase functions:config:set facebook.verify_token="YOUR_VERIFY_TOKEN"
firebase functions:config:set whatsapp.phone_number_id="YOUR_PHONE_NUMBER_ID"
```

**Note:** You'll need to update `common.py` to use `functions.config()` instead of `os.environ.get()` if using this method.

### Option B: Using Environment Variables (For Local Testing)

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your credentials

3. Load variables before deploying (Firebase will read from your shell environment)

## Step 2: Update common.py for Config Method

If you're using Firebase Functions Config (Option A), update the `get_remote_config` function in `common.py`:

```python
from firebase_functions import params

def get_remote_config(key: str) -> str:
    # Map environment variable names to Firebase config paths
    config_map = {
        'AWS_ACCESS_KEY': params.StringParam('AWS_ACCESS_KEY'),
        'AWS_SECRET_KEY': params.SecretParam('AWS_SECRET_KEY'),
        # ... etc
    }
    return config_map.get(key).value if config_map.get(key) else None
```

## Step 3: Install Dependencies

```bash
cd functions
pip install -r requirements.txt
```

## Step 4: Deploy to Firebase

```bash
# Deploy all functions
firebase deploy --only functions

# Or deploy specific function
firebase deploy --only functions:webhook_facebook
```

## Step 5: Note Your Function URLs

After deployment, Firebase will output URLs like:

```
✔  functions[us-central1-agent_invoke(us-central1)] deployed
✔  functions[us-central1-webhook_facebook(us-central1)] deployed
✔  functions[us-central1-webhook_instagram(us-central1)] deployed
✔  functions[us-central1-webhook_whatsapp(us-central1)] deployed
✔  functions[us-central1-users_list(us-central1)] deployed
✔  functions[us-central1-chat_history(us-central1)] deployed

Function URL (agent_invoke): https://us-central1-YOUR_PROJECT.cloudfunctions.net/agent_invoke
Function URL (webhook_facebook): https://us-central1-YOUR_PROJECT.cloudfunctions.net/webhook_facebook
...
```

**Save these URLs** - you'll need them for webhook configuration.

## Step 6: Configure Facebook Developer App Webhooks

### For Facebook Messenger:

1. Go to [Facebook Developers](https://developers.facebook.com)
2. Select your app → Messenger → Settings
3. In "Webhooks" section, click "Add Callback URL"
4. Enter:
   - **Callback URL**: `https://YOUR_REGION-YOUR_PROJECT.cloudfunctions.net/webhook_facebook`
   - **Verify Token**: Your `FACEBOOK_VERIFY_TOKEN`
5. Click "Verify and Save"
6. Subscribe to webhook fields:
   - `messages`
   - `messaging_postbacks`

### For Instagram:

1. Go to Instagram → Settings in your app dashboard
2. Follow same steps as Facebook
3. Use your `webhook_instagram` URL

### For WhatsApp:

1. Go to WhatsApp → Configuration
2. Add webhook URL: `webhook_whatsapp`
3. Subscribe to `messages` field

## Step 7: Test the Integration

### Test Agent Invoke API:
```bash
curl -X POST https://YOUR_FUNCTION_URL/agent_invoke \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "message": "Hello, can you help me?"
  }'
```

### Test Webhook Verification:
```bash
# This should return your challenge token
curl "https://YOUR_FUNCTION_URL/webhook_facebook?hub.mode=subscribe&hub.challenge=test123&hub.verify_token=YOUR_VERIFY_TOKEN"
```

### Test Live Message:
Send a message to your Facebook Page or Instagram account and check:
1. Firebase Functions logs (`firebase functions:log`)
2. Firestore console for user details and chat history
3. Response received on the platform

## Step 8: Monitor and Debug

### View Logs:
```bash
# Stream logs in real-time
firebase functions:log --only webhook_facebook

# View all logs
firebase functions:log
```

### Check Firestore:
1. Open [Firebase Console](https://console.firebase.google.com)
2. Navigate to Firestore Database
3. Look for collections:
   - `ss_facebook_user_details`
   - `ss_facebook_chat_history`
   - etc.

## Troubleshooting

### Issue: "FACEBOOK_VERIFY_TOKEN not found"
- Make sure environment variables are set correctly
- Redeploy after setting config: `firebase deploy --only functions`

### Issue: Webhook verification fails
- Check that verify token in Facebook matches your config
- Check function logs for errors

### Issue: Messages not being received
- Verify webhook subscription is active
- Check that page access token has correct permissions
- Ensure app is not in development mode (or test with test users)

### Issue: AWS Bedrock errors
- Verify AWS credentials are correct
- Check that Bedrock Agent ID and Alias are valid
- Ensure AWS region is correct

## Security Best Practices

1. **Never commit credentials** to git
2. Use Firebase **Secret Manager** for production:
   ```bash
   firebase functions:secrets:set AWS_SECRET_KEY
   ```
3. Rotate access tokens regularly
4. Monitor function usage and costs
5. Set up Firebase App Check for additional security

## Next Steps

- Set up monitoring and alerts
- Configure CORS if needed for direct API access
- Add rate limiting
- Implement user authentication for API endpoints
- Set up CI/CD pipeline for automatic deployment
