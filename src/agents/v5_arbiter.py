"""V5: Arbiter Agent - Final decision maker for classification output"""

from typing import Tuple
from ..schemas import (
    VerificationReport,
    ArbiterDecision,
    IssueSeverity
)


class V5ArbiterAgent:
    """
    Makes final decision based on V1-V4 verification issues.
    
    Decision Logic (Rule-Based):
    - Any BLOCKER → ESCALATE_TO_SME
    - ≥3 MAJOR issues → ESCALATE_TO_SME
    - ≥2 non-fixable MAJOR → ESCALATE_TO_SME
    - 1-2 fixable MAJOR → AUTO_RETRY
    - Only MINOR → AUTO_ACCEPT
    - No issues → AUTO_ACCEPT
    """
    
    def decide(
        self,
        verification_report: VerificationReport
    ) -> ArbiterDecision:
        """
        Make final decision based on verification issues
        
        Args:
            verification_report: Report from V1-V4 agents
            
        Returns:
            ArbiterDecision with decision code and reasoning
        """
        issues = verification_report.issues
        
        # Count issues by severity
        blocker_count = len([i for i in issues if i.severity == IssueSeverity.BLOCKER])
        major_count = len([i for i in issues if i.severity == IssueSeverity.MAJOR])
        minor_count = len([i for i in issues if i.severity == IssueSeverity.MINOR])
        fixable_count = len([i for i in issues if i.auto_fixable])
        
        # Count non-fixable major issues
        major_non_fixable = len([
            i for i in issues 
            if i.severity == IssueSeverity.MAJOR and not i.auto_fixable
        ])
        
        major_fixable = len([
            i for i in issues
            if i.severity == IssueSeverity.MAJOR and i.auto_fixable
        ])
        
        # Decision logic
        decision, reason = self._apply_decision_rules(
            blocker_count=blocker_count,
            major_count=major_count,
            minor_count=minor_count,
            major_fixable=major_fixable,
            major_non_fixable=major_non_fixable,
            total_issues=len(issues)
        )
        
        return ArbiterDecision(
            decision=decision,
            reason=reason,
            issues_analyzed=len(issues),
            blocker_count=blocker_count,
            major_count=major_count,
            minor_count=minor_count,
            fixable_count=fixable_count
        )
    
    def _apply_decision_rules(
        self,
        blocker_count: int,
        major_count: int,
        minor_count: int,
        major_fixable: int,
        major_non_fixable: int,
        total_issues: int
    ) -> Tuple[str, str]:
        """
        Apply quantitative decision thresholds
        
        Returns:
            (decision_code, reason)
        """
        
        # Rule 1: Any BLOCKER → ESCALATE
        if blocker_count > 0:
            return (
                "ESCALATE_TO_SME",
                f"Found {blocker_count} BLOCKER issue(s) indicating critical failure. Human review required."
            )
        
        # Rule 2: ≥3 MAJOR → ESCALATE
        if major_count >= 3:
            return (
                "ESCALATE_TO_SME",
                f"Found {major_count} MAJOR issues. Too many significant errors to auto-correct confidently."
            )
        
        # Rule 3: ≥2 non-fixable MAJOR → ESCALATE
        if major_non_fixable >= 2:
            return (
                "ESCALATE_TO_SME",
                f"Found {major_non_fixable} non-fixable MAJOR issues. Requires human judgment."
            )
        
        # Rule 4: 1 non-fixable MAJOR → ESCALATE (conservative)
        if major_non_fixable >= 1:
            return (
                "ESCALATE_TO_SME",
                f"Found {major_non_fixable} non-fixable MAJOR issue(s). Human expertise needed to resolve."
            )
        
        # Rule 5: 1-2 fixable MAJOR → RETRY
        if 1 <= major_fixable <= 2:
            return (
                "AUTO_RETRY",
                f"Found {major_fixable} fixable MAJOR issue(s). Will apply suggested fixes and retry classification."
            )
        
        # Rule 6: Only MINOR issues → ACCEPT
        if minor_count > 0 and major_count == 0 and blocker_count == 0:
            return (
                "AUTO_ACCEPT",
                f"Found only {minor_count} MINOR issue(s). Issues are tolerable and do not affect classification validity."
            )
        
        # Rule 7: No issues → ACCEPT
        if total_issues == 0:
            return (
                "AUTO_ACCEPT",
                "No issues detected. Classification output is valid and compliant."
            )
        
        # Fallback: Should not reach here, but default to escalation for safety
        return (
            "ESCALATE_TO_SME",
            f"Ambiguous issue pattern ({major_count} MAJOR, {minor_count} MINOR). Defaulting to human review for safety."
        )
