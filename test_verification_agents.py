"""
Test suite for verification agents V1-V5.

Tests various issue scenarios to ensure agents correctly identify problems
and V5 makes appropriate decisions.
"""

import json
from pathlib import Path
from src.schemas import (
    ClassificationOutput,
    DocumentBundle,
    SegmentComposition,
    DocumentType,
    PresenceLevel,
    Issue,
    IssueSeverity,
    VerificationReport
)
from src.agents import (
    V1SchemaValidator,
    V2ConsistencyChecker,
    V3TrapDetector,
    V4EvidenceQualityAssessor,
    V5ArbiterAgent,
    VerificationRunner
)


def create_test_classification_with_issues(issue_type: str) -> ClassificationOutput:
    """
    Create a test classification with intentional issues
    
    Args:
        issue_type: Type of issue to inject:
            - 'invalid_confidence': Confidence > 1.0
            - 'invalid_shares': Segment shares don't sum to 1.0
            - 'page_overlap': Segments have overlapping pages
            - 'missing_evidence': No evidence for PRIMARY type
    """
    
    base_classification = {
        "number_of_segments": 1,
        "dominant_type_overall": "Clinical Note",
        "vendor_signals": [],
        "segments": [{
            "segment_index": 1,
            "start_page": 1,
            "end_page": 3,
            "dominant_type": "Clinical Note",
            "embedded_types": [],
            "segment_composition": [
                {
                    "document_type": "Clinical Note",
                    "presence_level": "PRIMARY",
                    "segment_share": 0.85 if issue_type != 'invalid_shares' else 0.60,
                    "confidence": 0.95 if issue_type != 'invalid_confidence' else 1.5
                },
                {
                    "document_type": "Pathology Report",
                    "presence_level": "NO_EVIDENCE",
                    "segment_share": 0.05 if issue_type != 'invalid_shares' else 0.05,
                    "confidence": 0.0
                },
                {
                    "document_type": "Genomic Report",
                    "presence_level": "NO_EVIDENCE",
                    "segment_share": 0.05 if issue_type != 'invalid_shares' else 0.10,
                    "confidence": 0.0
                },
                {
                    "document_type": "Radiology Report",
                    "presence_level": "NO_EVIDENCE",
                    "segment_share": 0.03 if issue_type != 'invalid_shares' else 0.15,
                    "confidence": 0.0
                },
                {
                    "document_type": "Other",
                    "presence_level": "NO_EVIDENCE",
                    "segment_share": 0.02 if issue_type != 'invalid_shares' else 0.10,
                    "confidence": 0.0
                }
            ],
            "top_evidence": [] if issue_type == 'missing_evidence' else [
                {
                    "document_type": "Clinical Note",
                    "snippet": "Patient presents with...",
                    "page": 1,
                    "anchors_found": ["Patient", "presents"]
                }
            ]
        }],
        "document_mixture": [
            {
                "document_type": "Clinical Note",
                "presence_level": "PRIMARY",
                "overall_share": 0.85,
                "confidence": 0.95,
                "dominance_score": 0.85
            },
            {
                "document_type": "Pathology Report",
                "presence_level": "NO_EVIDENCE",
                "overall_share": 0.05,
                "confidence": 0.0,
                "dominance_score": 0.0
            },
            {
                "document_type": "Genomic Report",
                "presence_level": "NO_EVIDENCE",
                "overall_share": 0.05,
                "confidence": 0.0,
                "dominance_score": 0.0
            },
            {
                "document_type": "Radiology Report",
                "presence_level": "NO_EVIDENCE",
                "overall_share": 0.03,
                "confidence": 0.0,
                "dominance_score": 0.0
            },
            {
                "document_type": "Other",
                "presence_level": "NO_EVIDENCE",
                "overall_share": 0.02,
                "confidence": 0.0,
                "dominance_score": 0.0
            }
        ]
    }
    
    # Add page overlap if requested
    if issue_type == 'page_overlap':
        base_classification["number_of_segments"] = 2
        base_classification["segments"].append({
            "segment_index": 2,
            "start_page": 3,  # Overlaps with segment 1 (ends at 3)
            "end_page": 5,
            "dominant_type": "Pathology Report",
            "embedded_types": [],
            "segment_composition": [
                {"document_type": "Clinical Note", "presence_level": "NO_EVIDENCE", "segment_share": 0.10, "confidence": 0.0},
                {"document_type": "Pathology Report", "presence_level": "PRIMARY", "segment_share": 0.70, "confidence": 0.85},
                {"document_type": "Genomic Report", "presence_level": "NO_EVIDENCE", "segment_share": 0.10, "confidence": 0.0},
                {"document_type": "Radiology Report", "presence_level": "NO_EVIDENCE", "segment_share": 0.05, "confidence": 0.0},
                {"document_type": "Other", "presence_level": "NO_EVIDENCE", "segment_share": 0.05, "confidence": 0.0}
            ],
            "top_evidence": [{
                "document_type": "Pathology Report",
                "snippet": "Final Diagnosis: ...",
                "page": 4,
                "anchors_found": ["Final Diagnosis"]
            }]
        })
    
    return ClassificationOutput(**base_classification)


def create_dummy_doc_bundle(num_pages: int = 5) -> DocumentBundle:
    """Create a minimal document bundle for testing"""
    return DocumentBundle(
        pdf_filename="test_document.pdf",
        total_pages=num_pages,
        pages=[
            {"page_number": i+1, "text": f"Page {i+1} content..."}
            for i in range(num_pages)
        ]
    )


def test_v1_invalid_confidence():
    """Test V1 catches invalid confidence values"""
    print("\n" + "="*60)
    print("TEST 1: V1 Schema Validator - Invalid Confidence (>1.0)")
    print("="*60)
    
    classification = create_test_classification_with_issues('invalid_confidence')
    doc_bundle = create_dummy_doc_bundle()
    
    v1 = V1SchemaValidator()
    issues = v1.validate(classification, doc_bundle)
    
    print(f"Issues found: {len(issues)}")
    for issue in issues:
        print(f"  [{issue.severity.value}] {issue.message}")
    
    assert len(issues) > 0, "V1 should catch invalid confidence"
    assert any("confidence" in i.message.lower() for i in issues), "Should flag confidence issue"
    print("✓ TEST PASSED")
    return issues


def test_v2_invalid_shares():
    """Test V2 catches share sums != 1.0"""
    print("\n" + "="*60)
    print("TEST 2: V2 Consistency Checker - Invalid Share Sums")
    print("="*60)
    
    classification = create_test_classification_with_issues('invalid_shares')
    doc_bundle = create_dummy_doc_bundle()
    
    from google import genai
    from src.config import settings
    client = genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.vertex_ai_location
    )
    
    v2 = V2ConsistencyChecker(client)
    issues, score = v2.validate(classification, doc_bundle)
    
    print(f"Issues found: {len(issues)}")
    print(f"Consistency score: {score:.2f}")
    for issue in issues:
        print(f"  [{issue.severity.value}] {issue.message}")
    
    assert len(issues) > 0, "V2 should catch invalid shares"
    assert score < 1.0, "Score should be < 1.0 with issues"
    print("✓ TEST PASSED")
    return issues


def test_v2_page_overlap():
    """Test V2 catches overlapping page ranges"""
    print("\n" + "="*60)
    print("TEST 3: V2 Consistency Checker - Page Overlap")
    print("="*60)
    
    classification = create_test_classification_with_issues('page_overlap')
    doc_bundle = create_dummy_doc_bundle()
    
    from google import genai
    from src.config import settings
    client = genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.vertex_ai_location
    )
    
    v2 = V2ConsistencyChecker(client)
    issues, score = v2.validate(classification, doc_bundle)
    
    print(f"Issues found: {len(issues)}")
    for issue in issues:
        print(f"  [{issue.severity.value}] {issue.message}")
    
    assert len(issues) > 0, "V2 should catch page overlap"
    assert any(i.severity == IssueSeverity.BLOCKER for i in issues), "Overlap should be BLOCKER"
    print("✓ TEST PASSED")
    return issues


def test_v5_decision_escalate_blocker():
    """Test V5 escalates when BLOCKER present"""
    print("\n" + "="*60)
    print("TEST 4: V5 Arbiter - ESCALATE on BLOCKER")
    print("="*60)
    
    # Create report with BLOCKER issue
    report = VerificationReport(
        issues=[
            Issue(
                ig_id="IG-6",
                issue_id="TEST-0001",
                agent="V2",
                severity=IssueSeverity.BLOCKER,
                message="Page overlap detected",
                location={},
                suggested_fix="Fix page ranges",
                auto_fixable=False
            )
        ],
        v1_validation_passed=False,
        v2_consistency_score=0.0,
        v3_traps_triggered=0,
        v4_evidence_quality_score=1.0,
        has_blocker_issues=True,
        total_issues=1,
        llm_calls_made=0
    )
    
    v5 = V5ArbiterAgent()
    decision = v5.decide(report)
    
    print(f"Decision: {decision.decision}")
    print(f"Reason: {decision.reason}")
    
    assert decision.decision == "ESCALATE_TO_SME", "Should escalate on BLOCKER"
    assert decision.blocker_count == 1
    print("✓ TEST PASSED")
    return decision


def test_v5_decision_retry_fixable():
    """Test V5 retries on fixable MAJOR issues"""
    print("\n" + "="*60)
    print("TEST 5: V5 Arbiter - AUTO_RETRY on Fixable MAJOR")
    print("="*60)
    
    report = VerificationReport(
        issues=[
            Issue(
                ig_id="IG-8",
                issue_id="TEST-0002",
                agent="V2",
                severity=IssueSeverity.MAJOR,
                message="Shares sum to 0.95",
                location={},
                suggested_fix="Normalize shares",
                auto_fixable=True
            )
        ],
        v1_validation_passed=True,
        v2_consistency_score=0.8,
        v3_traps_triggered=0,
        v4_evidence_quality_score=1.0,
        has_blocker_issues=False,
        total_issues=1,
        llm_calls_made=0
    )
    
    v5 = V5ArbiterAgent()
    decision = v5.decide(report)
    
    print(f"Decision: {decision.decision}")
    print(f"Reason: {decision.reason}")
    
    assert decision.decision == "AUTO_RETRY", "Should retry on fixable MAJOR"
    assert decision.major_count == 1
    assert decision.fixable_count == 1
    print("✓ TEST PASSED")
    return decision


def test_v5_decision_accept_minor():
    """Test V5 accepts on MINOR-only issues"""
    print("\n" + "="*60)
    print("TEST 6: V5 Arbiter - AUTO_ACCEPT on MINOR Only")
    print("="*60)
    
    report = VerificationReport(
        issues=[
            Issue(
                ig_id="IG-3",
                issue_id="TEST-0003",
                agent="V4",
                severity=IssueSeverity.MINOR,
                message="Snippet slightly long",
                location={},
                suggested_fix="Trim snippet",
                auto_fixable=True
            )
        ],
        v1_validation_passed=True,
        v2_consistency_score=1.0,
        v3_traps_triggered=0,
        v4_evidence_quality_score=0.95,
        has_blocker_issues=False,
        total_issues=1,
        llm_calls_made=2
    )
    
    v5 = V5ArbiterAgent()
    decision = v5.decide(report)
    
    print(f"Decision: {decision.decision}")
    print(f"Reason: {decision.reason}")
    
    assert decision.decision == "AUTO_ACCEPT", "Should accept on MINOR only"
    assert decision.minor_count == 1
    print("✓ TEST PASSED")
    return decision


if __name__ == "__main__":
    print("\n" + "="*60)
    print("VERIFICATION AGENTS TEST SUITE")
    print("="*60)
    
    try:
        # V1 Tests
        test_v1_invalid_confidence()
        
        # V2 Tests  
        test_v2_invalid_shares()
        test_v2_page_overlap()
        
        # V5 Decision Tests
        test_v5_decision_escalate_blocker()
        test_v5_decision_retry_fixable()
        test_v5_decision_accept_minor()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
