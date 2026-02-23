# Phase 1 Setup - Fix Billing and Model Access

## Issue 1: Billing Not Enabled

Your GCP project needs billing enabled to use Document AI and Vertex AI.

### Enable Billing:

1. Go to: https://console.cloud.google.com/billing/enable?project=medical-report-extraction

2. Select or create a billing account

3. Click "SET ACCOUNT"

4. Wait 2-3 minutes for billing to propagate

---

## Issue 2: Model Name Fixed

Updated `.env` to use correct model version:
- ❌ `gemini-1.5-pro` (invalid)
- ✅ `gemini-1.5-pro-002` (correct)

---

## After Enabling Billing:

Wait a few minutes, then run:

```bash
source venv_new/bin/activate
python run_classification.py
```

---

## Alternative: Use Existing Project

If you have another GCP project with billing already enabled, you can:

1. Update `.env`:
   ```bash
   GCP_PROJECT_ID=your-existing-project-id
   ```

2. Create the Document AI processor in that project instead

3. Update the processor ID in `.env`
