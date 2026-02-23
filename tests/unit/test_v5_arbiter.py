"""
Test V5 Arbiter decision logic with all scenarios
"""

from src.schemas import (
    Issue,
    IssueSeverity,
    VerificationReport
)
from src.agents.v5_arbiter import V5ArbiterAgent


def test_scenario_1_no_issues():
    """Scenario 1: No issues → AUTO_ACCEPT"""
    print("\n" + "="*60)
    print("SCENARIO 1: No Issues")
    print("="*60)
    
    report = VerificationReport(
        issues=[],
        v1_validation_passed=True,
        v2_consistency_score=1.0,
        v3_traps_triggered=0,
        v4_evidence_quality_score=1.0,
        has_blocker_issues=False,
        total_issues=0,
        llm_calls_made=2
    )
    
    arbiter = V5ArbiterAgent()
    decision = arbiter.decide(report)
    
    print(f"  Decision: {decision.decision}")
    print(f"  Reason: {decision.reason}")
    assert decision.decision == "AUTO_ACCEPT", f"Expected AUTO_ACCEPT, got {decision.decision}"
    print("  ✓ PASSED")
    return decision


def test_scenario_2_minor_only():
    """Scenario 2: Only MINOR issues → AUTO_ACCEPT"""
    print("\n" + "="*60)
    print("SCENARIO 2: MINOR Issues Only")
    print("="*60)
    
    report = VerificationReport(
        issues=[
            Issue(
                ig_id="IG-3",
                issue_id="V4-0001",
                agent="V4",
                severity=IssueSeverity.MINOR,
                message="Snippet slightly too long (35 words)",
                location={"segment": 1},
                suggested_fix="Trim to 30 words",
                auto_fixable=True
            ),
            Issue(
                ig_id="IG-3",
                issue_id="V4-0002",
                agent="V4",
                severity=IssueSeverity.MINOR,
                message="Minor formatting issue in anchor",
                location={"segment": 2},
                suggested_fix="Clean anchor text",
                auto_fixable=True
            )
        ],
        v1_validation_passed=True,
        v2_consistency_score=1.0,
        v3_traps_triggered=0,
        v4_evidence_quality_score=0.95,
        has_blocker_issues=False,
        total_issues=2,
        llm_calls_made=2
    )
    
    arbiter = V5ArbiterAgent()
    decision = arbiter.decide(report)
    
    print(f"  Decision: {decision.decision}")
    print(f"  Reason: {decision.reason}")
    print(f"  MINOR count: {decision.minor_count}")
    assert decision.decision == "AUTO_ACCEPT", f"Expected AUTO_ACCEPT, got {decision.decision}"
    assert decision.minor_count == 2
    print("  ✓ PASSED")
    return decision


def test_scenario_3_one_fixable_major():
    """Scenario 3: 1 fixable MAJOR → AUTO_RETRY"""
    print("\n" + "="*60)
    print("SCENARIO 3: One Fixable MAJOR Issue")
    print("="*60)
    
    report = VerificationReport(
        issues=[
            Issue(
                ig_id="IG-8",
                issue_id="V2-0001",
                agent="V2",
                severity=IssueSeverity.MAJOR,
                message="Segment shares sum to 0.98 instead of 1.0",
                location={"segment": 1},
                suggested_fix="Normalize shares to sum to 1.0",
                auto_fixable=True
            )
        ],
        v1_validation_passed=True,
        v2_consistency_score=0.85,
        v3_traps_triggered=0,
        v4_evidence_quality_score=1.0,
        has_blocker_issues=False,
        total_issues=1,
        llm_calls_made=1
    )
    
    arbiter = V5ArbiterAgent()
    decision = arbiter.decide(report)
    
    print(f"  Decision: {decision.decision}")
    print(f"  Reason: {decision.reason}")
    print(f"  MAJOR count: {decision.major_count}, Fixable: {decision.fixable_count}")
    assert decision.decision == "AUTO_RETRY", f"Expected AUTO_RETRY, got {decision.decision}"
    assert decision.major_count == 1
    assert decision.fixable_count == 1
    print("  ✓ PASSED")
    return decision


def test_scenario_4_two_fixable_major():
    """Scenario 4: 2 fixable MAJOR → AUTO_RETRY"""
    print("\n" + "="*60)
    print("SCENARIO 4: Two Fixable MAJOR Issues")
    print("="*60)
    
    report = VerificationReport(
        issues=[
            Issue(
                ig_id="IG-8",
                issue_id="V2-0001",
                agent="V2",
                severity=IssueSeverity.MAJOR,
                message="Segment 1 shares sum to 0.97",
                location={"segment": 1},
                suggested_fix="Normalize",
                auto_fixable=True
            ),
            Issue(
                ig_id="IG-8",
                issue_id="V2-0002",
                agent="V2",
                severity=IssueSeverity.MAJOR,
                message="Segment 2 shares sum to 1.03",
                location={"segment": 2},
                suggested_fix="Normalize",
                auto_fixable=True
            )
        ],
        v1_validation_passed=True,
        v2_consistency_score=0.75,
        v3_traps_triggered=0,
        v4_evidence_quality_score=1.0,
        has_blocker_issues=False,
        total_issues=2,
        llm_calls_made=1
    )
    
    arbiter = V5ArbiterAgent()
    decision = arbiter.decide(report)
    
    print(f"  Decision: {decision.decision}")
    print(f"  Reason: {decision.reason}")
    print(f"  MAJOR count: {decision.major_count}, Fixable: {decision.fixable_count}")
    assert decision.decision == "AUTO_RETRY", f"Expected AUTO_RETRY, got {decision.decision}"
    assert decision.major_count == 2
    assert decision.fixable_count == 2
    print("  ✓ PASSED")
    return decision


def test_scenario_5_one_nonfixable_major():
    """Scenario 5: 1 non-fixable MAJOR → ESCALATE_TO_SME"""
    print("\n" + "="*60)
    print("SCENARIO 5: One Non-Fixable MAJOR Issue")
    print("="*60)
    
    report = VerificationReport(
        issues=[
            Issue(
                ig_id="IG-3",
                issue_id="V4-0001",
                agent="V4",
                severity=IssueSeverity.MAJOR,
                message="Evidence snippet does not support claimed document type",
                location={"segment": 1},
                suggested_fix="Requires manual review of classification logic",
                auto_fixable=False
            )
        ],
        v1_validation_passed=True,
        v2_consistency_score=1.0,
        v3_traps_triggered=0,
        v4_evidence_quality_score=0.65,
        has_blocker_issues=False,
        total_issues=1,
        llm_calls_made=2
    )
    
    arbiter = V5ArbiterAgent()
    decision = arbiter.decide(report)
    
    print(f"  Decision: {decision.decision}")
    print(f"  Reason: {decision.reason}")
    print(f"  MAJOR count: {decision.major_count}, Fixable: {decision.fixable_count}")
    assert decision.decision == "ESCALATE_TO_SME", f"Expected ESCALATE_TO_SME, got {decision.decision}"
    assert decision.major_count == 1
    assert decision.fixable_count == 0
    print("  ✓ PASSED")
    return decision


def test_scenario_6_three_major():
    """Scenario 6: 3+ MAJOR issues → ESCALATE_TO_SME"""
    print("\n" + "="*60)
    print("SCENARIO 6: Three MAJOR Issues")
    print("="*60)
    
    report = VerificationReport(
        issues=[
            Issue(
                ig_id="IG-8",
                issue_id="V2-0001",
                agent="V2",
                severity=IssueSeverity.MAJOR,
                message="Issue 1",
                location={},
                suggested_fix="Fix 1",
                auto_fixable=True
            ),
            Issue(
                ig_id="IG-7",
                issue_id="V2-0002",
                agent="V2",
                severity=IssueSeverity.MAJOR,
                message="Issue 2",
                location={},
                suggested_fix="Fix 2",
                auto_fixable=True
            ),
            Issue(
                ig_id="IG-3",
                issue_id="V4-0001",
                agent="V4",
                severity=IssueSeverity.MAJOR,
                message="Issue 3",
                location={},
                suggested_fix="Fix 3",
                auto_fixable=True
            )
        ],
        v1_validation_passed=True,
        v2_consistency_score=0.60,
        v3_traps_triggered=0,
        v4_evidence_quality_score=0.70,
        has_blocker_issues=False,
        total_issues=3,
        llm_calls_made=2
    )
    
    arbiter = V5ArbiterAgent()
    decision = arbiter.decide(report)
    
    print(f"  Decision: {decision.decision}")
    print(f"  Reason: {decision.reason}")
    print(f"  MAJOR count: {decision.major_count}")
    assert decision.decision == "ESCALATE_TO_SME", f"Expected ESCALATE_TO_SME, got {decision.decision}"
    assert decision.major_count == 3
    print("  ✓ PASSED")
    return decision


def test_scenario_7_blocker():
    """Scenario 7: BLOCKER issue → ESCALATE_TO_SME"""
    print("\n" + "="*60)
    print("SCENARIO 7: BLOCKER Issue")
    print("="*60)
    
    report = VerificationReport(
        issues=[
            Issue(
                ig_id="IG-6",
                issue_id="V2-0001",
                agent="V2",
                severity=IssueSeverity.BLOCKER,
                message="Page ranges overlap: Segment 1 ends at page 5, Segment 2 starts at page 5",
                location={"segment": 2},
                suggested_fix="Adjust page boundaries",
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
    
    arbiter = V5ArbiterAgent()
    decision = arbiter.decide(report)
    
    print(f"  Decision: {decision.decision}")
    print(f"  Reason: {decision.reason}")
    print(f"  BLOCKER count: {decision.blocker_count}")
    assert decision.decision == "ESCALATE_TO_SME", f"Expected ESCALATE_TO_SME, got {decision.decision}"
    assert decision.blocker_count == 1
    print("  ✓ PASSED")
    return decision


if __name__ == "__main__":
    print("\n" + "="*70)
    print("V5 ARBITER DECISION LOGIC TEST SUITE")
    print("="*70)
    
    try:
        # Test all 7 scenarios
        test_scenario_1_no_issues()
        test_scenario_2_minor_only()
        test_scenario_3_one_fixable_major()
        test_scenario_4_two_fixable_major()
        test_scenario_5_one_nonfixable_major()
        test_scenario_6_three_major()
        test_scenario_7_blocker()
        
        print("\n" + "="*70)
        print("ALL 7 SCENARIOS PASSED ✅")
        print("="*70)
        print("\nDecision Coverage:")
        print("  AUTO_ACCEPT:    Scenarios 1, 2")
        print("  AUTO_RETRY:     Scenarios 3, 4")
        print("  ESCALATE_TO_SME: Scenarios 5, 6, 7")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
