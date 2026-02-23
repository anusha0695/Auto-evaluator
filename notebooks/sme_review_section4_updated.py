"""
EXACT CODE TO COPY INTO JUPYTER NOTEBOOK
Section 4: Review Issues Detected

This code replaces the existing code in the Section 4 cell of sme_review_interface.ipynb
"""

if packet:
    print("="*60)
    print(f"ISSUES DETECTED ({packet.total_issues})")
    print("="*60)
    
    for i, issue in enumerate(packet.issues_summary, 1):
        print(f"\n{i}. [{issue['severity']}] {issue['agent']}")
        print(f"   ID: {issue['id']}")
        print(f"   Message: {issue['message']}")
        print(f"   Location: {issue['location']}")
        print(f"   Suggested Fix: {issue['suggested_fix']}")
        
        # Get and display context
        context = helper.get_issue_context(packet, issue)
        
        if context['segment_info']:
            seg = context['segment_info']
            classif = context['classification_reasoning']
            
            # Build HTML for context display
            html = f"""
            <div style="border: 2px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 8px; background: #fafafa;">
                <h4 style="margin-top: 0; color: #333;">📍 Context: Segment {seg['segment_index']} (Pages {seg['start_page']}-{seg['end_page']}) - {seg['dominant_type']}</h4>
                
                <div style="margin: 10px 0; padding: 10px; background: white; border-radius: 5px;">
                    <strong>Document Type:</strong> {classif['document_type']}<br>
                    <strong>Presence Level:</strong> {classif['presence_level']} (Confidence: {classif['confidence']:.2f})<br>
                    <strong>Segment Share:</strong> {classif['segment_share']:.1%}
                </div>
            """
            
            # NEW: Display actual PDF text if available
            if context.get('pdf_text_chunks'):
                html += '<div style="background: #f0f8ff; padding: 12px; margin: 10px 0; border-left: 4px solid #1976d2; border-radius: 5px;">'
                html += '<strong style="color: #0d47a1;">📄 Original Document Text:</strong><br>'
                
                import html as html_lib
                
                for chunk in context['pdf_text_chunks']:
                    html += f'<div style="margin-top: 10px;">'
                    html += f'<strong>Page {chunk["page"]}:</strong><br>'
                    
                    snippet_escaped = html_lib.escape(chunk['snippet'])
                    
                    # Display paragraphs if available
                    if chunk.get('paragraphs'):
                        for para in chunk['paragraphs']:
                            para_escaped = html_lib.escape(para)
                            
                            # Highlight the evidence snippet
                            para_highlighted = para_escaped.replace(
                                snippet_escaped,
                                f'<mark style="background: #ffeb3b; padding: 2px 4px; border-radius: 3px; font-weight: bold;">{snippet_escaped}</mark>'
                            )
                            
                            html += f'<div style="margin: 8px 0; padding: 8px; background: white; border-radius: 3px; font-family: monospace; font-size: 0.9em;">{para_highlighted}</div>'
                    
                    # Otherwise display full page text
                    elif chunk.get('full_page_text'):
                        page_text_escaped = html_lib.escape(chunk['full_page_text'])
                        
                        # Highlight the evidence snippet in the full text
                        page_text_highlighted = page_text_escaped.replace(
                            snippet_escaped,
                            f'<mark style="background: #ffeb3b; padding: 2px 4px; border-radius: 3px; font-weight: bold;">{snippet_escaped}</mark>'
                        )
                        
                        html += f'<div style="margin: 8px 0; padding: 12px; background: white; border-radius: 3px; font-family: monospace; font-size: 0.9em; white-space: pre-wrap;">{page_text_highlighted}</div>'
                    
                    html += '</div>'
                
                html += '</div>'
            
            # Classification reasoning (agent's interpretation)
            html += """
                <div style="background: #fff3cd; padding: 12px; margin: 10px 0; border-left: 4px solid #ff6b6b; border-radius: 5px;">
                    <strong style="color: #856404;">🔍 Classification Reasoning:</strong><br>
                    <div style="margin-top: 8px; color: #333;">
            """
            
            # Highlight problematic text in reasoning if found
            reasoning = classif['reasoning']
            if context['problematic_text']:
                # Escape HTML and highlight
                import html as html_lib
                reasoning_escaped = html_lib.escape(reasoning)
                problematic_escaped = html_lib.escape(context['problematic_text'])
                reasoning_highlighted = reasoning_escaped.replace(
                    problematic_escaped,
                    f'<mark style="background: #ffeb3b; padding: 2px 4px; border-radius: 3px;">{problematic_escaped}</mark>'
                )
                html += reasoning_highlighted
            else:
                html += html_lib.escape(reasoning)
            
            html += """
                    </div>
                </div>
            """
            
            # Add evidence if available (and not already shown in PDF text)
            if context['evidence'] and not context.get('pdf_text_chunks'):
                html += '<div style="background: #e3f2fd; padding: 12px; margin: 10px 0; border-left: 4px solid #2196f3; border-radius: 5px;">'
                html += '<strong style="color: #0d47a1;">📄 Evidence References:</strong><br>'
                html += '<div style="margin-top: 8px;">'
                for ev in context['evidence']:
                    html += f'<div style="margin: 5px 0;">'
                    html += f'<strong>Page {ev["page"]}:</strong> "{html_lib.escape(ev["snippet"])}"'
                    if ev.get('anchors'):
                        html += f'<br><small style="color: #666;">Anchors: {", ".join(ev["anchors"])}</small>'
                    html += '</div>'
                html += '</div></div>'
            
            html += '</div>'
            
            # Display the HTML
            display(HTML(html))
        else:
            print("   (No detailed context available for this issue)")
