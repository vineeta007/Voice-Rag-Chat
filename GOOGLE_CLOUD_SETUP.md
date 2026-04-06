# Google Cloud TTS Setup Guide

## Quick Setup (5 minutes)

### Step 1: Create New Google Cloud Account

1. Go to https://console.cloud.google.com
2. Sign in with your Google account
3. Accept terms and create new project

### Step 2: Enable Text-to-Speech API

1. Go to https://console.cloud.google.com/apis/library/texttospeech.googleapis.com
2. Click "Enable" button
3. Wait for API to activate (~30 seconds)

### Step 3: Enable Billing (Required)

1. Go to https://console.cloud.google.com/billing
2. Click "Link Billing Account"
3. Add payment method (credit/debit card)
4. **Free tier**: 1 million characters/month = ~10,000 responses!

### Step 4: Create Service Account Key

1. Go to https://console.cloud.google.com/iam-admin/serviceaccounts
2. Click "Create Service Account"
3. Name: `voicerag-tts`
4. Role: Select "Project > Owner" or "Cloud Text-to-Speech Admin"
5. Click "Done"
6. Click on the service account you just created
7. Go to "Keys" tab
8. Click "Add Key" > "Create New Key"
9. Select "JSON" format
10. Click "Create" - JSON file will download

### Step 5: Configure Voice RAG

1. Move downloaded JSON file to `/Users/meetpatel/Desktop/voicerag/`
2. Rename it to `google-cloud-key.json`
3. Update `.env` file to point to it (already done!)
4. Restart backend: `./start_gemini.sh`

### Step 6: Verify

```bash
# Test TTS
curl -X POST http://localhost:8000/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, this is working!","language":"English"}'
```

## Troubleshooting

**If you see billing errors:**

- Wait 2-3 minutes after enabling billing
- Check billing is linked at https://console.cloud.google.com/billing

**If you see 403 errors:**

- Make sure service account has "Text-to-Speech Admin" role
- Re-download the JSON key

**Cost concerns:**

- Free tier: 1M characters/month (plenty for personal use)
- After free tier: $4 per 1M characters
- You can set budget alerts at $1 to be safe

## Alternative: Disable Google Cloud TTS

If you prefer free browser TTS only, comment out in `.env`:

```env
# GOOGLE_APPLICATION_CREDENTIALS=/Users/meetpatel/Desktop/voicerag/google-cloud-key.json
```

Browser TTS works great and is 100% free!
