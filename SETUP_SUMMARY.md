# Quick Setup Summary

## What We Fixed:

1. ✅ Removed old Vertex AI config from `.env`
2. ✅ Installed `google-generativeai` SDK
3. ✅ Added back `GCP_PROJECT_ID` (needed for Document AI)
4. ⚠️ ADC lacks scopes for GenAI SDK

## Next Step - Get API Key:

**Simplest solution:** Use a Google AI API key

### Get Your API Key:
1. Go to: https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy the key

### Add to `.env`:
```bash
# Uncomment and add your key:
GOOGLE_API_KEY=your-actual-api-key-here
```

### Then Run:
```bash
python run_classification.py
```

---

## Alternative: Fix ADC Scopes (More Complex)

If you prefer ADC over API key:
```bash
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/generative-language.retriever
```

But API key is much simpler!
