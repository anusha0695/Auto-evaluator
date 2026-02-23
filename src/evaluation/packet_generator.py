"""
SME Packet Generator - Creates review packets for escalated cases
"""

from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from .ground_truth_schemas import SMEPacket, SMEReviewStatus
from src.schemas import ClassificationOutput, VerificationReport, ArbiterDecision
from src.production_schemas import ProductionResult
import json
import logging

logger = logging.getLogger(__name__)


class SMEPacketGenerator:
    """Generate SME review packets for ESCALATE_TO_SME cases"""
    
    def generate_packet(
        self,
        pdf_path: str,
        primary_classification: ClassificationOutput,
        verification_report: VerificationReport,
        arbiter_decision: ArbiterDecision,
        production_result: Optional[ProductionResult] = None,
        document_bundle_path: Optional[str] = None
    ) -> SMEPacket:
        """
        Generate SME review packet
        
        Args:
            pdf_path: Path to PDF file
            primary_classification: Primary agent classification
            verification_report: Full V1-V5 verification report
            arbiter_decision: V5 decision
            production_result: Optional production classifier result for comparison
            document_bundle_path: Optional path to saved DocumentBundle JSON
            
        Returns:
            SMEPacket ready for review
        """
        if arbiter_decision.decision != "ESCALATE_TO_SME":
            raise ValueError(
                f"Can only generate packets for ESCALATE_TO_SME decisions, "
                f"got: {arbiter_decision.decision}"
            )
        
        pdf_file = Path(pdf_path)
        doc_id = pdf_file.stem
        
        logger.info(f"Generating SME packet for: {doc_id}")
        
        # Format issues for SME review
        issues_summary = self._format_issues(verification_report)
        
        # Check if production differs (if provided)
        production_differs = None
        production_dict = None
        if production_result:
            production_differs = (
                production_result.dominant_type != primary_classification.dominant_type_overall
            )
            production_dict = {
                "dominant_type": production_result.dominant_type,
                "all_types": production_result.all_types,
                "vendor": production_result.vendor
            }
        
        
        # Calculate total pages from segments
        total_pages = len(primary_classification.segments) if primary_classification.segments else 1
        
        packet = SMEPacket(
            doc_id=doc_id,
            pdf_filename=pdf_file.name,
            pdf_path=str(pdf_file.absolute()),
            total_pages=total_pages,
            primary_agent_classification=primary_classification,
            v5_decision=arbiter_decision.decision,
            total_issues=len(verification_report.issues),
            issues_summary=issues_summary,
            production_classification=production_dict,
            production_differs=production_differs,
            document_bundle_path=document_bundle_path,
            review_status=SMEReviewStatus.PENDING
        )
        
        logger.info(f"SME packet generated: {packet.total_issues} issues to review")
        
        return packet
    
    def _format_issues(self, verification_report: VerificationReport) -> list:
        """Format issues for human-readable SME review"""
        formatted_issues = []
        
        for issue in verification_report.issues:
            formatted_issue = {
                "id": issue.issue_id,
                "agent": issue.agent,
                "severity": issue.severity.value,
                "message": issue.message,
                "location": issue.location if issue.location else "General",
                "suggested_fix": issue.suggested_fix if issue.suggested_fix else "Manual review needed"
            }
            formatted_issues.append(formatted_issue)
        
        # Sort by severity (BLOCKER > MAJOR > MINOR)
        severity_order = {"BLOCKER": 0, "MAJOR": 1, "MINOR": 2}
        formatted_issues.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        return formatted_issues
    
    def save_packet(self, packet: SMEPacket, output_dir: str = "output/sme_packets") -> Path:
        """
        Save SME packet to JSON file
        
        Args:
            packet: SME packet to save
            output_dir: Directory to save packets
            
        Returns:
            Path to saved packet file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"sme_packet_{packet.doc_id}.json"
        file_path = output_path / filename
        
        with open(file_path, 'w') as f:
            json.dump(packet.model_dump(mode='json'), f, indent=2, default=str)
        
        logger.info(f"SME packet saved to: {file_path}")
        
        return file_path
    
    def load_packet(self, packet_path: str) -> SMEPacket:
        """Load SME packet from JSON file"""
        with open(packet_path, 'r') as f:
            data = json.load(f)
        
        return SMEPacket(**data)


def main():
    """Test SME packet generator"""
    import sys
    
    # Load existing classification and verification results
    classif_path = "output/classification_result.json"
    verif_path = "output/classification_result_verification.json"
    
    if not Path(classif_path).exists() or not Path(verif_path).exists():
        print("Error: Run classification first to generate test data")
        print(f"  Missing: {classif_path} or {verif_path}")
        sys.exit(1)
    
    # Load data
    with open(classif_path) as f:
        classif_data = json.load(f)
    with open(verif_path) as f:
        verif_data = json.load(f)
    
    # Reconstruct objects
    primary_classification = ClassificationOutput(**classif_data)
    verification_report = VerificationReport(**verif_data["verification_report"])
    arbiter_decision = ArbiterDecision(**verif_data["arbiter_decision"])
    
    # Check if this was escalated
    if arbiter_decision.decision != "ESCALATE_TO_SME":
        print(f"Note: This document was {arbiter_decision.decision}, not ESCALATE_TO_SME")
        print("Generating packet anyway for demonstration...")
    
    # Generate packet
    generator = SMEPacketGenerator()
    
    # Find the PDF path (assume it's in test data)
    pdf_path = "data/input/raw_documents/doc2_6.pdf"
    
    packet = generator.generate_packet(
        pdf_path=pdf_path,
        primary_classification=primary_classification,
        verification_report=verification_report,
        arbiter_decision=arbiter_decision
    )
    
    # Save packet
    saved_path = generator.save_packet(packet)
    
    # Display summary
    print("\n" + "="*60)
    print("SME PACKET GENERATED")
    print("="*60)
    print(f"Document: {packet.pdf_filename}")
    print(f"Doc ID: {packet.doc_id}")
    print(f"V5 Decision: {packet.v5_decision}")
    print(f"Total Issues: {packet.total_issues}")
    print(f"\nIssues Summary:")
    for issue in packet.issues_summary[:3]:  # Show first 3
        print(f"  [{issue['severity']}] {issue['agent']}: {issue['message'][:80]}...")
    
    if packet.total_issues > 3:
        print(f"  ... and {packet.total_issues - 3} more issues")
    
    print(f"\n📄 Packet saved to: {saved_path}")


if __name__ == "__main__":
    main()
