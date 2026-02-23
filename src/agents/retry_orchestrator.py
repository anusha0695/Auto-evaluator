"""
Retry Orchestrator - Manages verification retry loop with auto-fix

Coordinates V1-V5 verification, auto-fix application, and retry attempts
with cycle detection and retry limits.
"""

import hashlib
import json
import logging
from typing import Tuple, List, Dict, Any

from ..schemas import ClassificationOutput, DocumentBundle, VerificationReport, ArbiterDecision
from .verification_runner import VerificationRunner
from .auto_fix_engine import AutoFixEngine

logger = logging.getLogger(__name__)


class RetryOrchestrator:
    """
    Orchestrates verification with automatic retry on fixable issues
    """
    
    MAX_RETRIES = 2  # Maximum retry attempts to prevent infinite loops
    
    def __init__(self):
        """Initialize orchestrator with verification runner and fix engine"""
        self.verification_runner = VerificationRunner()
        self.fix_engine = AutoFixEngine()
    
    def verify_with_retry(
        self,
        classification: ClassificationOutput,
        doc_bundle: DocumentBundle
    ) -> Tuple[ClassificationOutput, VerificationReport, ArbiterDecision, List[Dict[str, Any]]]:
        """
        Run verification with automatic retry on AUTO_RETRY decision
        
        Args:
            classification: Initial classification output
            doc_bundle: Document bundle
            
        Returns:
            (
                final_classification,
                final_verification_report,
                final_arbiter_decision,
                retry_log
            )
        """
        current_classification = classification
        retry_log = []
        seen_fingerprints = set()
        
        for attempt in range(self.MAX_RETRIES + 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"VERIFICATION ATTEMPT {attempt + 1}/{self.MAX_RETRIES + 1}")
            logger.info(f"{'='*60}")
            
            # Run V1-V5 verification
            report, decision = self.verification_runner.run_all(
                current_classification, 
                doc_bundle
            )
            
            # Check for cycle (same classification seen before)
            fingerprint = self._get_classification_fingerprint(current_classification)
            if fingerprint in seen_fingerprints:
                logger.warning("🔄 Cycle detected - same classification seen before")
                decision = ArbiterDecision(
                    decision="ESCALATE_TO_SME",
                    reason=f"Cycle detected in auto-fix loop after {attempt} attempts. Fixes did not resolve issues.",
                    issues_analyzed=decision.issues_analyzed,
                    blocker_count=decision.blocker_count,
                    major_count=decision.major_count,
                    minor_count=decision.minor_count,
                    fixable_count=decision.fixable_count
                )
                return current_classification, report, decision, retry_log
            
            seen_fingerprints.add(fingerprint)
            
            # Check decision
            if decision.decision != "AUTO_RETRY":
                # Either AUTO_ACCEPT or ESCALATE_TO_SME - we're done
                logger.info(f"✓ Final decision: {decision.decision}")
                return current_classification, report, decision, retry_log
            
            # AUTO_RETRY decision - check if we can retry
            if attempt >= self.MAX_RETRIES:
                logger.warning(f"⚠️  Max retries ({self.MAX_RETRIES}) reached")
                # Override decision to escalate
                decision = ArbiterDecision(
                    decision="ESCALATE_TO_SME",
                    reason=f"Max retries ({self.MAX_RETRIES}) reached. Auto-fix could not resolve all issues.",
                    issues_analyzed=decision.issues_analyzed,
                    blocker_count=decision.blocker_count,
                    major_count=decision.major_count,
                    minor_count=decision.minor_count,
                    fixable_count=decision.fixable_count
                )
                return current_classification, report, decision, retry_log
            
            # Apply auto-fixes
            logger.info(f"\n🔧 Applying auto-fixes (Attempt {attempt + 1})")
            
            fixable_issues = [i for i in report.issues if i.auto_fixable]
            logger.info(f"   Found {len(fixable_issues)} fixable issues")
            
            current_classification, fixes_applied = self.fix_engine.apply_fixes(
                current_classification,
                fixable_issues
            )
            
            # Log retry attempt
            retry_entry = {
                'attempt': attempt + 1,
                'issues_before_fix': len(report.issues),
                'fixable_issues': len(fixable_issues),
                'fixes_applied': fixes_applied,
                'decision_before_retry': decision.decision
            }
            retry_log.append(retry_entry)
            
            logger.info(f"   Applied {len(fixes_applied)} fixes:")
            for fix in fixes_applied:
                logger.info(f"     - {fix}")
            
            # Continue to next iteration to re-verify
        
        # Should not reach here
        raise RuntimeError("Retry loop exited unexpectedly")
    
    def _get_classification_fingerprint(self, classification: ClassificationOutput) -> str:
        """
        Generate a fingerprint hash of classification to detect cycles
        
        Uses key structural properties:
        - Segment boundaries
        - Dominant types
        - Share distributions
        
        Args:
            classification: Classification to fingerprint
            
        Returns:
            MD5 hash string
        """
        fingerprint_data = {
            'num_segments': classification.number_of_segments,
            'dominant_overall': classification.dominant_type_overall.value,
            'segments': [
                {
                    'start': seg.start_page,
                    'end': seg.end_page,
                    'dominant': seg.dominant_type.value,
                    'shares': [round(c.segment_share, 4) for c in seg.segment_composition]
                }
                for seg in classification.segments
            ],
            'mixture_shares': [round(m.overall_share, 4) for m in classification.document_mixture]
        }
        
        # Create stable JSON string
        json_str = json.dumps(fingerprint_data, sort_keys=True)
        
        # Hash it
        return hashlib.md5(json_str.encode()).hexdigest()
