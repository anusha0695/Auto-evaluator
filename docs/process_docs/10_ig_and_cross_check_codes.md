# Instruction Groups & Cross-Check Codes — Complete Reference

**Source files:** `Prompts/V2_Internal_Consistency_Auditor_Enhanced.txt`, `Prompts/V3_Trap_Detector_and_Rule_Violation_Checker.txt`, `Prompts/V4_Evidence_Quality_Assessor.txt`, `src/agents/v1_schema_validator.py`

---

## Instruction Groups (IG Codes)

| IG Code | Name | What It Governs | Agent(s) |
|---|---|---|---|
| **IG-1** | Schema Structure | Segment count, page bounds (`start_page ≤ end_page`), confidence values in [0.0, 1.0] | V1 |
| **IG-2** | Administrative Exclusion & Header/Footer | Admin docs (requisitions, fax covers, consent forms) must NOT be classified as reports; page headers/footers must not be used as classification evidence | V3 |
| **IG-3** | Context Over Keywords (Evidence Quality) | Evidence snippets must show structural document context, not just isolated keywords; anchors must be meaningful structural indicators | V4 |
| **IG-4** | True Multi-Label Inclusion | All 5 document types must appear in every output; Genomic keyword trap — gene names alone (EGFR, KRAS, PCR) do not constitute a Genomic Report | V3 |
| **IG-5** | Evidence Required Rule & Routine Lab | Every non-NO_EVIDENCE type must provide at least one snippet; Quest Diagnostics / LabCorp = routine lab (must NOT be classified as Genomic Report) | V1, V3 |
| **IG-6** | Segment Continuity & Coverage | Segments are ordered, no gaps, no overlapping page ranges; `page_count = end_page − start_page + 1`; each segment's dominant type must have supporting evidence | V1, V2 |
| **IG-7** | Segment Composition Completeness | Every segment's `segment_composition` must contain all 5 document types exactly once — no duplicates, no missing types | V1, V2 |
| **IG-8** | Segment Share Distribution | All 5 `segment_share` values per segment must sum to **1.0 ±0.01**; MENTION_ONLY types should not exceed **0.10** share individually | V2 |
| **IG-9** | Presence Level Consistency (Segment ↔ Mixture) | `document_mixture.presence_level` for each type must match the **strongest** presence seen across all segments (e.g. if PRIMARY in any segment → must be PRIMARY in mixture) | V2 |
| **IG-10** | Overall Share Consistency | `overall_share` in `document_mixture` must roughly correspond to the page-count-weighted sum of `segment_share` values across all segments | V2 |

---

## Cross-Check Codes (X Codes)

| X Code | Name | What It Checks | Agent |
|---|---|---|---|
| **X1** | Genomic Keyword Trap | Genomic Report flagged as PRIMARY/EMBEDDED_RAW based only on gene names or sequencing terms — without lab report structure (no accession number, no methodology section, no lab signature) | V2, V3 |
| **X2** | Pathology "Final Diagnosis" Trap | Pathology Report flagged as PRIMARY/EMBEDDED_RAW but the evidence is a narrative diagnosis reference, not an actual pathology report — missing the classic triad: Gross Description + Microscopic Description + pathologist signature | V3 |
| **X3** | Genomic vs Pathology Overlap Trap | When both Genomic and Pathology content are present in a document, Genomic must be PRIMARY and Pathology must be EMBEDDED_RAW — not the reverse. Vendor signals from Foundation Medicine, Caris, or Tempus confirm a comprehensive genomic assay. | V3 |
| **X4** | Dominant Type Overall Logic | `dominant_type_overall` must match the type with the highest dominance score; ties broken by structural precedence | V2 |

---

## Dominance Score Formula (X4)

$$\text{dominance\_score} = \text{overall\_share} \times \text{presence\_weight}$$

| Presence Level | Presence Weight | Eligible for Dominance? |
|---|---|---|
| PRIMARY | 1.0 | ✅ Yes |
| EMBEDDED_RAW | 0.6 | ✅ Yes |
| MENTION_ONLY | — | ❌ No |
| NO_EVIDENCE | — | ❌ No |

**Tie-breaking rule:** If two dominance scores are within **0.10** of each other, apply structural precedence:

```
Clinical Note > Genomic Report > Pathology Report > Radiology Report > Other
```

**Safety override rules (cannot be broken):**
- Genomic Report or Pathology Report can **never** be dominant if they only appear as MENTION_ONLY anywhere
- If content is primarily a Clinical Note narrative → dominant must be Clinical Note, regardless of page proportions
- Administrative/form documents → dominant must be Other (never Genomic or Pathology)

---

## Confidence Caps by Rule

| Presence Level | Required Confidence |
|---|---|
| NO_EVIDENCE | Must be exactly **0.0** |
| MENTION_ONLY | Maximum **0.59** |
| EMBEDDED_RAW (not PRIMARY anywhere in doc) | Maximum **0.89** |
| PRIMARY | Up to **1.0** |

---

## MENTION_ONLY Share Cap (IG-8)

Any type with `presence_level = MENTION_ONLY` in a segment should have `segment_share ≤ 0.10` (10%).
A MENTION_ONLY type with share > 0.15 is flagged as a likely overestimation.

---

## Agent Coverage Matrix

| Code | V1 | V2 | V3 | V4 |
|---|:---:|:---:|:---:|:---:|
| IG-1 | ✅ | | | |
| IG-2 | | | ✅ | |
| IG-3 | | | | ✅ |
| IG-4 | | | ✅ | |
| IG-5 | ✅ | | ✅ | |
| IG-6 | ✅ | ✅ | | |
| IG-7 | ✅ | ✅ | | |
| IG-8 | | ✅ | | |
| IG-9 | | ✅ | | |
| IG-10 | | ✅ | | |
| X1 | | ✅ | ✅ | |
| X2 | | | ✅ | |
| X3 | | | ✅ | |
| X4 | | ✅ | | |

---

## Issue ID Prefixes by Agent

| Agent | Issue ID Prefix | Example |
|---|---|---|
| V1 Schema Validator | `V1-XXXX` | `V1-0001` |
| V2 Consistency Checker | `V2-XXXX` | `V2-0003` |
| V3 Trap Detector | `V3-XXXX` | `V3-0002` |
| V4 Evidence Quality | `V4-XXXX` | `V4-0001` |

---

## Example Issue Object Format

```json
{
  "ig_id": "IG-8",
  "issue_id": "V2-0001",
  "severity": "MAJOR",
  "location": {
    "segment_index": 2,
    "field": "segment_share"
  },
  "message": "Segment 2 shares sum to 1.06 instead of 1.0 (Genomic=0.50, Clinical=0.30, Pathology=0.10, Radiology=0.08, Other=0.08)",
  "suggested_fix": "Normalize shares: divide each value by 1.06",
  "auto_fixable": true
}
```

---

## Quick Lookup: Which IG/X Catches Which Error?

| Error Scenario | Code | Severity |
|---|---|---|
| `number_of_segments` mismatch | IG-1 | BLOCKER |
| Page number out of bounds | IG-1 | BLOCKER |
| Confidence not in [0.0, 1.0] | IG-1 | BLOCKER |
| Segment page range overlaps another | IG-6 | BLOCKER |
| Missing document type in segment composition | IG-7 | BLOCKER |
| Segment share sum ≠ 1.0 | IG-8 | MAJOR (auto-fix) |
| Mixture share sum ≠ 1.0 | IG-8 | MAJOR (auto-fix) |
| MENTION_ONLY share > 0.15 | IG-8 | MINOR |
| Presence level segment ≠ mixture | IG-9 | BLOCKER |
| Overall share inconsistent with segments | IG-10 | MAJOR |
| Quest/LabCorp + Genomic PRIMARY | IG-5 | BLOCKER |
| Admin requisition classified as report | IG-2 | BLOCKER |
| Header/footer text used as evidence | IG-2 | MINOR |
| Gene names only → Genomic PRIMARY/EMBEDDED | X1 / IG-4 | MAJOR |
| Narrative diagnosis → Pathology PRIMARY | X2 | MAJOR |
| Genomic + Pathology → Pathology dominant | X3 | MAJOR |
| Wrong dominant_type_overall | X4 | BLOCKER |
| Evidence snippet missing for non-NO_EVIDENCE | IG-5 / IG-3 | BLOCKER |
| Evidence snippet too vague or too long | IG-3 | MAJOR / MINOR |
| Anchor not meaningful (e.g. "patient", page #) | IG-3 | MINOR |
| MENTION_ONLY confidence > 0.59 | IG-3 | MAJOR |
| NO_EVIDENCE confidence ≠ 0.0 | IG-3 | MAJOR |
