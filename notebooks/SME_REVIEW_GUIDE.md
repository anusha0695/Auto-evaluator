# Quick Start Guide: SME Review Interface

## Setup

1. **Start Jupyter Lab:**
   ```bash
   cd /Users/maverick/Documents/Anusha/Unstructured/agentic_evaluation
   source venv_new/bin/activate
   jupyter lab notebooks/sme_review_interface.ipynb
   ```

2. **The notebook will open in your browser**

## Workflow

### Step 1: Check Review Queue
Run the first few cells to see pending reviews:
- View statistics (total, pending, completed)
- List documents awaiting review

### Step 2: Load Document
- Set `DOC_ID` variable to the document you want to review
- Example: `DOC_ID = "doc2_6"`

### Step 3: Review Content
- View the PDF (requires path access)
- Review primary agent classification
- Examine detected issues
- Compare with production classifier (if available)

### Step 4: Submit Review

**Option A: Interactive Widget Form**
- Fill in reviewer name
- Select "Agree" or "Need Corrections"
- Set confidence level
- Add review notes
- If correcting: enter corrected type and explanation
- Click "Submit Review"

**Option B: Manual Code Submission**
- Use cell #8 if widgets don't work
- Edit variables directly:
  ```python
  REVIEWER_NAME = "Your Name"
  AGREES_WITH_PRIMARY = True  # or False
  REVIEW_NOTES = "Your notes here"
  ```

### Step 5: Verify Ground Truth
- Run the final cell to view the created ground truth record
- Saved to: `output/ground_truth/gt_{DOC_ID}.json`

## Example Review Session

```python
# 1. Check pending
pending = helper.list_pending_reviews()
# Shows: doc2_6 - 1 issue(s)

# 2. Load packet
DOC_ID = "doc2_6"
packet = helper.load_packet(DOC_ID)

# 3. Review classification and issues
# (View in notebook cells)

# 4. Submit review
helper.save_review(
    doc_id="doc2_6",
    reviewer_name="Dr. Smith",
    agrees_with_primary=True,
    review_notes="Classification is correct",
    confidence=1.0
)
# ✅ Review saved
# ✅ Ground truth created
```

## Output Files

- **SME Packets:** `output/sme_packets/sme_packet_{doc_id}.json`
- **Ground Truth:** `output/ground_truth/gt_{doc_id}.json`

## Ground Truth Schema

Each ground truth record contains:
- Document identification
- Primary agent classification
- Production classifier result
- Verification details (V1-V5)
- SME review (reviewer, decision, corrections)
- Final validated classification
- Source tracking (SME_VALIDATED or SME_CORRECTED)

