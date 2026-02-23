"""
Auto-Fix Engine - Applies automated fixes to classification issues

Supports fix types:
- Share normalization (segment-level)
- Share normalization (document-level)
- Page boundary adjustments (future)
"""

from typing import List, Tuple, Callable, Dict
from copy import deepcopy
import logging

from ..schemas import ClassificationOutput, Issue, IssueSeverity

logger = logging.getLogger(__name__)


class AutoFixEngine:
    """
    Engine for applying automatic fixes to classification output
    based on identified issues.
    """
    
    def __init__(self):
        """Initialize the fix engine with registry"""
        self.fix_registry: Dict[str, Callable] = {
            'share_normalization_segment': self._fix_segment_share_normalization,
            'share_normalization_document': self._fix_document_share_normalization,
        }
    
    def apply_fixes(
        self, 
        classification: ClassificationOutput, 
        issues: List[Issue]
    ) -> Tuple[ClassificationOutput, List[str]]:
        """
        Apply all auto-fixable issues to classification
        
        Args:
            classification: Original classification output
            issues: List of issues to fix
            
        Returns:
            (modified_classification, fixes_applied_log)
        """
        # Work on a deep copy to avoid modifying original
        modified = deepcopy(classification)
        fixes_log = []
        
        # Filter to only auto-fixable issues
        fixable_issues = [i for i in issues if i.auto_fixable]
        
        if not fixable_issues:
            logger.info("No auto-fixable issues found")
            return modified, fixes_log
        
        logger.info(f"Attempting to fix {len(fixable_issues)} issues")
        
        # Apply fixes
        for issue in fixable_issues:
            try:
                fix_type = self._infer_fix_type(issue)
                
                if not fix_type:
                    logger.warning(f"Could not infer fix type for issue {issue.issue_id}")
                    continue
                
                if fix_type not in self.fix_registry:
                    logger.warning(f"No fix handler for type '{fix_type}'")
                    continue
                
                # Apply the fix
                modified = self.fix_registry[fix_type](modified, issue)
                
                fix_description = f"{fix_type} for {issue.issue_id}: {issue.message[:60]}"
                fixes_log.append(fix_description)
                logger.info(f"Applied fix: {fix_description}")
                
            except Exception as e:
                logger.error(f"Failed to apply fix for {issue.issue_id}: {e}")
                # Continue with other fixes
        
        return modified, fixes_log
    
    def _infer_fix_type(self, issue: Issue) -> str:
        """
        Infer fix type from issue characteristics
        
        Args:
            issue: Issue to analyze
            
        Returns:
            Fix type string or empty string if cannot infer
        """
        message_lower = issue.message.lower()
        
        # Check for share sum issues
        if 'share' in message_lower and 'sum' in message_lower:
            # Determine if segment-level or document-level
            if 'segment' in message_lower and issue.location.get('segment') is not None:
                return 'share_normalization_segment'
            elif 'document' in message_lower or 'overall' in message_lower or 'mixture' in message_lower:
                return 'share_normalization_document'
        
        # Future: Add more patterns for other fix types
        
        return ""
    
    def _fix_segment_share_normalization(
        self, 
        classification: ClassificationOutput, 
        issue: Issue
    ) -> ClassificationOutput:
        """
        Fix: Normalize segment composition shares to sum to 1.0
        
        Args:
            classification: Classification to modify
            issue: Issue with location info
            
        Returns:
            Modified classification
        """
        segment_idx = issue.location.get('segment')
        
        if segment_idx is None:
            logger.warning(f"No segment index in issue location: {issue.location}")
            return classification
        
        # Find the segment (segment_index is 1-based)
        segment = None
        for seg in classification.segments:
            if seg.segment_index == segment_idx:
                segment = seg
                break
        
        if not segment:
            logger.warning(f"Segment {segment_idx} not found")
            return classification
        
        # Calculate current sum
        current_sum = sum(comp.segment_share for comp in segment.segment_composition)
        
        if current_sum == 0:
            logger.warning(f"Segment {segment_idx} has zero share sum, cannot normalize")
            return classification
        
        # Normalize to 1.0
        for comp in segment.segment_composition:
            comp.segment_share = comp.segment_share / current_sum
        
        logger.info(f"Normalized segment {segment_idx} shares from {current_sum:.4f} to 1.0")
        
        return classification
    
    def _fix_document_share_normalization(
        self, 
        classification: ClassificationOutput, 
        issue: Issue
    ) -> ClassificationOutput:
        """
        Fix: Normalize document mixture overall_share to sum to 1.0
        
        Args:
            classification: Classification to modify
            issue: Issue (location not required)
            
        Returns:
            Modified classification
        """
        # Calculate current sum
        current_sum = sum(mix.overall_share for mix in classification.document_mixture)
        
        if current_sum == 0:
            logger.warning("Document mixture has zero share sum, cannot normalize")
            return classification
        
        # Normalize to 1.0
        for mixture in classification.document_mixture:
            mixture.overall_share = mixture.overall_share / current_sum
        
        logger.info(f"Normalized document mixture shares from {current_sum:.4f} to 1.0")
        
        return classification
