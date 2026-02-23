#!/usr/bin/env python3
"""
Standalone script to regenerate DocumentBundle with fixed extraction logic
No imports from src needed - contains all logic inline
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

def process_blocks_recursively(blocks, pages_dict: Dict, parent_type: str = None):
    """
    Recursively process blocks and nested sub-blocks
    
    Args:
        blocks: List of blocks to process
        pages_dict: Dictionary to accumulate page data
        parent_type: Type of parent block (for context)
    """
    for block in blocks:
        # Get page number
        page_num = block.get('pageSpan', {}).get('pageStart', 1)
        
        # Initialize page if not exists
        if page_num not in pages_dict:
            pages_dict[page_num] = {
                'page_num': page_num,
                'text': '',
                'paragraphs': [],
                'layout_metadata': {
                    'block_types': [],
                    'has_tables': False
                }
            }
        
        # Process text blocks
        if 'textBlock' in block:
            text_block = block['textBlock']
            text = text_block.get('text', '')
            block_type = text_block.get('type', 'unknown')
            
            # Add text to page (if not empty)
            if text.strip():
                pages_dict[page_num]['text'] += text + '\n'
                
                # Add to paragraphs array for ALL text content
                # (headings, paragraphs, everything with actual text)
                pages_dict[page_num]['paragraphs'].append(text)
                
                # Track block type
                pages_dict[page_num]['layout_metadata']['block_types'].append(block_type)
            
            # Process nested blocks if present
            if 'blocks' in text_block:
                process_blocks_recursively(text_block['blocks'], pages_dict, block_type)
        
        # Process table blocks
        elif 'tableBlock' in block:
            pages_dict[page_num]['layout_metadata']['has_tables'] = True
            
            # Extract text from table cells
            table_block = block['tableBlock']
            if 'bodyRows' in table_block:
                for row in table_block['bodyRows']:
                    if 'cells' in row:
                        for cell in row['cells']:
                            if 'blocks' in cell:
                                # Recursively process blocks in table cells
                                process_blocks_recursively(cell['blocks'], pages_dict, 'table')

def extract_pages(document_layout_data: Dict) -> List[Dict]:
    """Extract pages from LayoutParser documentLayout"""
    pages_dict = {}
    
    blocks = document_layout_data.get('blocks', [])
    if blocks:
        process_blocks_recursively(blocks, pages_dict)
    
    # Convert dict to sorted list
    pages = [pages_dict[page_num] for page_num in sorted(pages_dict.keys())]
    return pages

def main():
    print("="*70)
    print("REGENERATING DOCUMENTBUNDLE WITH FIXED EXTRACTION")
    print("="*70)
    print()
    
    # Load the real LayoutParser response
    with open('rest_api_response.json', 'r') as f:
        rest_api_data = json.load(f)
    
    layout_data = rest_api_data['document']['documentLayout']
    
    print("✅ Loaded real LayoutParser response")
    print(f"   Total blocks (top-level): {len(layout_data['blocks'])}")
    print()
    
    # Extract pages with FIXED recursive logic
    print("⚙️  Extracting pages with FIXED recursive logic...")
    pages = extract_pages(layout_data)
    
    print(f"✅ Extracted {len(pages)} page(s)")
    print()
    
    # Display results
    for page in pages:
        print(f"{'='*70}")
        print(f"PAGE {page['page_num']}")
        print(f"{'='*70}")
        print(f"📝 Total text length: {len(page['text'])} characters")
        print(f"📄 Number of content blocks: {len(page['paragraphs'])}")
        print(f"🏷️  Block types: {', '.join(sorted(set(page['layout_metadata']['block_types'])))}")
        print(f"📊 Has tables: {page['layout_metadata']['has_tables']}")
        print()
        
        # Show first 5 content blocks
        print("First 5 content blocks:")
        for i, para in enumerate(page['paragraphs'][:5], 1):
            display_text = para.replace('\n', ' ')[:80]
            print(f"  {i}. {display_text}{'...' if len(para) > 80 else ''}")
        
        if len(page['paragraphs']) > 5:
            print(f"  ... and {len(page['paragraphs']) - 5} more content blocks")
        print()
    
    # Create proper DocumentBundle
    bundle_data = {
        'doc_id': 'doc2_6',
        'file_path': 'data/input/raw_documents/doc2_6.pdf',
        'total_pages': len(pages),
        'pages': pages,
        'processing_timestamp': datetime.utcnow().isoformat()
    }
    
    # Save updated bundle
    bundle_path = Path('output/document_bundles/bundle_doc2_6.json')
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(bundle_path, 'w') as f:
        json.dump(bundle_data, f, indent=2)
    
    print("="*70)
    print("✅ SUCCESS!")
    print("="*70)
    print(f"DocumentBundle saved to: {bundle_path}")
    print(f"  Total pages: {len(pages)}")
    total_paragraphs = sum(len(p['paragraphs']) for p in pages)
    print(f"  Total content blocks: {total_paragraphs}")
    print()
    print("🎯 WHAT'S DIFFERENT:")
    print("  BEFORE: Only headings, empty paragraphs array")
    print(f"  AFTER:  {total_paragraphs} content blocks with FULL text")
    print()
    print("💡 NOW THE SME REVIEW INTERFACE WILL SHOW:")
    print("  ✓ Full page content with actual paragraph text")
    print("  ✓ Evidence snippets highlighted within real content")
    print("  ✓ Complete context for SME review")
    print()


if __name__ == '__main__':
    main()
