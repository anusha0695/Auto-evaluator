"""
Test AUTO_RETRY logic with synthetic fixable issues

This test creates a classification with share sum errors and 
verifies that the retry orchestrator applies fixes and retries.
"""

import json
from pathlib import Path
from src.schemas import ClassificationOutput, DocumentBundle
from src.agents import RetryOrchestrator


def test_autoretry_with_share_error():
    """
    Test that AUTO_RETRY logic:
    1. Detects share sum error
    2. Applies fix
    3. Re-verifies
    4. Returns AUTO_ACCEPT or appropriate decision
    """
    
    print("\n" + "="*70)
    print("TEST: AUTO_RETRY with Share Normalization")
    print("="*70)
    
    # Load a valid classification as baseline
    classification_path = Path("output/classification_result.json")
    if not classification_path.exists():
        print("❌ Error: Need a baseline classification file")
        print("   Run: python run_classification.py data/input/raw_documents/doc2_1.pdf")
        return False
    
    with open(classification_path, 'r') as f:
        classification_data = json.load(f)
    
    # Create VALID classification first
    print("\n1. Loading valid classification...")
    classification = ClassificationOutput(**classification_data)
    original_shares = [c.segment_share for c in classification.segments[0].segment_composition]
    print(f"   Original shares sum: {sum(original_shares):.4f}")
    
    # Now MODIFY after validation (bypass Pydantic)
    print("\n2. Injecting share sum error (post-validation)...")
    # Reduce first share to create error (this modifies the object directly)
    classification.segments[0].segment_composition[0].segment_share = 0.10
    
    modified_shares = [c.segment_share for c in classification.segments[0].segment_composition]
    print(f"   Modified shares sum: {sum(modified_shares):.4f} (should be != 1.0)")
    
    # Create document bundle
    doc_bundle = DocumentBundle(
        doc_id="test-retry-001",
        pdf_filename="test_retry.pdf",
        file_path="/tmp/test_retry.pdf",
        total_pages=5,
        processing_timestamp="2024-01-01T00:00:00",
        pages=[{"page_number": i+1, "text": f"Page {i+1}"} for i in range(5)]
    )
    
    # Run verification with retry
    print("\n3. Running verification with AUTO_RETRY enabled...")
    orchestrator = RetryOrchestrator()
    final_classification, report, decision, retry_log = orchestrator.verify_with_retry(
        classification, doc_bundle
    )
    
    # Check results
    print("\n4. Results:")
    print(f"   Final decision: {decision.decision}")
    print(f"   Retry attempts: {len(retry_log)}")
    print(f"   Total issues found initially: {retry_log[0]['issues_before_fix'] if retry_log else report.total_issues}")
    print(f"   Total issues after retry: {report.total_issues}")
    
    if retry_log:
        print("\n5. Retry Log:")
        for entry in retry_log:
            print(f"\n   Attempt {entry['attempt']}:")
            print(f"     Issues before fix: {entry['issues_before_fix']}")
            print(f"     Fixable issues: {entry['fixable_issues']}")
            print(f"     Fixes applied: {len(entry['fixes_applied'])}")
            for fix in entry['fixes_applied']:
                print(f"       - {fix}")
    
    # Verify fix was applied
    final_shares = [c.segment_share for c in final_classification.segments[0].segment_composition]
    final_sum = sum(final_shares)
    print(f"\n6. Verification:")
    print(f"   Final shares sum: {final_sum:.6f}")
    print(f"   Shares normalized: {'✅ YES' if abs(final_sum - 1.0) < 0.0001 else '❌ NO'}")
    
    # Assert expectations
    success = True
    
    if len(retry_log) < 1:
        print("\n❌ FAIL: Expected at least 1 retry attempt")
        print(f"   Actual: {len(retry_log)} retries")
        success = False
    
    if abs(final_sum - 1.0) > 0.0001:
        print(f"\n❌ FAIL: Shares not normalized (sum={final_sum:.6f})")
        success = False
    
    if decision.decision == "AUTO_RETRY":
        print("\n❌ FAIL: Still in AUTO_RETRY state after max retries")
        success = False
    
    if success:
        print("\n" + "="*70)
        print("✅ TEST PASSED: AUTO_RETRY logic working correctly")
        print("="*70)
        print("\nKey findings:")
        print(f"  - Detected share sum error ({sum(modified_shares):.4f} != 1.0)")
        print(f"  - Applied {len(retry_log[0]['fixes_applied']) if retry_log else 0} auto-fixes")
        print(f"  - Successfully normalized shares to {final_sum:.6f}")
        print(f"  - Final decision: {decision.decision}")
    else:
        print("\n" + "="*70)
        print("❌ TEST FAILED: See errors above")
        print("="*70)
    
    return success


if __name__ == "__main__":
    try:
        success = test_autoretry_with_share_error()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
