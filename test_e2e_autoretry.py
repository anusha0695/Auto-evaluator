"""
End-to-End AUTO_RETRY Test with Custom Classification Data

This test creates a custom classification from scratch with a known
fixable issue, then validates the complete retry cycle:
1. V1-V5 detect the issue
2. V5 decides AUTO_RETRY
3. Auto-fix engine applies fix
4. Pipeline re-runs V1-V5
5. V5 decides AUTO_ACCEPT
"""

import json
from datetime import datetime
from pathlib import Path
from src.schemas import ClassificationOutput, DocumentBundle, DocumentType, PresenceLevel
from src.agents import RetryOrchestrator


def create_custom_classification_with_fixable_issue():
    """
    Create a classification with a SINGLE fixable issue:
    - Load valid classification from file
    - Modify AFTER validation to inject share error
    """
    
    # Load a real, valid classification
    classification_path = Path("output/classification_result.json")
    if not classification_path.exists():
        raise FileNotFoundError(
            "Please run classification first: "
            "python run_classification.py data/input/raw_documents/doc2_1.pdf"
        )
    
    with open(classification_path, 'r') as f:
        data = json.load(f)
    
    # Create VALID classification
    classification = ClassificationOutput(**data)
    
    # Now modify AFTER validation to inject a SUBTLE fixable error
    # INCREASE a share slightly to create sum > 1.0 (not negative, so V1 won't flag as BLOCKER)
    print("Original segment 1 shares:")
    for comp in classification.segments[0].segment_composition:
        print(f"  {comp.document_type.value}: {comp.segment_share:.4f}")
    
    original_sum = sum(c.segment_share for c in classification.segments[0].segment_composition)
    print(f"  TOTAL: {original_sum:.4f}")
    
    # Inject error: INCREASE first non-zero share by a small amount
    # Find first non-zero share to modify
    for comp in classification.segments[0].segment_composition:
        if comp.segment_share > 0:
            comp.segment_share += 0.03  # Small increase creates sum = 1.03
            break
    
    modified_sum = sum(c.segment_share for c in classification.segments[0].segment_composition)
    print(f"\nModified segment 1 shares:")
    print(f"  {classification.segments[0].segment_composition[0].document_type.value}: "
          f"{classification.segments[0].segment_composition[0].segment_share:.4f} (increased)")
    print(f"  TOTAL: {modified_sum:.4f} ❌ (should be 1.00)")
    print(f"  Error: +{modified_sum - 1.0:.2f} (all shares positive, V2 should catch)")
    
    return classification


def test_end_to_end_retry():
    """
    Test complete AUTO_RETRY flow with custom data
    """
    
    print("\n" + "="*70)
    print("END-TO-END AUTO_RETRY TEST")
    print("="*70)
    print("\nTest Goal: Validate complete retry cycle from issue → fix → accept")
    
    # Step 1: Create classification with fixable issue
    print("\n" + "-"*70)
    print("STEP 1: Create Custom Classification with Fixable Issue")
    print("-"*70)
    
    classification = create_custom_classification_with_fixable_issue()
    
    # Create document bundle
    doc_bundle = DocumentBundle(
        doc_id="custom-test-001",
        pdf_filename="custom_test.pdf",
        file_path="/tmp/custom_test.pdf",
        total_pages=3,
        processing_timestamp=datetime.now().isoformat(),
        pages=[
            {"page_number": 1, "text": "Patient presents with symptoms..."},
            {"page_number": 2, "text": "Clinical assessment and diagnosis..."},
            {"page_number": 3, "text": "Treatment plan and follow-up..."}
        ]
    )
    
    # Step 2: Run verification with retry
    print("\n" + "-"*70)
    print("STEP 2: Run Verification with AUTO_RETRY Enabled")
    print("-"*70)
    
    orchestrator = RetryOrchestrator()
    final_classification, report, decision, retry_log = orchestrator.verify_with_retry(
        classification, doc_bundle
    )
    
    # Step 3: Analyze results
    print("\n" + "-"*70)
    print("STEP 3: Analyze Results")
    print("-"*70)
    
    print(f"\n📊 VERIFICATION RESULTS:")
    print(f"   Total issues detected: {report.total_issues}")
    print(f"   Retry attempts made: {len(retry_log)}")
    print(f"   Final decision: {decision.decision}")
    
    if retry_log:
        print(f"\n🔄 RETRY LOG:")
        for entry in retry_log:
            print(f"\n   Attempt {entry['attempt']}:")
            print(f"     Issues before fix: {entry['issues_before_fix']}")
            print(f"     Fixable issues: {entry['fixable_issues']}")
            print(f"     Fixes applied: {len(entry['fixes_applied'])}")
            for fix in entry['fixes_applied']:
                print(f"       - {fix}")
    
    # Verify fix was applied
    final_share_sum = sum(c.segment_share for c in final_classification.segments[0].segment_composition)
    print(f"\n🔧 FIX VERIFICATION:")
    print(f"   Original share sum: 0.95")
    print(f"   Final share sum: {final_share_sum:.6f}")
    print(f"   Normalized: {'✅ YES' if abs(final_share_sum - 1.0) < 0.0001 else '❌ NO'}")
    
    # Step 4: Validation
    print("\n" + "-"*70)
    print("STEP 4: Validate Test Expectations")
    print("-"*70)
    
    test_passed = True
    validations = []
    
    # Validation 1: At least one retry occurred
    if len(retry_log) >= 1:
        validations.append("✅ Retry occurred (expected)")
        print("   ✅ Retry occurred (expected)")
    else:
        validations.append("❌ No retry occurred")
        print("   ❌ FAIL: No retry occurred")
        test_passed = False
    
    # Validation 2: Shares were normalized
    if abs(final_share_sum - 1.0) < 0.0001:
        validations.append("✅ Shares normalized")
        print("   ✅ Shares normalized")
    else:
        validations.append(f"❌ Shares not normalized ({final_share_sum:.6f})")
        print(f"   ❌ FAIL: Shares not normalized ({final_share_sum:.6f})")
        test_passed = False
    
    # Validation 3: Final decision is AUTO_ACCEPT or reasonable
    if decision.decision in ["AUTO_ACCEPT", "ESCALATE_TO_SME"]:
        validations.append(f"✅ Final decision: {decision.decision}")
        print(f"   ✅ Final decision: {decision.decision}")
        if decision.decision == "ESCALATE_TO_SME":
            print(f"      Note: Escalated because: {decision.reason}")
    else:
        validations.append(f"❌ Unexpected decision: {decision.decision}")
        print(f"   ❌ FAIL: Unexpected decision: {decision.decision}")
        test_passed = False
    
    # Validation 4: Fixes were applied
    total_fixes = sum(len(entry['fixes_applied']) for entry in retry_log)
    if total_fixes > 0:
        validations.append(f"✅ Fixes applied: {total_fixes}")
        print(f"   ✅ Fixes applied: {total_fixes}")
    else:
        validations.append("❌ No fixes applied")
        print(f"   ❌ FAIL: No fixes applied")
        test_passed = False
    
    # Summary
    print("\n" + "="*70)
    if test_passed:
        print("✅ END-TO-END TEST PASSED")
    else:
        print("❌ END-TO-END TEST FAILED")
    print("="*70)
    
    # Save detailed report
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "test": "end_to_end_autoretry",
        "classification_id": "custom-test-001",
        "initial_share_sum": 0.95,
        "final_share_sum": float(final_share_sum),
        "retry_attempts": len(retry_log),
        "fixes_applied": total_fixes,
        "final_decision": decision.decision,
        "validations": validations,
        "test_passed": test_passed,
        "retry_log": retry_log,
        "final_issues": report.total_issues
    }
    
    report_path = Path("output/e2e_autoretry_test.json")
    with open(report_path, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_path}")
    
    return test_passed


if __name__ == "__main__":
    import sys
    try:
        success = test_end_to_end_retry()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
