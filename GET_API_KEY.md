# How to Get Google AI API Key

## Quick Steps:

1. Go to: https://aistudio.google.com/apikey

2. Click **"Create API Key"**

3. Select "Create API key in new project" (or use existing project)

4. Copy the API key

5. Add to `.env`:
   ```bash
   GOOGLE_API_KEY=your-key-here
   ```

## Benefits of GenAI SDK vs Vertex AI:

✅ No GCP billing required  
✅ Simpler authentication (just API key)  
✅ Free tier available  
✅ Works immediately

## After adding API key:

```bash
python run_classification.py
```

That's it!
