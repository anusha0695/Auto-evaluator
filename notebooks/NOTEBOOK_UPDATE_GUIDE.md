# How to Update the Notebook for Full Document Content Display

## Quick Answer

**The notebook cell starting at line 277 already has the PDF text display code**, but to get the **full enhancement with surrounding context**, you need to make a small update.

## What You Need to Do

### Step 1: Open the Notebook
Open `sme_review_interface.ipynb` in Jupyter

### Step 2: Find the Cell
Look for the cell that starts with:
```python
if packet:
    print("="*60)
    print(f"ISSUES DETECTED ({packet.total_issues})")
    ...
```

This is around **line 277** in the `.ipynb` file.

### Step 3: Update the PDF Text Display Section

Find this part (around lines 317-331):
```python
# Display paragraphs with highlighted snippets
import html as html_lib
for para in chunk['paragraphs']:
    para_escaped = html_lib.escape(para)
    snippet_escaped = html_lib.escape(chunk['snippet'])
    
    # Highlight the evidence snippet
    para_highlighted = para_escaped.replace(
        snippet_escaped,
        f'<mark style="background: #ffeb3b; padding: 2px 4px; border-radius: 3px; font-weight: bold;">{snippet_escaped}</mark>'
    )
    
    html += f'<div style="margin: 8px 0; padding: 8px; background: white; border-radius: 3px; font-family: monospace; font-size: 0.9em;">{para_highlighted}</div>'
```

**Replace it with this enhanced version:**

```python
# Display paragraphs with highlighted snippets
import html as html_lib

# Handle full page text if paragraphs are empty
if chunk.get('full_page_text') and not chunk['paragraphs']:
    # Show full page text with highlighted snippet
    text_escaped = html_lib.escape(chunk['full_page_text'])
    snippet_escaped = html_lib.escape(chunk['snippet'])
    
    # Highlight the snippet
    text_highlighted = text_escaped.replace(
        snippet_escaped,
        f'<mark style="background: #ffeb3b; padding: 2px 4px; border-radius: 3px; font-weight: bold;">{snippet_escaped}</mark>'
    )
    
    html += f'<div style="margin: 8px 0; padding: 8px; background: white; border-radius: 3px; font-family: monospace; font-size: 0.9em; white-space: pre-wrap;">{text_highlighted}</div>'
else:
    # Show paragraphs (with surrounding context)
    for para in chunk['paragraphs']:
        para_escaped = html_lib.escape(para)
        snippet_escaped = html_lib.escape(chunk['snippet'])
        
        # Highlight the evidence snippet if present
        if snippet_escaped.lower() in para_escaped.lower():
            # Case-insensitive replacement
            import re
            para_highlighted = re.sub(
                f'({re.escape(chunk["snippet"])})',
                r'<mark style="background: #ffeb3b; padding: 2px 4px; border-radius: 3px; font-weight: bold;">\1</mark>',
                para_escaped,
                flags=re.IGNORECASE,
                count=1
            )
        else:
            # This is surrounding context - no highlighting
            para_highlighted = para_escaped
        
        html += f'<div style="margin: 8px 0; padding: 8px; background: white; border-radius: 3px; font-family: monospace; font-size: 0.9em;">{para_highlighted}</div>'
```

## Why This Update?

1. **Handles empty paragraphs** - Falls back to full page text
2. **Shows surrounding context** - Displays paragraphs before and after the evidence (thanks to the updated `review_helper.py`)
3. **Better highlighting** - Only highlights the actual evidence paragraph, shows context paragraphs without highlighting

## That's It!

After making this change:
1. **Re-run the notebook cell**
2. You'll see **6 paragraphs** of context instead of just 1
3. Evidence will be **highlighted in yellow**
4. Surrounding paragraphs provide **full context**

## Expected Output

**Before:**
```
📄 Evidence References:
Page 3: "Immunohistochemistry Results"
```

**After:**
```
📄 Original Document Text:

Page 3:
  c.798G>A                          ← Context (2 paragraphs before)
  2.08                              ← Context (1 paragraph before)
  Immunohistochemistry Results      ← HIGHLIGHTED EVIDENCE
  Biomarker                         ← Context (1 paragraph after)
  Result                            ← Context (2 paragraphs after)
  AR                                ← Context (3 paragraphs after)
```

## Already Fixed in Backend

The `review_helper.py` is already updated to provide surrounding context, so once you update the notebook cell, you'll immediately see the improvement!
