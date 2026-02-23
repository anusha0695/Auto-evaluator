"""
Unit tests for V1 Schema Validator

Tests rule-based schema validation for ClassificationOutput.
"""

import pytest
from src.agents.v1_schema_validator import V1SchemaValidator
from src.schemas import ClassificationOutput, DocumentBundle, IssueSeverity


@pytest.mark.unit
class TestV1SchemaValidator:
    """Test suite for V1 Schema Validator"""
    
    def test_clean_classification_no_issues(self, clean_classification, sample_doc_bundle):
        """Test that a valid classification produces no issues"""
        v1 = V1SchemaValidator()
        issues = v1.validate(clean_classification, sample_doc_bundle)
        
        assert len(issues) == 0, "Clean classification should have no issues"
    
    def test_page_bounds_within_document(self, clean_classification, sample_doc_bundle):
        """Test that page numbers are within document range"""
        # Modify to have out-of-bounds page
        data = clean_classification.model_dump()
        data['segments'][0]['end_page'] = 999  # Beyond 5-page document
        
        # Have to test with dict since Pydantic may validate
        v1 = V1SchemaValidator()
        
        # Create modified classification
        modified = ClassificationOutput(**data)
        doc_bundle_small = DocumentBundle(
            pdf_filename="test.pdf",
            total_pages=5,
            pages=[{"page_number": i+1, "text": f"Page {i+1}"} for i in range(5)]
        )
        
        issues = v1.validate(modified, doc_bundle_small)
        
        # Should catch page out of bounds
        assert any("beyond document" in i.message.lower() for i in issues), \
            "Should flag page beyond document range"
    
    def test_segment_count_mismatch(self, clean_classification, sample_doc_bundle):
        """Test detection of segment count mismatch"""
        v1 = V1SchemaValidator()
        
        # Modify classification to have wrong segment count
        data = clean_classification.model_dump()
        data['number_of_segments'] = 99  # But segments list has different length
        
        modified = ClassificationOutput(**data)
        issues = v1.validate(modified, sample_doc_bundle)
        
        # Should flag mismatch
        assert len(issues) > 0, "Should detect segment count mismatch"
        assert any("segment" in i.message.lower() and "count" in i.message.lower() for i in issues)
    
    def test_page_ranges_start_less_than_end(self, clean_classification, sample_doc_bundle):
        """Test that start_page <= end_page"""
        v1 = V1SchemaValidator()
        
        # Make start > end
        data = clean_classification.model_dump()
        data['segments'][0]['start_page'] = 5
        data['segments'][0]['end_page'] = 1
        
        modified = ClassificationOutput(**data)
        issues = v1.validate(modified, sample_doc_bundle)
        
        assert len(issues) > 0, "Should catch start_page > end_page"
        assert any(i.severity == IssueSeverity.BLOCKER for i in issues), \
            "Invalid page range should be BLOCKER"
    
    def test_confidence_in_valid_range(self):
        """Test confidence values are in [0.0, 1.0]"""
        # Note: Pydantic schema enforces this at construction time
        # So we test that V1 would catch it if data came from external source
        
        # This test verifies the schema itself enforces the constraint
        from src.schemas import SegmentComposition, DocumentType, PresenceLevel
        
        with pytest.raises(Exception):  # Pydantic validation error
            SegmentComposition(
                document_type=DocumentType.CLINICAL_NOTE,
                presence_level=PresenceLevel.PRIMARY,
                segment_share=0.5,
                confidence=1.5,  # Invalid!
                reasoning="Test"
            )
    
    def test_all_document_types_present_in_segments(self, clean_classification, sample_doc_bundle):
        """Test that all 5 document types are present in segment compositions"""
        v1 = V1SchemaValidator()
        
        # Remove a document type from segment composition
        data = clean_classification.model_dump()
        # Remove "Other" type
        data['segments'][0]['segment_composition'] = [
            comp for comp in data['segments'][0]['segment_composition']
            if comp['document_type'] != 'Other'
        ]
        
        modified = ClassificationOutput(**data)
        issues = v1.validate(modified, sample_doc_bundle)
        
        assert len(issues) > 0, "Should detect missing document type"
        assert any("document type" in i.message.lower() or "missing" in i.message.lower() for i in issues)
    
    def test_all_document_types_present_in_mixture(self, clean_classification, sample_doc_bundle):
        """Test that all 5 document types are in document_mixture"""
        v1 = V1SchemaValidator()
        
        data = clean_classification.model_dump()
        # Remove a type from document_mixture
        data['document_mixture'] = [
            mix for mix in data['document_mixture']
            if mix['document_type'] != 'Radiology Report'
        ]
        
        modified = ClassificationOutput(**data)
        issues = v1.validate(modified, sample_doc_bundle)
        
        assert len(issues) > 0, "Should detect missing type in document_mixture"
    
    def test_evidence_present_for_non_no_evidence_types(self, clean_classification, sample_doc_bundle):
        """Test that non-NO_EVIDENCE types have supporting evidence"""
        v1 = V1SchemaValidator()
        
        # Remove all evidence but keep PRIMARY presence
        data = clean_classification.model_dump()
        for seg in data['segments']:
            seg['top_evidence'] = []  # No evidence!
        
        modified = ClassificationOutput(**data)
        issues = v1.validate(modified, sample_doc_bundle)
        
        # Should flag missing evidence for types with presence
        assert len(issues) > 0, "Should detect missing evidence"
        assert any("evidence" in i.message.lower() for i in issues)
    
    def test_multiple_issues_detected(self, sample_doc_bundle):
        """Test that V1 can detect multiple issues in one classification"""
        from tests.fixtures.mock_classifications import load_valid_classification_from_file
        
        v1 = V1SchemaValidator()
        
        # Create classification with multiple issues
        data = load_valid_classification_from_file().model_dump()
        data['number_of_segments'] = 99  # Wrong count
        data['segments'][0]['end_page'] = 999  # Out of bounds
        data['segments'][0]['top_evidence'] = []  # Missing evidence
        
        modified = ClassificationOutput(**data)
        issues = v1.validate(modified, DocumentBundle(
            pdf_filename="test.pdf",
            total_pages=5,
            pages=[{"page_number": i+1, "text": f"Page {i+1}"} for i in range(5)]
        ))
        
        # Should catch multiple issues
        assert len(issues) >= 2, f"Should detect multiple issues, got {len(issues)}"


@pytest.mark.unit
def test_v1_validator_initialization():
    """Test V1 can be instantiated"""
    v1 = V1SchemaValidator()
    assert v1 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
