"""Verification Runner - Orchestrates all V1-V4 agents"""

from typing import Tuple
from google import genai
from ..config import settings
from ..schemas import (
    ClassificationOutput,
    DocumentBundle,
    VerificationReport,
    Issue,
    IssueSeverity
)
from .v1_schema_validator import V1SchemaValidator
from .v2_consistency_checker import V2ConsistencyChecker
from .v3_trap_detector import V3TrapDetector
from .v4_evidence_quality import V4EvidenceQualityAssessor
from .v5_arbiter import V5ArbiterAgent
from .output_saver import AgentOutputSaver


class VerificationRunner:
    """
    Orchestrates all V1-V5 verification agents.
    Runs agents in sequence and consolidates results into unified report.
    """
    
    def __init__(self):
        """Initialize all agents and Gemini client"""
        # Initialize Gemini client for LLM-based agents
        self.client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location
        )
        
        # Initialize agents
        self.v1 = V1SchemaValidator()
        self.v2 = V2ConsistencyChecker(self.client)
        self.v3 = V3TrapDetector(self.client)
        self.v4 = V4EvidenceQualityAssessor(self.client)
        self.v5 = V5ArbiterAgent()
    
    def run_all(
        self,
        classification: ClassificationOutput,
        doc_bundle: DocumentBundle
    ) -> VerificationReport:
        """
        Run all verification agents (V1-V5) and return unified report
        
        Args:
            classification: Output from primary classifier
            doc_bundle: Original document bundle
            
        Returns:
            VerificationReport with all issues and scores
        """
        # NEW: Initialize output saver
        saver = AgentOutputSaver(doc_bundle.doc_id)
        saver.save_primary_classification(classification)
        
        all_issues = []
        llm_calls = 0
        
        print("\n" + "="*60)
        print("RUNNING VERIFICATION AGENTS (V1-V4)")
        print("="*60)
        
        # V1: Schema validation (rule-based, no LLM)
        print("  V1: Schema & Completeness Validator (rule-based)...")
        v1_issues = self.v1.validate(classification, doc_bundle)
        saver.save_agent_output("v1_schema_validation", v1_issues)
        all_issues.extend(v1_issues)
        v1_passed = len([i for i in v1_issues if i.severity == IssueSeverity.BLOCKER]) == 0
        print(f"      ✓ Issues found: {len(v1_issues)}")
        
        # V2: Consistency checking (hybrid: rules + LLM)
        print("  V2: Consistency Checker (hybrid)...")
        v2_issues, consistency_score = self.v2.validate(classification, doc_bundle)
        saver.save_agent_output("v2_consistency_check", v2_issues, consistency_score)
        all_issues.extend(v2_issues)
        # Count LLM call (only if no BLOCKER in V1 and V2 rules)
        v2_blocker_in_rules = any(
            i.severity == IssueSeverity.BLOCKER 
            for i in v2_issues 
            if "V2-" in i.issue_id and not "LLM" in i.issue_id
        )
        if not v1_passed or not v2_blocker_in_rules:
            pass  # LLM was skipped
        else:
            llm_calls += 1
        print(f"      ✓ Issues found: {len(v2_issues)}, Consistency score: {consistency_score:.2f}")
        
        # V3: Trap detection (hybrid: patterns + LLM)
        print("  V3: Trap Detector (hybrid)...")
        v3_issues, traps_triggered = self.v3.validate(classification, doc_bundle)
        saver.save_agent_output("v3_trap_detection", v3_issues, metadata={"traps_triggered": traps_triggered})
        all_issues.extend(v3_issues)
        llm_calls += 1
        print(f"      ✓ Traps detected: {traps_triggered}")
        
        # V4: Evidence quality (full LLM) - NOW WITH DOCUMENTBUNDLE
        print("  V4: Evidence Quality Assessor (LLM with PDF verification)...")
        v4_issues, evidence_score = self.v4.validate(classification, doc_bundle)
        saver.save_agent_output("v4_evidence_quality", v4_issues, evidence_score)
        all_issues.extend(v4_issues)
        llm_calls += 1
        print(f"      ✓ Issues found: {len(v4_issues)}, Quality score: {evidence_score:.2f}")
        
        # Build consolidated report
        report = VerificationReport(
            issues=all_issues,
            v1_validation_passed=v1_passed,
            v2_consistency_score=consistency_score,
            v3_traps_triggered=traps_triggered,
            v4_evidence_quality_score=evidence_score,
            has_blocker_issues=any(i.severity == IssueSeverity.BLOCKER for i in all_issues),
            total_issues=len(all_issues),
            llm_calls_made=llm_calls
        )
        
        # V5: Arbiter decision (rule-based, no LLM)
        print("  V5: Arbiter (decision maker)...")
        arbiter_decision = self.v5.decide(report)
        saver.save_arbiter_decision(
            decision=arbiter_decision.decision,
            reasoning=arbiter_decision.reason  # Fixed: attribute is 'reason' not 'reasoning'
        )
        print(f"      → Decision: {arbiter_decision.decision}")
        
        # Save final report
        saver.save_verification_report(report.model_dump(mode='json'))
        
        return report, arbiter_decision
    
    def print_report_summary(self, report: VerificationReport):
        """Print human-readable verification report summary"""
        print("\n" + "="*60)
        print("VERIFICATION REPORT SUMMARY")
        print("="*60)
        print(f"✓ V1 Schema Valid:       {report.v1_validation_passed}")
        print(f"✓ V2 Consistency Score:  {report.v2_consistency_score:.2f}" if report.v2_consistency_score else "✓ V2 Consistency Score:  N/A")
        print(f"✓ V3 Traps Triggered:    {report.v3_traps_triggered}")
        print(f"✓ V4 Evidence Quality:   {report.v4_evidence_quality_score:.2f}" if report.v4_evidence_quality_score else "✓ V4 Evidence Quality:   N/A")
        print(f"\nTotal Issues: {report.total_issues}")
        print(f"LLM Calls:    {report.llm_calls_made}")
        
        if report.blocker_issues:
            print(f"\n🔴 BLOCKER Issues ({len(report.blocker_issues)}):")
            for issue in report.blocker_issues:
                print(f"  [{issue.agent}] {issue.message}")
        
        if report.major_issues:
            print(f"\n🟡 MAJOR Issues ({len(report.major_issues)}):")
            for issue in report.major_issues[:5]:  # Show first 5
                print(f"  [{issue.agent}] {issue.message}")
            if len(report.major_issues) > 5:
                print(f"  ... and {len(report.major_issues) - 5} more")
        
        if report.minor_issues:
            print(f"\n🟢 MINOR Issues ({len(report.minor_issues)}):")
            for issue in report.minor_issues[:3]:  # Show first 3
                print(f"  [{issue.agent}] {issue.message}")
            if len(report.minor_issues) > 3:
                print(f"  ... and {len(report.minor_issues) - 3} more")
        
        if not report.issues:
            print("\n✅ No issues detected! Classification output is valid.")
