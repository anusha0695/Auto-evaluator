# Authentication Options for Gemini

## Option 1: Application Default Credentials (ADC) - RECOMMENDED

Use your existing `gcloud auth` without needing explicit keys.

**Pros:**
- ✅ No API key to manage
- ✅ Uses existing `gcloud auth application-default login`
- ✅ More secure (no keys in files)
- ✅ Works with GenAI SDK

**Setup:**
```bash
gcloud auth application-default login
```

**In code:** GenAI SDK automatically detects ADC, no changes needed!

---

## Option 2: Service Account Key File

Use the service account you already created.

**Pros:**
- ✅ Production-ready
- ✅ Can be deployed to servers
- ✅ Fine-grained permissions

**Cons:**
- ⚠️ Requires billing on GCP project
- ⚠️ Need to manage key file securely

**Setup:**
You already have this: `~/clinical-classifier-key.json`

---

## Option 3: Google AI API Key (Current)

Direct API key from AI Studio.

**Pros:**
- ✅ Simplest setup
- ✅ Free tier available
- ✅ No billing required

**Cons:**
- ⚠️ Less secure (key in .env file)
- ⚠️ Not recommended for production

---

## Recommendation: Use ADC

Since you already have `gcloud auth` configured, just use ADC!

**Changes needed:**
1. Make API key optional in config
2. GenAI SDK will automatically use ADC if no API key is provided

**Command:**
```bash
# Just ensure you're authenticated
gcloud auth application-default login

# Then run
python run_classification.py
```

Would you like me to update the code to support ADC?
