# Manual SME Packet Generation Guide

## Which PDF Creates an SME Packet?

**Answer:** `doc2_6.pdf` 

This document gets escalated by V5 Arbiter with `ESCALATE_TO_SME` decision because it has 1 MAJOR issue detected by the verification agents.

**Location:** `data/input/raw_documents/doc2_6.pdf`

---

## How to Generate SME Packet Manually (Step-by-Step)

### Prerequisites

```bash
cd /Users/maverick/Documents/Anusha/Unstructured/agentic_evaluation
source venv_new/bin/activate
```

---

### Step 1: Run Classification Pipeline

This runs the primary agent classifier and V1-V5 verification:

```bash
python run_classification.py data/input/raw_documents/doc2_6.pdf
```

**What this does:**
- Extracts text from PDF
- Runs primary classifier agent
- Runs V1-V5 verification agents
- V5 Arbiter makes decision

**Output files created:**
- `output/classification_result.json` - Primary agent classification
- `output/classification_result_verification.json` - V1-V5 verification report

---

### Step 2: Check V5 Decision

Verify that V5 decided to escalate:

```bash
cat output/classification_result_verification.json | grep -A 5 '"arbiter_decision"'
```

**Expected output:**
```json
"arbiter_decision": {
  "decision": "ESCALATE_TO_SME",
  "reason": "Found 1 non-fixable MAJOR issue(s). Human expertise needed to resolve.",
  ...
}
```

---

### Step 3: Generate SME Packet

Only if Step 2 shows `ESCALATE_TO_SME`, run:

```bash
python -c "
import json
from pathlib import Path
from src.schemas import ClassificationOutput, VerificationReport, ArbiterDecision
from src.evaluation.packet_generator import SMEPacketGenerator
from src.production_classifier import ProductionClassifier

# Load classification and verification results
with open('output/classification_result.json') as f:
    classif = ClassificationOutput(**json.load(f))

with open('output/classification_result_verification.json') as f:
    verif_data = json.load(f)
    arbiter = ArbiterDecision(**verif_data['arbiter_decision'])
    verif = VerificationReport(
        issues=verif_data.get('issues', []),
        v1_validation_passed=verif_data['v1_validation_passed'],
        v2_consistency_score=verif_data['v2_consistency_score'],
        v3_traps_triggered=verif_data['v3_traps_triggered'],
        v4_evidence_quality_score=verif_data['v4_evidence_quality_score'],
        has_blocker_issues=verif_data['has_blocker_issues'],
        total_issues=verif_data['total_issues'],
        llm_calls_made=verif_data['llm_calls_made'],
        arbiter_decision=arbiter,
        retry_log=verif_data.get('retry_log', [])
    )

# Optional: Run production classifier for comparison
prod_classifier = ProductionClassifier()
prod_result = prod_classifier.classify('data/input/raw_documents/doc2_6.pdf')

# Generate SME packet
generator = SMEPacketGenerator()
packet = generator.generate_packet(
    pdf_path='data/input/raw_documents/doc2_6.pdf',
    primary_classification=classif,
    verification_report=verif,
    arbiter_decision=arbiter,
    production_result=prod_result
)

# Save packet
saved_path = generator.save_packet(packet)
print(f'✅ SME Packet saved to: {saved_path}')
"
```

---

### Step 4: Verify SME Packet Created

```bash
ls -lh output/sme_packets/
cat output/sme_packets/sme_packet_doc2_6.json
```

**SME Packet JSON Structure:**
```json
{
  "doc_id": "doc2_6",
  "pdf_filename": "doc2_6.pdf",
  "pdf_path": "/absolute/path/to/doc2_6.pdf",
  "total_pages": 2,
  "primary_agent_classification": { ... },
  "v5_decision": "ESCALATE_TO_SME",
  "total_issues": 1,
  "issues_summary": [
    {
      "id": "issue_id",
      "agent": "V3",
      "severity": "MAJOR",
      "message": "...",
      "location": "...",
      "suggested_fix": "..."
    }
  ],
  "production_classification": {
    "dominant_type": "Genomic Report",
    "all_types": ["Genomic Report"],
    "vendor": "Unknown"
  },
  "production_differs": false,
  "review_status": "pending",
  "created_at": "2026-02-16T19:42:00",
  "updated_at": null
}
```

---

## Simplified One-Command Option

Instead of the multi-step manual process, use the integrated test script:

```bash
python test_phase6_simple.py
```

This automatically:
1. Runs classification on `doc2_6.pdf`
2. Runs production classifier
3. Checks V5 decision
4. Generates SME packet (if ESCALATE_TO_SME)

**Output:** `output/sme_packets/sme_packet_doc2_6.json`

---

## Why doc2_6.pdf Creates an SME Packet

This document has a **MAJOR issue** detected by **V3 Trap Detector**:
- Issue: Pathology Report classified as EMBEDDED_RAW 
- Severity: MAJOR (non-fixable via auto-retry)
- V5 Decision: Manual SME review required

Other test documents like `doc_3.pdf` result in `AUTO_ACCEPT` (no issues), so they don't create SME packets.

---

## File Locations Summary

| What | Path |
|------|------|
| **Input PDF** | `data/input/raw_documents/doc2_6.pdf` |
| **Classification** | `output/classification_result.json` |
| **Verification** | `output/classification_result_verification.json` |
| **SME Packet** | `output/sme_packets/sme_packet_doc2_6.json` |
| **Ground Truth** | `output/ground_truth/gt_doc2_6.json` (after review) |

---

## Next Steps After Packet Generation

Once you have the SME packet, you can:

1. **Review programmatically:**
   ```bash
   python test_sme_interface.py
   ```

2. **Review in Jupyter:**
   ```bash
   jupyter lab notebooks/sme_review_interface.ipynb
   ```

3. **Submit manual review:**
   See `notebooks/SME_REVIEW_GUIDE.md`
