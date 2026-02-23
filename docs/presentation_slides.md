# Agentic Evaluation System — Presentation Slides

---

## SLIDE 1 — System Overview

### Agentic Evaluation System for Clinical Document Classification

**What it does:**
A multi-agent pipeline that verifies, validates, and quality-controls AI-generated clinical document classifications before they are accepted as ground truth.

**Pipeline at a glance:**

```
PDF → Document AI → Primary Classifier → [V1 → V2 → V3 → V4] → V5 Arbiter
                                                                      ↓
                                              AUTO_ACCEPT / AUTO_RETRY / ESCALATE_TO_SME
```

**5 Document Types Classified:**
| Type | Example |
|---|---|
| Clinical Note | Physician progress notes, discharge summaries |
| Pathology Report | Biopsy results, surgical pathology |
| Genomic Report | NGS panel, BRCA sequencing results |
| Radiology Report | CT scan, MRI reads |
| Other | Administrative forms, fax cover sheets |

> ⚠️ **KEY POINT:** No single agent makes the final call. Every classification goes through 4 independent verification agents before a decision is made.

---

## SLIDE 2 — Primary Classifier Agent

### What It Does
The first LLM agent that reads the PDF and produces a structured `ClassificationOutput`.

**Inputs:**
- Raw PDF text (formatted page by page from `DocumentBundle`)
- Gemini LLM prompt: `primary_classifier_agent_prompt.txt`

**Outputs — `ClassificationOutput` contains:**
| Field | Description |
|---|---|
| `dominant_type_overall` | Single dominant document type for the whole PDF |
| `segments` | Page-range segments, each with all 5 doc type classifications |
| `document_mixture` | Overall share of each doc type across the full document |
| `vendor_signals` | Detected lab/vendor names (e.g., "Quest Diagnostics") |
| `number_of_segments` | How many logical segments the document was split into |
| `self_evaluation` | LLM's own assessment of its classification |

**Per-segment output (for each of the 5 doc types):**
- `presence_level`: PRIMARY / EMBEDDED_RAW / MENTION_ONLY / NO_EVIDENCE
- `confidence`: 0.0–1.0
- `segment_share`: fraction of segment belonging to this type
- `top_evidence`: text snippets + anchors from the PDF

> ⚠️ **KEY POINT:** The classifier must assign ALL 5 document types to EVERY segment — even if a type has 0% share and NO_EVIDENCE. This completeness requirement is enforced by V1.

**Example:**
```
PDF: 8-page document — pages 1-5 are a genomic sequencing report,
     pages 6-8 are a clinical note from the ordering physician.

Segment 1 (pages 1–5):
  dominant_type: Genomic Report
  Genomic Report  → PRIMARY,    confidence: 0.92, share: 0.85
  Clinical Note   → MENTION_ONLY, confidence: 0.30, share: 0.10
  Pathology Report → NO_EVIDENCE, confidence: 0.00, share: 0.02
  Radiology Report → NO_EVIDENCE, confidence: 0.00, share: 0.02
  Other           → NO_EVIDENCE, confidence: 0.00, share: 0.01

Segment 2 (pages 6–8):
  dominant_type: Clinical Note
  Clinical Note   → PRIMARY,    confidence: 0.88, share: 0.90
  ...
```

---

## SLIDE 3 — Document Ingestion: Layout Parser & DocumentBundle

### What It Does
Before any AI classification happens, the raw PDF must be converted into structured, machine-readable text.
We use **Google Cloud Document AI — Layout Parser processor** for this.

**Why not just extract plain text?**
- Clinical PDFs contain tables, multi-column layouts, headers/footers, embedded forms
- Plain PDF text extraction loses structure and mixes up content across columns
- Layout Parser understands the **2D visual structure** of the page and extracts semantically grouped blocks

---

**What Layout Parser Extracts:**

| Element | What it is | How we use it |
|---|---|---|
| `text_block` | Paragraphs, headings, body text | Primary text content per page |
| `table_block` | Tables (e.g., lab result panels) | Detected as structured data; has_tables flag set |
| `block_type` | heading / paragraph / list item | Metadata for layout understanding |
| Page spans | Which pages each block belongs to | Used to assign text to correct page numbers |

---

**Extraction Process:**

```
PDF (binary)
    → Document AI Layout Parser
        → documentLayout.blocks (recursive tree)
            → text_block   → extract text → append to page paragraphs
            → table_block  → recurse into rows/cells → extract cell text
        → No blocks? → fallback to OCR (legacy page extraction)
    → pages_dict (keyed by page_num)
    → Sorted list of page dicts
```

**Fallback:** If Layout Parser returns no structured blocks, the system falls back to raw OCR text extraction from `document.pages`.

---

**Output — `DocumentBundle` structure:**

```json
{
  "doc_id": "doc2_6",
  "file_path": "/data/input/raw_documents/doc2_6.pdf",
  "total_pages": 8,
  "processing_timestamp": "2025-02-18T14:30:00Z",
  "pages": [
    {
      "page_num": 1,
      "text": "GENOMIC SEQUENCING REPORT\nPatient: John Doe...",
      "paragraphs": [
        "GENOMIC SEQUENCING REPORT",
        "Patient: John Doe  DOB: 01/15/1970",
        "Specimen: Blood  Collected: 02/01/2025",
        "BRCA1/2 Analysis — Full Gene Sequencing"
      ],
      "layout_metadata": {
        "block_types": ["heading", "paragraph", "paragraph", "heading"],
        "has_tables": false
      }
    },
    {
      "page_num": 2,
      "text": "VARIANT FINDINGS\n...",
      "paragraphs": [...],
      "layout_metadata": { "block_types": [...], "has_tables": true }
    }
  ]
}
```

> ⚠️ **KEY POINT:** The `DocumentBundle` is the **single source of truth** for actual PDF content. Every downstream agent (V2, V4) and the SME review interface reads from this — not from the classifier's claims. This is what makes hallucination detection possible.

> ⚠️ **KEY POINT:** The `has_tables` flag and `paragraphs` list give agents fine-grained context. V4 uses individual paragraphs for the 2-before / 3-after evidence context window shown to SMEs.

---

## SLIDE 4 — V1: Schema & Completeness Validator

### What It Does
**Type: Pure rule-based — ZERO LLM cost**

Validates the structural correctness of the `ClassificationOutput` before any expensive LLM checks run.

**5 Checks Performed:**

| # | Check | Severity | Auto-Fix? |
|---|---|---|---|
| 1 | `number_of_segments` matches actual segment count | BLOCKER | ✅ Yes |
| 2 | All page numbers within 1..total_pages, start ≤ end | BLOCKER | ❌ No |
| 3 | Wrong `segment_page_count` (end - start + 1) | MAJOR | ✅ Yes |
| 4 | All confidence values in [0.0, 1.0] | BLOCKER | ❌ No |
| 5 | All 5 document types present in every segment + mixture | BLOCKER | ✅ Yes |
| 6 | Evidence missing for non-NO_EVIDENCE types | MINOR | ❌ No |

> ⚠️ **KEY POINT:** V1 catches structural corruption — if the LLM hallucinated a segment count or returned out-of-range page numbers, V1 stops the pipeline immediately with a BLOCKER before any LLM money is spent.

**Example — Issue Caught:**
```
ClassificationOutput says:  number_of_segments = 3
Actual segments array has:  2 items

→ V1 raises:
  Issue ID:  V1-0001
  Severity:  BLOCKER
  Message:   "number_of_segments is 3 but segments array has 2 items"
  Auto-fixable: True
  IG Code:   IG-1
```

**Example — Evidence Alignment:**
```
Segment 1, Genomic Report:
  presence_level = PRIMARY   ← claims it's present
  top_evidence = []          ← but no evidence provided!

→ V1 raises:
  Issue ID:  V1-0004
  Severity:  MINOR
  Message:   "Genomic Report is PRIMARY but has no evidence snippets"
```

---

## SLIDE 4 — V2: Internal Consistency Checker

### What It Does
**Type: Hybrid — fast rules first, then LLM semantic check**

Ensures the classification is internally self-consistent — mathematically and semantically.

**Phase 1 — Rule Checks (Zero LLM cost):**

| Check | Condition | Severity |
|---|---|---|
| Segment shares sum | Each segment's 5 `segment_share` values must sum to 1.0 ±0.01 | MAJOR (auto-fix) |
| Mixture shares sum | All 5 `overall_share` values must sum to 1.0 ±0.01 | MAJOR (auto-fix) |
| Page range overlap | No two segments can share the same page | BLOCKER |

**Phase 2 — LLM Semantic Check (Gemini call):**
- Receives: full `ClassificationOutput` JSON + **complete page text** for every segment
- Checks: does the text actually match the labels? (e.g., segment labelled "Genomic Report" but text is all clinical notes)
- Returns: JSON array of issues

> ⚠️ **KEY POINT:** If Phase 1 finds a BLOCKER, Phase 2 is **skipped entirely** — saving an LLM call. The LLM only runs when the structure is sound.

**Example — Share Sum Error:**
```
Segment 2 composition shares:
  Genomic Report:   0.50
  Clinical Note:    0.30
  Pathology Report: 0.10
  Radiology Report: 0.08
  Other:            0.08
  TOTAL:            1.06  ← exceeds 1.0!

→ V2 raises:
  Issue ID:  V2-0001
  Severity:  MAJOR
  Message:   "Segment 2 shares sum to 1.060 instead of 1.0"
  Auto-fixable: True  → AutoFixEngine normalises to sum=1.0
```

**Example — Semantic Inconsistency (LLM):**
```
Segment 1 labelled: Genomic Report → PRIMARY (confidence 0.91)
Actual page text:   "CBC with differential... WBC 8.2... Hemoglobin 13.4..."
                    (routine blood panel, not genomic sequencing)

→ V2-LLM raises:
  Severity: MAJOR
  Message:  "Segment 1 text contains routine lab values inconsistent
             with Genomic Report PRIMARY classification"
```

---

## SLIDE 5 — V3: Trap Detector & Rule Violation Checker

### What It Does
**Type: Hybrid — domain-specific pattern matching + LLM contextual analysis**

Catches classification "traps" — domain-specific mistakes that look correct on the surface but are clinically wrong.

**Phase 1 — 3 Rule-Based Traps:**

**Trap 1: Routine Lab Vendor + Genomic PRIMARY**
- Vendors checked: Quest Diagnostics, LabCorp, Lab Corp
- If these vendors appear in `vendor_signals` AND Genomic Report is PRIMARY → BLOCKER
- *Why:* Quest/LabCorp produce routine blood panels, not genomic sequencing

**Trap 2: Administrative Keywords + Report Classification**
- Keywords: "requisition", "authorization number", "fax cover", "test request", "specimen receipt"
- If these appear in the document AND a report type is classified as non-NO_EVIDENCE → BLOCKER
- *Why:* These are admin forms, not clinical reports

**Trap 3: Header/Footer Content in Evidence**
- Regex patterns: `page X of Y`, fax numbers, `MRN`, `date of birth DD/MM/YYYY`
- If evidence snippets match these → MINOR
- *Why:* Page headers are not meaningful classification evidence

**Phase 2 — LLM Contextual Analysis:**
- Uses first 4,000 characters of document text
- Catches subtle traps pattern matching misses

> ⚠️ **KEY POINT:** V3 encodes **clinical domain knowledge** as rules. A general-purpose LLM might not know that Quest Diagnostics = routine lab, not genomic lab. These rules prevent systematic misclassification.

**Example — Trap 1 Triggered:**
```
Document: Routine CBC panel from Quest Diagnostics
vendor_signals: ["Quest Diagnostics"]
document_mixture: Genomic Report → PRIMARY (confidence 0.78)
  (LLM was confused by gene-like column headers: "WBC", "RBC", "PLT")

→ V3 raises:
  Issue ID:  V3-0001
  Severity:  BLOCKER
  Message:   "Routine lab vendor detected (Quest Diagnostics) but
               Genomic Report marked PRIMARY"
  Suggested: "Reclassify as 'Other' or downgrade to MENTION_ONLY"
```

**Example — Trap 2 Triggered:**
```
Document: Lab requisition form with "Test Request Authorization #4821"
document_mixture: Pathology Report → EMBEDDED_RAW

→ V3 raises:
  Severity: BLOCKER
  Message:  "Administrative keywords found ('test request') but
              Pathology Report marked EMBEDDED_RAW"
```

---

## SLIDE 6 — V4: Evidence Quality Assessor

### What It Does
**Type: Full LLM — independent verification against actual PDF source text**

The most rigorous agent. It does NOT trust the classifier's evidence — it independently cross-checks every evidence snippet against the raw PDF text extracted by Document AI.

**What the LLM receives:**
1. Full `ClassificationOutput` JSON (classifier's claims)
2. Actual PDF text per page from `DocumentBundle` (ground truth text)

**4 Tasks the LLM Performs:**

| Task | What it checks |
|---|---|
| Evidence quality | Are snippets specific, relevant, appropriately sized? |
| Snippet verification | Does the snippet text actually exist in the PDF page? |
| Anchor verification | Are the `anchors_found` strings present on the claimed page? |
| Fabrication detection | Any snippet that cannot be found in the source PDF |

**Scoring:**
```
quality_score = 1.0
  - 0.30 per BLOCKER issue
  - 0.15 per MAJOR issue
  - 0.05 per MINOR issue
(minimum 0.0)
```

> ⚠️ **KEY POINT:** V4 is the **hallucination detector**. LLMs sometimes generate plausible-sounding evidence snippets that don't actually exist in the document. V4 catches this by comparing against the raw Document AI output.

**Example — Fabricated Evidence:**
```
Classifier claims:
  Evidence snippet: "BRCA1 pathogenic variant c.5266dupC detected"
  Page: 3, Anchor: "Variant Classification"

V4 checks actual page 3 text from DocumentBundle:
  Page 3 actual text: "Patient history reviewed. No prior genetic testing.
                       Family history: mother with breast cancer age 52."

→ V4 raises:
  Severity: BLOCKER
  Message:  "Evidence snippet 'BRCA1 pathogenic variant...' not found
              in actual PDF text on page 3. Possible hallucination."
```

**Example — Weak Evidence:**
```
Classifier claims:
  Genomic Report → PRIMARY (confidence 0.85)
  Evidence: "See attached results" (page 2)

→ V4 raises:
  Severity: MAJOR
  Message:  "Evidence snippet 'See attached results' is a generic
              reference, not specific genomic evidence. Confidence
              0.85 is not supported by this evidence quality."
```

---

## SLIDE 7 — V5: Decision Maker (Arbiter)

### What It Does
**Type: Pure rule-based — ZERO LLM cost, fully deterministic**

Reads the consolidated issues from V1–V4 and makes the final disposition decision.

**Decision Rules (evaluated in priority order):**

| Priority | Condition | Decision | Rationale |
|---|---|---|---|
| 1 | Any BLOCKER issue | 🔴 ESCALATE_TO_SME | Critical failure — cannot auto-correct |
| 2 | ≥ 3 MAJOR issues | 🔴 ESCALATE_TO_SME | Too many errors for auto-correction |
| 3 | ≥ 2 non-fixable MAJOR | 🔴 ESCALATE_TO_SME | Requires human judgment |
| 4 | ≥ 1 non-fixable MAJOR | 🔴 ESCALATE_TO_SME | Conservative — any human-needed issue escalates |
| 5 | 1–2 fixable MAJOR | 🟡 AUTO_RETRY | AutoFixEngine can correct these |
| 6 | Only MINOR issues | 🟢 AUTO_ACCEPT | Tolerable, doesn't affect validity |
| 7 | No issues | 🟢 AUTO_ACCEPT | Perfect output |
| 8 | Ambiguous | 🔴 ESCALATE_TO_SME | Safety fallback |

> ⚠️ **KEY POINT:** V5 is intentionally **conservative** — even a single non-fixable MAJOR issue triggers escalation. The system is designed to over-escalate rather than silently accept a bad classification.

> ⚠️ **KEY POINT:** V5 makes **NO Gemini API call**. It is pure Python if/else logic — deterministic and auditable. The same issue set always produces the same decision.

**Example — AUTO_RETRY:**
```
V1–V4 Issues found:
  [MAJOR, auto_fixable=True]  "Segment 1 shares sum to 1.06 instead of 1.0"
  [MAJOR, auto_fixable=True]  "Mixture overall_share sums to 0.97 instead of 1.0"
  [MINOR, auto_fixable=False] "Genomic Report has no evidence snippets"

V5 counts: blocker=0, major=2 (both fixable), minor=1
→ Rule 5 matches: 1–2 fixable MAJOR
→ Decision: AUTO_RETRY
→ AutoFixEngine normalises shares → re-verify
```

**Example — ESCALATE_TO_SME:**
```
V1–V4 Issues found:
  [BLOCKER] "Routine vendor Quest Diagnostics but Genomic Report is PRIMARY"

V5 counts: blocker=1
→ Rule 1 matches immediately
→ Decision: ESCALATE_TO_SME
→ SME packet generated
```

---

## SLIDE 8 — Retry Orchestrator & Auto-Fix Engine

### What It Does
Manages the verification retry loop — applies automatic mathematical fixes and re-verifies, with safeguards against infinite loops.

**Retry Loop:**
```
Attempt 0 → Verify → AUTO_RETRY → Fix → Attempt 1 → Verify → AUTO_RETRY → Fix → Attempt 2 → Verify
                                                                                        ↓
                                                                              If still AUTO_RETRY:
                                                                              → ESCALATE_TO_SME
                                                                              (MAX_RETRIES = 2)
```

**Auto-Fix Types:**

| Fix | What it does | Triggered by |
|---|---|---|
| Segment share normalisation | Divides each of 5 `segment_share` values by their sum → forces total = 1.0 | V2 share sum error |
| Mixture share normalisation | Divides each `overall_share` by their sum → forces total = 1.0 | V2 mixture sum error |

**Cycle Detection:**
- MD5 fingerprint of: segment boundaries + dominant types + all share values
- If same fingerprint seen twice → immediately escalate (fix didn't change anything)

> ⚠️ **KEY POINT:** The retry loop prevents wasting LLM calls on a classification that can't be fixed. Max 3 total verification attempts (attempt 0, 1, 2). If still broken after 2 fixes → human review.

**Example — Successful Auto-Fix:**
```
Attempt 0:
  V2 finds: Segment 1 shares sum to 1.06 (MAJOR, auto_fixable)
  V5 decides: AUTO_RETRY

AutoFixEngine:
  Before: [0.50, 0.30, 0.10, 0.08, 0.08] → sum=1.06
  After:  [0.472, 0.283, 0.094, 0.075, 0.075] → sum=1.000

Attempt 1:
  V1–V4: No issues found
  V5 decides: AUTO_ACCEPT ✅
```

---

## SLIDE 9 — SME Packet Generation

### What It Does
When V5 decides `ESCALATE_TO_SME`, a structured review packet is generated containing everything a Subject Matter Expert needs to make a classification decision — without having to look at the raw code.

**What's in the SME Packet:**

| Section | Contents |
|---|---|
| Document info | PDF filename, path, page count |
| Primary agent classification | Full `ClassificationOutput` (segments, evidence, mixture) |
| Issues summary | All V1–V4 issues sorted: BLOCKER → MAJOR → MINOR |
| Production comparison | Whether production classifier agrees/disagrees |
| Review status | `PENDING` until SME completes review |
| Document bundle path | Path to extracted PDF text for context lookup |

**Issues are formatted for human readability:**
```
[BLOCKER] V3-0001 (Agent: V3)
  Message:   Routine lab vendor detected (Quest Diagnostics) but
             Genomic Report marked PRIMARY
  Location:  document_mixture → Genomic Report
  Fix:       Reclassify as 'Other' or downgrade to MENTION_ONLY
```

> ⚠️ **KEY POINT:** The packet is saved as JSON to `output/sme_packets/sme_packet_{doc_id}.json`. The SME never needs to run code — they work entirely through the Jupyter notebook review interface.

**Example Packet Summary:**
```json
{
  "doc_id": "doc2_6",
  "pdf_filename": "doc2_6.pdf",
  "v5_decision": "ESCALATE_TO_SME",
  "total_issues": 3,
  "review_status": "pending",
  "production_differs": true,
  "issues_summary": [
    {"severity": "BLOCKER", "agent": "V3", "message": "Routine vendor..."},
    {"severity": "MAJOR",   "agent": "V4", "message": "Evidence snippet not found..."},
    {"severity": "MINOR",   "agent": "V1", "message": "Missing evidence for..."}
  ]
}
```

---

## SLIDE 10 — SME Review Interface & Feedback Loop

### What It Does
The Jupyter notebook interface where a clinician/SME reviews escalated cases, provides corrections, and creates the final ground truth record.

**Review Workflow:**

```
1. List pending reviews   → SMEReviewHelper.list_pending_reviews()
2. Load packet            → SMEReviewHelper.load_packet("doc2_6")
3. View issues + context  → get_issue_context() per issue
4. Make decision          → agrees / corrects
5. Save review            → save_review()
6. Ground truth created   → output/ground_truth/gt_doc2_6.json
```

**Context Shown to SME per Issue:**
- Segment info (page range, dominant type)
- Classification reasoning from the LLM
- Evidence snippets + anchors
- **Actual PDF text: 2 paragraphs before + 3 paragraphs after** the matched evidence location

> ⚠️ **KEY POINT:** The SME sees the **actual PDF text** from Document AI output — not just the LLM's claimed evidence. This lets them independently verify whether the evidence is real and relevant.

**Two Outcomes:**

| SME Decision | Ground Truth Source | What's stored |
|---|---|---|
| Agrees with primary agent | `SME_VALIDATED` | Primary agent's classification as-is |
| Corrects classification | `SME_CORRECTED` | SME's corrected dominant type, segments, mixture |

**Example — SME Corrects:**
```
Primary agent classified: Genomic Report → PRIMARY
SME reviews and sees:     It's actually a routine Quest CBC panel

SME provides correction:
  corrected_dominant_type: "Other"
  correction_notes: "This is a routine CBC from Quest, not a genomic report.
                     Gene-like column headers (WBC, RBC) confused the classifier."

Ground truth saved:
  ground_truth_source: SME_CORRECTED
  ground_truth_classification: dominant_type = "Other"
```

**Example — SME Validates:**
```
Primary agent classified: Pathology Report → PRIMARY
SME reviews and confirms: Correct — it's a surgical biopsy report

Ground truth saved:
  ground_truth_source: SME_VALIDATED
  ground_truth_classification: (primary agent output unchanged)
```

---

## SLIDE 11 — Flagged Important Design Decisions

### Why This Architecture?

| Design Choice | Reason |
|---|---|
| **V1 runs first, no LLM** | Catch structural errors cheaply before spending on LLM calls |
| **V2 skips LLM if BLOCKER found** | Don't waste API calls on structurally broken output |
| **V3 encodes clinical domain rules** | General LLMs don't know Quest = routine lab, not genomic |
| **V4 cross-checks against raw PDF text** | Detects LLM hallucination of evidence snippets |
| **V5 is pure rule-based** | Deterministic, auditable, reproducible — same input = same decision always |
| **MAX_RETRIES = 2** | Prevents infinite fix loops; 3 attempts is enough for mathematical fixes |
| **MD5 cycle detection** | Prevents AutoFixEngine from applying the same fix repeatedly with no effect |
| **Conservative escalation** | Even 1 non-fixable MAJOR → escalate. Over-escalate rather than silently accept bad output |
| **SME sees actual PDF text** | SME can independently verify evidence, not just trust the LLM's claims |

### LLM Call Budget per Document

| Agent | LLM Calls | When |
|---|---|---|
| Primary Classifier | 1 | Always |
| V1 Schema Validator | 0 | Always |
| V2 Consistency Checker | 0 or 1 | 0 if BLOCKER in rules, else 1 |
| V3 Trap Detector | 0 or 1 | 1 always (rules + LLM) |
| V4 Evidence Quality | 1 | Always |
| V5 Arbiter | 0 | Always |
| **Total (best case)** | **2** | AUTO_ACCEPT, no rule BLOCKERs |
| **Total (worst case)** | **3 per attempt × 3 attempts = 9** | MAX_RETRY path |
