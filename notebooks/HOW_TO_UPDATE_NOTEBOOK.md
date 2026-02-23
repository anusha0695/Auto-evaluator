# How to Update the SME Review Interface Notebook

## What Was Enhanced

Your SME review interface now displays **actual document content** where issues are detected, with evidence highlighted in yellow. Before, it only showed evidence snippets as references.

## Changes Made

1. ✅ **Updated `src/evaluation/review_helper.py`**
   - Enhanced to load full page text from DocumentBundle
   - Handles cases where paragraphs are empty
   - Extracts actual content around evidence snippets

2. 📝 **Created updated notebook code**
   - Located in: `notebooks/sme_review_section4_updated.py`
   - Shows actual document text with highlighting
   - Better visual organization

## How to Apply to Your Notebook

### Step 1: Open the Notebook
```bash
jupyter notebook notebooks/sme_review_interface.ipynb
```

### Step 2: Update Section 4
1. Find the cell titled **"## 4. Review Issues Detected"**
2. Delete the current code in that cell
3. Copy the entire code from `notebooks/sme_review_section4_updated.py`
4. Paste it into the cell
5. Save the notebook (Cmd+S or Ctrl+S)

### Step 3: Run the Updated Notebook
1. Run all cells from the beginning
2. When you reach Section 4, you'll now see:
   - 📄 **Original Document Text** section
   - Full page content with evidence **highlighted in yellow**
   - Clear visual separation between document content and reasoning

## Example of What You'll See

```
1. [MAJOR] V3
   
┌─────────────────────────────────────────────┐
│ 📍 Context: Segment 1 (Pages 1-4)          │
│                                             │
│ 📄 Original Document Text:                 │
│                                             │
│ Page 3:                                     │
│ Gene Variants of Unknown Significance      │
│ [Immunohistochemistry Results] ← YELLOW!   │
│ Genes Tested with Indeterminate Results... │
│                                             │
│ 🔍 Classification Reasoning:               │
│ The 'Immunohistochemistry Results'...      │
└─────────────────────────────────────────────┘
```

## Test the Enhancement (Optional)

Run the test script to verify everything works:
```bash
python notebooks/test_sme_enhancement.py
```

## What's Improved

**Before:**
- Only showed: "Page 3: 'Immunohistochemistry Results'"
- No actual document content visible
- SMEs had to open the PDF separately

**After:**
- Shows full page text where the issue occurs
- Evidence highlighted in bright yellow within the text
- SMEs can review in one place without switching to PDF
- Better context for making decisions

## Files Created/Modified

- ✅ `src/evaluation/review_helper.py` - Backend enhancement
- 📝 `notebooks/sme_review_section4_updated.py` - Updated notebook code
- 📖 `notebooks/SME_REVIEW_ENHANCEMENT.md` - Detailed documentation
- 🧪 `notebooks/test_sme_enhancement.py` - Test script

## Need Help?

If you have any issues:
1. Check that `output/document_bundles/bundle_doc2_6.json` exists
2. Verify the SME packet has `document_bundle_path` field set
3. Run the test script to see if the enhancement is working
