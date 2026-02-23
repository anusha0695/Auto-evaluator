# SME Review Interface Enhancement

## Summary
Enhanced the SME review interface to display the **actual content** of document segments/chunks where issues are detected, with highlighted evidence.

## Changes Made

### 1. Updated `review_helper.py`
**File:** `src/evaluation/review_helper.py`

**Enhancement:** Modified the `get_issue_context()` method to properly handle cases where DocumentBundle paragraphs are empty. Now it:
- Falls back to full page text when paragraphs are not available
- Shows the actual text content from the PDF (via DocumentBundle)
- Includes the evidence snippet highlighted within the context

### 2. Improved Notebook Display Code
**File:** `notebooks/sme_review_section4_updated.py`

**Enhancement:** Created updated display code for the notebook that:
- Shows the actual document text content (full page or paragraphs)
- Highlights evidence snippets in bright yellow
- Displays both page text and classification reasoning
- Uses a clear visual hierarchy with color-coded sections

## What Changed in the Display

### Before
Showed only:
- Evidence snippets as references (e.g., "Page 3: 'Immunohistochemistry Results'")
- Classification reasoning from the agent
- No actual document content

### After  
Now shows:
- **📄 Original Document Text** section
- Full page content where the issue occurs
- Evidence snippets **highlighted in bright yellow** within the actual text
- Better visual organization with distinct colored sections

## How to Use

### Option 1: Copy Updated Code into Notebook

1. Open `notebooks/sme_review_interface.ipynb`
2. Find **Section 4: Review Issues Detected**
3. Replace the code in that cell with the code from `notebooks/sme_review_section4_updated.py`
4. Re-run the notebook

### Option 2: Test the Enhancement

Run the test script to see the improvement:

```bash
cd /Users/maverick/Documents/Anusha/Unstructured/agentic_evaluation
python notebooks/test_sme_enhancement.py
```

This will show you a side-by-side comparison of old vs new display.

## Example Output

When reviewing doc2_6, you'll now see:

```
1. [MAJOR] V3
   ID: V3-0001
   Message: Pathology Report classified as EMBEDDED_RAW in segment 1...
   
┌─────────────────────────────────────────────────────────────┐
│ 📍 Context: Segment 1 (Pages 1-4) - Genomic Report         │
├─────────────────────────────────────────────────────────────┤
│ Document Type: Pathology Report                             │
│ Presence Level: EMBEDDED_RAW (Confidence: 0.75)            │
│ Segment Share: 20.0%                                        │
├─────────────────────────────────────────────────────────────┤
│ 📄 Original Document Text:                                  │
│                                                              │
│ Page 3:                                                      │
│ Gene Variants of Unknown Significance                       │
│ [Immunohistochemistry Results] ← HIGHLIGHTED!               │
│ Genes Tested with Indeterminate Results by Tumor DNA...    │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ 🔍 Classification Reasoning:                                │
│ The 'Immunohistochemistry Results' section on page 3...    │
└─────────────────────────────────────────────────────────────┘
```

## Key Benefits

1. **SMEs can now see actual content** - Not just snippets, but the full text where issues occur
2. **Visual highlighting** - Evidence is clearly marked in yellow
3. **Better context** - Full page text shows surrounding content
4. **Handles edge cases** - Works with both paragraph-based and heading-only DocumentBundles

## Technical Details

The enhancement works by:
1. Loading the DocumentBundle JSON from `output/document_bundles/bundle_{doc_id}.json`
2. Extracting text from pages within the segment range
3. Matching evidence snippets to page content
4. Displaying full page text when paragraphs are empty (common in mock/test data)
5. Using HTML formatting with inline styles for rich display in Jupyter
