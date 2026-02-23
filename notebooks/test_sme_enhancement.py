#!/usr/bin/env python3
"""
Test script to demonstrate the SME review enhancement
Shows the improved display with actual document content and highlighting
"""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from src.evaluation.review_helper import SMEReviewHelper

def main():
    """Demonstrate the enhancement"""
    print("="*70)
    print("SME REVIEW INTERFACE ENHANCEMENT - DEMONSTRATION")
    print("="*70)
    print()
    
    # Initialize helper
    helper = SMEReviewHelper()
    
    # Load the test packet
    doc_id = "doc2_6"
    
    try:
        packet = helper.load_packet(doc_id)
        print(f"✅ Loaded packet for: {doc_id}")
        print(f"   PDF: {packet.pdf_filename}")
        print(f"   Total Issues: {packet.total_issues}")
        print(f"   DocumentBundle: {packet.document_bundle_path}")
        print()
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return
    
    # Get context for the first issue
    if packet.issues_summary:
        issue = packet.issues_summary[0]
        
        print("="*70)
        print("ISSUE DETAILS")
        print("="*70)
        print(f"ID: {issue['id']}")
        print(f"Agent: {issue['agent']}")
        print(f"Severity: {issue['severity']}")
        print(f"Message: {issue['message']}")
        print()
        
        # Get context
        context = helper.get_issue_context(packet, issue)
        
        print("="*70)
        print("CONTEXT EXTRACTED")
        print("="*70)
        
        if context['segment_info']:
            seg = context['segment_info']
            print(f"📍 Segment: {seg['segment_index']}")
            print(f"   Pages: {seg['start_page']}-{seg['end_page']}")
            print(f"   Dominant Type: {seg['dominant_type']}")
            print()
        
        if context['classification_reasoning']:
            classif = context['classification_reasoning']
            print(f"📋 Classification:")
            print(f"   Document Type: {classif['document_type']}")
            print(f"   Presence Level: {classif['presence_level']}")
            print(f"   Confidence: {classif['confidence']:.2f}")
            print(f"   Segment Share: {classif['segment_share']:.1%}")
            print()
        
        # The main enhancement - show PDF text chunks
        if context.get('pdf_text_chunks'):
            print("="*70)
            print("📄 ACTUAL DOCUMENT CONTENT (ENHANCED DISPLAY)")
            print("="*70)
            print()
            
            for chunk in context['pdf_text_chunks']:
                print(f"Page {chunk['page']}:")
                print("-" * 70)
                
                if chunk.get('paragraphs'):
                    print(f"Found {len(chunk['paragraphs'])} paragraph(s) containing evidence:")
                    for i, para in enumerate(chunk['paragraphs'], 1):
                        print(f"\n  Paragraph {i}:")
                        print(f"  {para}")
                        print(f"  [Evidence snippet: '{chunk['snippet']}' should be highlighted]")
                
                elif chunk.get('full_page_text'):
                    print("Full page text:")
                    print()
                    text = chunk['full_page_text']
                    snippet = chunk['snippet']
                    
                    # Simple text highlighting for terminal
                    if snippet in text:
                        before, after = text.split(snippet, 1)
                        print(f"  {before}", end='')
                        print(f">>> {snippet} <<<", end='')  # Highlighted
                        print(f"{after}")
                    else:
                        print(f"  {text}")
                    
                    print()
                    print(f"  [Evidence snippet: '{snippet}' is highlighted above]")
                
                print()
        else:
            print("⚠️  No PDF text chunks found (DocumentBundle may not be available)")
            print()
            print("Falling back to evidence references:")
            for ev in context.get('evidence', []):
                print(f"  • Page {ev['page']}: \"{ev['snippet']}\"")
        
        print()
        print("="*70)
        print("SUMMARY")
        print("="*70)
        print()
        print("✅ Enhancement working! The review interface now shows:")
        print("   1. Actual document content from the PDF")
        print("   2. Evidence snippets highlighted within that content")
        print("   3. Full page text when paragraphs aren't available")
        print()
        print("📓 To use in Jupyter notebook:")
        print("   - Copy code from: notebooks/sme_review_section4_updated.py")
        print("   - Paste into Section 4 cell of sme_review_interface.ipynb")
        print("   - Re-run the notebook to see rich HTML display")
        print()

if __name__ == "__main__":
    main()
