# Document AI Extraction Failure - Diagnosis

## Issue:
Document AI is returning **0 pages and 0 text** from the PDF, causing the LLM classifier to fail validation.

## Debug Output:
```
Document AI response - Total pages in document: 0
Document AI response - Text length: 0
Extracted 0 pages
```

## Root Cause Checklist:

### 1. ✅ PDF File Exists
```bash
-rw-r--r--@ 1 maverick  staff    11K Sep 30  2024 data/input/raw_documents/doc2_1.pdf
```
File is present (11KB).

### 2. ❓ Document AI API Enabled
Check if Document AI API is enabled:
```bash
gcloud services list --enabled --project=medical-report-extraction | grep documentai
```

### 3. ❓ Billing Enabled for Document AI
Document AI requires billing to be enabled. Even though Gemini is now working, Document AI might need separate billing activation.

### 4. ❓ Processor Configuration
Check if processor ID `81e83f6783d90bb0` exists and is correctly configured:
```bash
gcloud documentai processors list --location=us --project=medical-report-extraction
```

## Likely Solutions:

**Option 1: Enable Document AI API**
```bash
gcloud services enable documentai.googleapis.com --project=medical-report-extraction
```

**Option 2: Re-create Processor**
If the processor was deleted or misconfigured, recreate it via the console or gcloud CLI.

**Option 3: Check Billing**
Ensure the project has billing enabled and linked to an active billing account:
https://console.cloud.google.com/billing/projects

## Next Steps:
Run the diagnostic commands above to identify which service is missing/misconfigured.
