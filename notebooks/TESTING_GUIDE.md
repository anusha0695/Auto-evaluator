# Complete SME Review Testing Guide

## Overview

Test both the SME packet generation and the review interface to ensure the complete workflow works end-to-end.

---

## Quick Test (Automated)

```bash
# Test programmatically (no Jupyter needed)
source venv_new/bin/activate
python test_sme_interface.py
```

This will:
1. Check review queue
2. Load an SME packet
3. Display classification & issues
4. Submit a test review
5. Create ground truth
6. Verify completion

---

## Full Test Walkthrough

### Part 1: Generate SME Packet

**Method 1: Using test_phase6_simple.py (Recommended)**

```bash
source venv_new/bin/activate
python test_phase6_simple.py
```

This runs the complete flow:
- Classification → Verification → SME packet (if ESCALATE_TO_SME)

**Method 2: Manual step-by-step**

```bash
# Step 1: Classify document
python run_classification.py data/input/raw_documents/doc2_6.pdf

# Step 2: Check if escalated
cat output/classification_result_verification.json | grep decision

# Step 3: If ESCALATE_TO_SME, generate packet
python test_phase6_simple.py
```

**Verify packet created:**
```bash
ls -lh output/sme_packets/
cat output/sme_packets/sme_packet_doc2_6.json | jq .
```

---

### Part 2: Test Review Interface (Programmatic)

```bash
python test_sme_interface.py
```

**Expected Output:**
```
========================================
SME REVIEW INTERFACE TEST
========================================

📋 Step 1: Checking Review Queue...
   Total Packets: 1
   Pending: 1
   Completed: 0
   
   Pending Documents:
     • doc2_6 - 1 issue(s)

📦 Step 2: Loading Packet...
   ✅ Loaded: doc2_6
   
🏥 Step 3: Primary Agent Classification...
   Dominant Type: Genomic Report
   
⚠️  Step 4: Issues (1)...
   1. [MAJOR] V3
   
✍️  Step 5: Submitting Test Review...
   ✅ Review saved for doc2_6
   
✅ Step 6: Verifying Ground Truth...
   Ground Truth Created
   
📊 Step 7: Updated Statistics...
   Completed: 1
   Completion Rate: 100%
   
✅ SME REVIEW INTERFACE TEST COMPLETE
```

---

### Part 3: Test Jupyter Notebook Interface

**Start Jupyter:**
```bash
source venv_new/bin/activate
jupyter lab notebooks/sme_review_interface.ipynb
```

**In the notebook:**

1. **Run Cell 1** - Setup (imports, initialize helper)
   - Should print: ✅ SME Review Interface Ready

2. **Run Cell 2** - View pending reviews
   - Should show review queue stats and pending documents

3. **Run Cell 3** - Load packet
   - Set `DOC_ID = "doc2_6"`
   - Should load packet successfully

4. **Run Cell 4** - View PDF
   - Opens PDF in iframe (if path is accessible)
   - Note: May not work in all Jupyter environments

5. **Run Cell 5** - Review classification
   - Displays primary agent's classification details

6. **Run Cell 6** - Review issues
   - Shows verification issues with severity

7. **Run Cell 7** - Production comparison
   - Shows if production classifier agrees/differs

8. **Run Cell 8** - Submit review via widgets
   - Fill in form interactively
   - OR use Cell 9 for manual submission

9. **Run Cell 10** - View ground truth
   - Verify ground truth record was created

---

## Expected Test Data

After running `test_phase6_simple.py`, you should have:

**SME Packet** (`output/sme_packets/sme_packet_doc2_6.json`):
```json
{
  "doc_id": "doc2_6",
  "pdf_filename": "doc2_6.pdf",
  "total_pages": 1,
  "v5_decision": "ESCALATE_TO_SME",
  "total_issues": 1,
  "review_status": "pending"
}
```

**After Review** (`output/ground_truth/gt_doc2_6.json`):
```json
{
  "doc_id": "doc2_6",
  "ground_truth_source": "sme_validated",
  "sme_review": {
    "reviewer_name": "Test Reviewer",
    "agrees_with_primary_agent": true,
    "confidence_in_review": 1.0
  }
}
```

---

## Verification Checklist

- [ ] SME packet generated for ESCALATE_TO_SME case
- [ ] Packet contains all required fields
- [ ] Review helper can load packet
- [ ] Issues are properly formatted with severity
- [ ] Production comparison is available (if applicable)
- [ ] Review submission works (programmatic)
- [ ] Ground truth record created
- [ ] Review status updates from "pending" to "completed"
- [ ] Stats update correctly
- [ ] Jupyter notebook loads without errors
- [ ] Interactive form works (or manual submission)

---

## Troubleshooting

**No pending reviews:**
```bash
# Generate one
python test_phase6_simple.py
```

**Jupyter doesn't start:**
```bash
# Install if missing
pip install jupyterlab ipywidgets
```

**PDF viewer doesn't work in notebook:**
- This is normal for some Jupyter environments
- PDF path must be accessible from browser
- Alternative: View PDF externally and review in notebook

**Widget form doesn't render:**
- Use Cell 9 (manual submission) instead
- Edit variables directly and run

---

## Success Criteria

✅ **SME Packet Generation:**
- Packets created for ESCALATE_TO_SME cases
- All required fields populated
- Issues formatted correctly

✅ **Review Interface:**
- Can list pending reviews
- Can load and display packet
- Can submit review (programmatic or interactive)
- Ground truth created correctly
- Stats updated

✅ **End-to-End:**
- Classification → Verification → Packet → Review → Ground Truth
- Full workflow tested and working
