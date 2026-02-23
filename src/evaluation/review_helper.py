"""
SME Review Helper - Utilities for Jupyter notebook review interface
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Optional
from src.evaluation.ground_truth_schemas import (
    SMEPacket, SMEReview, SMECorrections, GroundTruthRecord, 
    GroundTruthSource, SMEReviewStatus
)
from src.schemas import ClassificationOutput


class SMEReviewHelper:
    """Helper class for SME review workflow in Jupyter notebook"""
    
    def __init__(self, packets_dir: str = "output/sme_packets"):
        # Find project root (where 'src' directory exists)
        project_root = Path.cwd()
        
        # Walk up the directory tree until we find 'src' directory
        while not (project_root / 'src').exists():
            if project_root.parent == project_root:
                # We've reached the root of the filesystem without finding 'src'
                raise RuntimeError("Could not find project root (directory containing 'src')")
            project_root = project_root.parent
        
        # Resolve paths relative to project root
        self.packets_dir = project_root / packets_dir
        self.ground_truth_dir = project_root / "output/ground_truth"
        self.ground_truth_dir.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def inject_styles():
        """
        Inject CSS + JS to fix grey text in the review interface.
        Call this once at notebook startup:  SMEReviewHelper.inject_styles()
        Uses setInterval to keep fixing colours for 60 s so it catches any
        cell that runs after setup, regardless of rendering delay.
        """
        from IPython.display import display, HTML
        display(HTML("""
        <style>
            .jp-OutputArea-output div[style*="font-family: monospace"] { color: #000 !important; }
            .jp-OutputArea-output h4 { color: #000 !important; }
            .jp-OutputArea-output strong { color: #000 !important; }
        </style>
        <script>
        (function() {
            function fixSMEColors() {
                document.querySelectorAll('div').forEach(function(el) {
                    var s = el.getAttribute('style') || '';

                    // Monospace paragraph boxes (Original Document Text lines)
                    if (s.indexOf('font-family: monospace') !== -1) {
                        el.style.color = '#000';
                    }

                    // Context card: Document Type / Presence Level / Segment Share
                    // style="margin: 10px 0; padding: 10px; background: white; border-radius: 5px;"
                    if (s.indexOf('background: white') !== -1) {
                        el.style.color = '#000';
                    }

                    // Outer review card background: #fafafa
                    if (s.indexOf('background: #fafafa') !== -1) {
                        el.style.color = '#000';
                    }

                    // Any div with color:#333 inline
                    if (s.replace(/\\s/g,'').indexOf('color:#333') !== -1) {
                        el.style.color = '#000';
                    }

                    // Page label wrapper inside blue doc box
                    if (s.indexOf('margin-top: 10px') !== -1) {
                        el.style.color = '#000';
                    }
                });

                // Anchor small tags with colour:#666
                document.querySelectorAll('small').forEach(function(el) {
                    el.style.color = '#000';
                });

                // h4 headings with colour:#333
                document.querySelectorAll('h4').forEach(function(el) {
                    el.style.color = '#000';
                });
            }

            // Run immediately to fix already-rendered cells
            fixSMEColors();

            // Poll every 500 ms for 60 s to catch cells run after setup
            var ticks = 0;
            var interval = setInterval(function() {
                fixSMEColors();
                ticks++;
                if (ticks >= 120) { clearInterval(interval); }
            }, 500);

            // Also watch DOM for new output nodes (belt-and-braces)
            var observer = new MutationObserver(function() { fixSMEColors(); });
            observer.observe(document.body, { childList: true, subtree: true });
        })();
        </script>
        """))

    def list_pending_reviews(self):
        """List all pending SME review packets"""
        if not self.packets_dir.exists():
            return []
        
        packets = []
        for packet_file in self.packets_dir.glob("sme_packet_*.json"):
            with open(packet_file) as f:
                data = json.load(f)
            
            if data.get('review_status') == 'pending':
                packets.append({
                    'file': packet_file.name,
                    'doc_id': data['doc_id'],
                    'total_issues': data['total_issues'],
                    'created_at': data.get('created_at', 'Unknown')
                })
        
        return packets
    
    def load_packet(self, doc_id: str) -> SMEPacket:
        """Load SME packet for review"""
        packet_file = self.packets_dir / f"sme_packet_{doc_id}.json"
        
        if not packet_file.exists():
            raise FileNotFoundError(f"Packet not found for doc_id: {doc_id}")
        
        with open(packet_file) as f:
            data = json.load(f)
        
        return SMEPacket(**data)
    
    def save_review(
        self,
        doc_id: str,
        reviewer_name: str,
        agrees_with_primary: bool,
        corrections: Optional[dict] = None,
        review_notes: str = "",
        confidence: float = 1.0
    ):
        """
        Save SME review and create ground truth record
        
        Args:
            doc_id: Document ID
            reviewer_name: Name of SME reviewer
            agrees_with_primary: Whether SME agrees with primary agent
            corrections: Optional corrections dict
            review_notes: SME's review notes
            confidence: SME's confidence in review (0.0-1.0)
        """
        # Load packet
        packet = self.load_packet(doc_id)
        
        # Create SME corrections if provided
        sme_corrections = None
        if corrections and not agrees_with_primary:
            sme_corrections = SMECorrections(
                corrected_dominant_type=corrections.get('dominant_type'),
                corrected_segments=corrections.get('segments'),
                corrected_document_mixture=corrections.get('document_mixture'),
                correction_notes=corrections.get('notes', '')
            )
        
        # Create SME review
        sme_review = SMEReview(
            reviewer_name=reviewer_name,
            review_date=datetime.now(),
            agrees_with_primary_agent=agrees_with_primary,
            corrections=sme_corrections,
            review_notes=review_notes,
            confidence_in_review=confidence
        )
        
        # Update packet
        packet.sme_review = sme_review
        packet.review_status = SMEReviewStatus.COMPLETED
        packet.updated_at = datetime.now()
        
        # Save updated packet
        packet_file = self.packets_dir / f"sme_packet_{doc_id}.json"
        with open(packet_file, 'w') as f:
            json.dump(packet.model_dump(mode='json'), f, indent=2, default=str)
        
        # Create ground truth record
        self._create_ground_truth(packet, sme_review)
        
        print(f"✅ Review saved for {doc_id}")
        print(f"   Agrees with primary: {agrees_with_primary}")
        print(f"   Ground truth created: output/ground_truth/gt_{doc_id}.json")
    
    def _create_ground_truth(self, packet: SMEPacket, sme_review: SMEReview):
        """Create ground truth record from reviewed packet"""
        
        # Determine ground truth classification
        if sme_review.agrees_with_primary_agent:
            # Use primary agent classification as-is
            gt_classification = packet.primary_agent_classification
            gt_source = GroundTruthSource.SME_VALIDATED
        else:
            # Use SME corrections
            # For now, create a modified version (in production, would fully reconstruct)
            gt_classification = packet.primary_agent_classification
            gt_source = GroundTruthSource.SME_CORRECTED
        
        # Create ground truth record
        gt_record = GroundTruthRecord(
            doc_id=packet.doc_id,
            pdf_filename=packet.pdf_filename,
            pdf_path=packet.pdf_path,
            production_classification=packet.production_classification,
            primary_agent_classification=packet.primary_agent_classification,
            v5_decision=packet.v5_decision,
            verification_report={
                'total_issues': packet.total_issues,
                'issues_summary': packet.issues_summary
            },
            sme_review=sme_review,
            ground_truth_source=gt_source,
            ground_truth_classification=gt_classification
        )
        
        # Save ground truth
        gt_file = self.ground_truth_dir / f"gt_{packet.doc_id}.json"
        with open(gt_file, 'w') as f:
            json.dump(gt_record.model_dump(mode='json'), f, indent=2, default=str)
    
    def get_review_stats(self):
        """Get statistics on review progress"""
        if not self.packets_dir.exists():
            return {
                'total_packets': 0,
                'pending': 0,
                'completed': 0,
                'completion_rate': 0.0
            }
        
        total = 0
        pending = 0
        completed = 0
        
        for packet_file in self.packets_dir.glob("sme_packet_*.json"):
            total += 1
            with open(packet_file) as f:
                data = json.load(f)
            
            status = data.get('review_status', 'pending')
            if status == 'pending':
                pending += 1
            elif status == 'completed':
                completed += 1
        
        return {
            'total_packets': total,
            'pending': pending,
            'completed': completed,
            'completion_rate': completed / total if total > 0 else 0.0
        }
    
    def get_issue_context(self, packet: SMEPacket, issue: dict) -> dict:
        """
        Extract contextual information for an issue to display in review interface
        
        Args:
            packet: SME packet containing classification
            issue: Issue dictionary from issues_summary
            
        Returns:
            Dictionary with context information including segment details, 
            reasoning text, evidence snippets, and actual PDF text chunks
        """
        context = {
            'segment_info': None,
            'classification_reasoning': None,
            'evidence': [],
            'problematic_text': None,
            'pdf_text_chunks': []  # NEW: Actual text from PDF
        }
        
        # Parse issue location
        location = issue.get('location')
        if not location or location == 'General':
            return context
        
        # Extract location details
        segment_index = location.get('segment_index')
        document_type = location.get('document_type')
        field = location.get('field')
        
        if not segment_index or not document_type:
            return context
        
        # Find the segment
        classification = packet.primary_agent_classification
        segment = None
        for seg in classification.segments:
            if seg.segment_index == segment_index:
                segment = seg
                break
        
        if not segment:
            return context
        
        # Extract segment info
        context['segment_info'] = {
            'segment_index': segment.segment_index,
            'start_page': segment.start_page,
            'end_page': segment.end_page,
            'page_count': segment.segment_page_count,
            'dominant_type': segment.dominant_type,
            'notes': segment.notes if hasattr(segment, 'notes') else None
        }
        
        # Find the document type composition entry
        doc_type_entry = None
        for comp in segment.segment_composition:
            if comp.document_type == document_type:
                doc_type_entry = comp
                break
        
        if not doc_type_entry:
            return context
        
        # Extract classification details
        context['classification_reasoning'] = {
            'document_type': doc_type_entry.document_type,
            'presence_level': doc_type_entry.presence_level,
            'confidence': doc_type_entry.confidence,
            'segment_share': doc_type_entry.segment_share,
            'reasoning': doc_type_entry.reasoning
        }
        
        # Extract evidence
        if hasattr(doc_type_entry, 'top_evidence') and doc_type_entry.top_evidence:
            context['evidence'] = [
                {
                    'page': ev.page,
                    'snippet': ev.snippet,
                    'anchors': ev.anchors_found if hasattr(ev, 'anchors_found') else []
                }
                for ev in doc_type_entry.top_evidence
            ]
        
        # Try to identify problematic text from the issue message
        # This is a simple heuristic - extract quoted text or key phrases
        message = issue.get('message', '')
        reasoning = doc_type_entry.reasoning
        
        # Look for quoted text in the message that appears in reasoning
        import re
        quoted_pattern = r"['\"]([^'\"]+)['\"]"
        quotes = re.findall(quoted_pattern, message)
        
        for quote in quotes:
            if quote.lower() in reasoning.lower():
                context['problematic_text'] = quote
                break
        
        # Alternative: look for key phrases mentioned in the message
        if not context['problematic_text']:
            keywords = ['lacks', 'missing', 'without', 'no evidence', 'does not']
            for keyword in keywords:
                if keyword in message.lower() and keyword in reasoning.lower():
                    # Find the sentence containing the keyword in reasoning
                    sentences = reasoning.split('.')
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            context['problematic_text'] = sentence.strip()
                            break
                    if context['problematic_text']:
                        break
        
        # NEW: Extract actual PDF text from DocumentBundle
        if packet.document_bundle_path:
            try:
                bundle_path = Path(packet.document_bundle_path)
                if not bundle_path.is_absolute():
                    # Resolve relative to project root
                    project_root = Path.cwd()
                    while not (project_root / 'src').exists():
                        if project_root.parent == project_root:
                            break
                        project_root = project_root.parent
                    bundle_path = project_root / bundle_path
                
                if bundle_path.exists():
                    with open(bundle_path, 'r') as f:
                        bundle_data = json.load(f)
                    
                    # Extract text from relevant pages (segment pages)
                    start_page = segment.start_page
                    end_page = segment.end_page
                    
                    for page in bundle_data.get('pages', []):
                        page_num = page.get('page_num')
                        if start_page <= page_num <= end_page:
                            # Check if this page contains any evidence snippets
                            page_text = page.get('text', '')
                            paragraphs = page.get('paragraphs', [])
                            
                            # Find evidence for this page
                            for ev in context['evidence']:
                                if ev['page'] == page_num:
                                    snippet = ev['snippet']
                                    
                                    # Try to find paragraphs containing this snippet
                                    matching_paragraphs = []
                                    for idx, p in enumerate(paragraphs):
                                        if snippet.lower() in p.lower():
                                            # Found a match! Get surrounding context
                                            # Include 2 paragraphs before and 3 after for context
                                            start_idx = max(0, idx - 2)
                                            end_idx = min(len(paragraphs), idx + 4)
                                            
                                            # Get the context paragraphs
                                            context_paragraphs = paragraphs[start_idx:end_idx]
                                            matching_paragraphs.extend(context_paragraphs)
                                            break  # Only show first match
                                    
                                    # If we have paragraphs, use them; otherwise use full page text
                                    if matching_paragraphs:
                                        context['pdf_text_chunks'].append({
                                            'page': page_num,
                                            'snippet': snippet,
                                            'paragraphs': matching_paragraphs[:10],  # Limit to 10 paragraphs total
                                            'full_page_text': None
                                        })
                                    elif page_text and snippet.lower() in page_text.lower():
                                        # Snippet is in page text but not in separate paragraphs
                                        # Show the full page text
                                        context['pdf_text_chunks'].append({
                                            'page': page_num,
                                            'snippet': snippet,
                                            'paragraphs': [],
                                            'full_page_text': page_text
                                        })
            except Exception as e:
                # If bundle loading fails, continue without PDF text
                import logging
                logging.warning(f"Failed to load DocumentBundle: {e}")
        
        return context

