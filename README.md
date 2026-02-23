# Phase 1: Document Processing & Primary Classifier

This is the foundation implementation for the clinical document classification evaluation framework.

## Quick Start

1. **Setup environment:**
```bash
cp .env.example .env
# Edit .env with your GCP credentials
```

2. **Install dependencies:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Run classification:**
```bash
python run_classification.py data/input/raw_documents/sample.pdf
```

## Project Structure

- `src/` - Core modules
  - `config.py` - Configuration management
  - `schemas.py` - Pydantic data models
  - `document_processor.py` - Document AI integration
  - `primary_classifier_agent.py` - Gemini classifier
- `tests/` - Unit and integration tests
- `Prompts/raw_text/` - Classification prompt templates
- `data/input/raw_documents/` - Sample clinical PDFs

## Configuration

Set these environment variables in `.env`:
- `GCP_PROJECT_ID` - Your GCP project  
- `DOCUMENT_AI_PROCESSOR_ID` - Document AI processor ID
- `GEMINI_MODEL` - Model name (default: gemini-1.5-pro)

## Next Phase

After testing Phase 1, we'll implement V1-V5 verification agents.
# Auto-evaluator