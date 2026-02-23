"""V1: Schema & Completeness Validator - Pure rule-based validation"""

from typing import List
from ..schemas import (
    ClassificationOutput,
    DocumentBundle,
    Issue,
    IssueSeverity,
    DocumentType,
    PresenceLevel
)


class V1SchemaValidator:
    """
    Validates classifier output schema and completeness using deterministic rules.
    No LLM calls - fast and zero cost.
    """
    
    def validate(
        self,
        classification: ClassificationOutput,
        doc_bundle: DocumentBundle
    ) -> List[Issue]:
        """
        Run all V1 validation checks
        
        Args:
            classification: Output from primary classifier
            doc_bundle: Original document metadata
            
        Returns:
            List of issues found (empty if all validations pass)
        """
        issues = []
        issue_counter = 0
        
        # Check 1: Segment count matches
        issues.extend(self._check_segment_count(classification, issue_counter))
        issue_counter = len(issues)
        
        # Check 2: Page bounds
        issues.extend(self._check_page_bounds(classification, doc_bundle, issue_counter))
        issue_counter = len(issues)
        
        # Check 3: Confidence ranges
        issues.extend(self._check_confidence_ranges(classification, issue_counter))
        issue_counter = len(issues)
        
        # Check 4: Completeness (all 5 types present)
        issues.extend(self._check_completeness(classification, issue_counter))
        issue_counter = len(issues)
        
        # Check 5: Evidence emptiness for NO_EVIDENCE
        issues.extend(self._check_evidence_alignment(classification, issue_counter))
        
        return issues
    
    def _check_segment_count(
        self,
        classification: ClassificationOutput,
        start_counter: int
    ) -> List[Issue]:
        """Verify number_of_segments matches segments array length"""
        issues = []
        
        expected = classification.number_of_segments
        actual = len(classification.segments)
        
        if expected != actual:
            issues.append(Issue(
                ig_id="IG-1",
                issue_id=f"V1-{start_counter:04d}",
                agent="V1",
                severity=IssueSeverity.BLOCKER,
                message=f"number_of_segments is {expected} but segments array has {actual} items",
                location={"field": "number_of_segments"},
                suggested_fix=f"Set number_of_segments = {actual}",
                auto_fixable=True
            ))
        
        return issues
    
    def _check_page_bounds(
        self,
        classification: ClassificationOutput,
        doc_bundle: DocumentBundle,
        start_counter: int
    ) -> List[Issue]:
        """Check all page numbers are within document page count"""
        issues = []
        max_page = doc_bundle.total_pages
        
        for segment in classification.segments:
            # Check start_page
            if segment.start_page < 1 or segment.start_page > max_page:
                issues.append(Issue(
                    ig_id="IG-1",
                    issue_id=f"V1-{start_counter + len(issues):04d}",
                    agent="V1",
                    severity=IssueSeverity.BLOCKER,
                    message=f"Segment {segment.segment_index} start_page={segment.start_page} out of range [1, {max_page}]",
                    location={"segment_index": segment.segment_index, "field": "start_page"},
                    suggested_fix=f"Adjust start_page to valid range [1, {max_page}]",
                    auto_fixable=False
                ))
            
            # Check end_page
            if segment.end_page < 1 or segment.end_page > max_page:
                issues.append(Issue(
                    ig_id="IG-1",
                    issue_id=f"V1-{start_counter + len(issues):04d}",
                    agent="V1",
                    severity=IssueSeverity.BLOCKER,
                    message=f"Segment {segment.segment_index} end_page={segment.end_page} out of range [1, {max_page}]",
                    location={"segment_index": segment.segment_index, "field": "end_page"},
                    suggested_fix=f"Adjust end_page to valid range [1, {max_page}]",
                    auto_fixable=False
                ))
            
            # Check start <= end
            if segment.start_page > segment.end_page:
                issues.append(Issue(
                    ig_id="IG-6",
                    issue_id=f"V1-{start_counter + len(issues):04d}",
                    agent="V1",
                    severity=IssueSeverity.BLOCKER,
                    message=f"Segment {segment.segment_index}: start_page ({segment.start_page}) > end_page ({segment.end_page})",
                    location={"segment_index": segment.segment_index, "field": "page_range"},
                    suggested_fix="Swap start_page and end_page or adjust page range",
                    auto_fixable=False
                ))
            
            # Check segment_page_count calculation
            expected_count = segment.end_page - segment.start_page + 1
            if segment.segment_page_count != expected_count:
                issues.append(Issue(
                    ig_id="IG-1",
                    issue_id=f"V1-{start_counter + len(issues):04d}",
                    agent="V1",
                    severity=IssueSeverity.MAJOR,
                    message=f"Segment {segment.segment_index}: segment_page_count={segment.segment_page_count} but should be {expected_count} (end_page - start_page + 1)",
                    location={"segment_index": segment.segment_index, "field": "segment_page_count"},
                    suggested_fix=f"Set segment_page_count = {expected_count}",
                    auto_fixable=True
                ))
        
        return issues
    
    def _check_confidence_ranges(
        self,
        classification: ClassificationOutput,
        start_counter: int
    ) -> List[Issue]:
        """Validate all confidence scores in [0.0, 1.0]"""
        issues = []
        
        # Check segment compositions
        for segment in classification.segments:
            for comp in segment.segment_composition:
                if not (0.0 <= comp.confidence <= 1.0):
                    issues.append(Issue(
                        ig_id="IG-1",
                        issue_id=f"V1-{start_counter + len(issues):04d}",
                        agent="V1",
                        severity=IssueSeverity.BLOCKER,
                        message=f"Segment {segment.segment_index}, {comp.document_type.value}: confidence={comp.confidence} out of range [0.0, 1.0]",
                        location={
                            "segment_index": segment.segment_index,
                            "document_type": comp.document_type.value,
                            "field": "confidence"
                        },
                        suggested_fix="Adjust confidence to [0.0, 1.0]",
                        auto_fixable=False
                    ))
        
        # Check document mixture
        for mix in classification.document_mixture:
            if not (0.0 <= mix.confidence <= 1.0):
                issues.append(Issue(
                    ig_id="IG-1",
                    issue_id=f"V1-{start_counter + len(issues):04d}",
                    agent="V1",
                    severity=IssueSeverity.BLOCKER,
                    message=f"Document mixture {mix.document_type.value}: confidence={mix.confidence} out of range [0.0, 1.0]",
                    location={"document_type": mix.document_type.value, "field": "confidence"},
                    suggested_fix="Adjust confidence to [0.0, 1.0]",
                    auto_fixable=False
                ))
        
        return issues
    
    def _check_completeness(
        self,
        classification: ClassificationOutput,
        start_counter: int
    ) -> List[Issue]:
        """Check that all 5 document types are present in each segment and document_mixture"""
        issues = []
        
        # Check each segment has all 5 types
        for segment in classification.segments:
            types_in_segment = {comp.document_type for comp in segment.segment_composition}
            all_types = set(DocumentType)
            
            if types_in_segment != all_types:
                missing_types = all_types - types_in_segment
                extra_types = types_in_segment - all_types
                
                if missing_types:
                    issues.append(Issue(
                        ig_id="IG-7",
                        issue_id=f"V1-{start_counter + len(issues):04d}",
                        agent="V1",
                        severity=IssueSeverity.BLOCKER,
                        message=f"Segment {segment.segment_index} missing document types: {', '.join(t.value for t in missing_types)}",
                        location={"segment_index": segment.segment_index, "field": "segment_composition"},
                        suggested_fix=f"Add missing types with NO_EVIDENCE presence_level",
                        auto_fixable=True
                    ))
                
                if extra_types:
                    issues.append(Issue(
                        ig_id="IG-7",
                        issue_id=f"V1-{start_counter + len(issues):04d}",
                        agent="V1",
                        severity=IssueSeverity.BLOCKER,
                        message=f"Segment {segment.segment_index} has extra/duplicate types: {', '.join(t.value for t in extra_types)}",
                        location={"segment_index": segment.segment_index, "field": "segment_composition"},
                        suggested_fix="Remove duplicate entries",
                        auto_fixable=True
                    ))
        
        # Check document_mixture has all 5 types
        types_in_mixture = {mix.document_type for mix in classification.document_mixture}
        all_types = set(DocumentType)
        
        if types_in_mixture != all_types:
            missing_types = all_types - types_in_mixture
            extra_types = types_in_mixture - all_types
            
            if missing_types:
                issues.append(Issue(
                    ig_id="IG-7",
                    issue_id=f"V1-{start_counter + len(issues):04d}",
                    agent="V1",
                    severity=IssueSeverity.BLOCKER,
                    message=f"document_mixture missing types: {', '.join(t.value for t in missing_types)}",
                    location={"field": "document_mixture"},
                    suggested_fix=f"Add missing types with NO_EVIDENCE",
                    auto_fixable=True
                ))
            
            if extra_types:
                issues.append(Issue(
                    ig_id="IG-7",
                    issue_id=f"V1-{start_counter + len(issues):04d}",
                    agent="V1",
                    severity=IssueSeverity.BLOCKER,
                    message=f"document_mixture has extra/duplicate types: {', '.join(t.value for t in extra_types)}",
                    location={"field": "document_mixture"},
                    suggested_fix="Remove duplicates",
                    auto_fixable=True
                ))
        
        return issues
    
    def _check_evidence_alignment(
        self,
        classification: ClassificationOutput,
        start_counter: int
    ) -> List[Issue]:
        """Check for appropriate evidence when presence_level != NO_EVIDENCE"""
        issues = []
        
        for segment in classification.segments:
            for comp in segment.segment_composition:
                # If presence level is not NO_EVIDENCE, should ideally have evidence
                if comp.presence_level != PresenceLevel.NO_EVIDENCE:
                    if not comp.top_evidence or len(comp.top_evidence) == 0:
                        # This is a WARNING, not BLOCKER (evidence may be optional for low presence)
                        issues.append(Issue(
                            ig_id="IG-5",
                            issue_id=f"V1-{start_counter + len(issues):04d}",
                            agent="V1",
                            severity=IssueSeverity.MINOR,
                            message=f"Segment {segment.segment_index}, {comp.document_type.value} has {comp.presence_level.value} but no evidence provided",
                            location={
                                "segment_index": segment.segment_index,
                                "document_type": comp.document_type.value,
                                "field": "top_evidence"
                            },
                            suggested_fix="Add at least one evidence snippet or change to NO_EVIDENCE",
                            auto_fixable=False
                        ))
        
        return issues
