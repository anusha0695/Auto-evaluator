"""
Test Phase 6 Week 1-2: Dual Classification + SME Packet Generation
"""

from pathlib import Path
import json
import logging
from src.production_classifier import ProductionClassifier
from src.primary_classifier_agent import PrimaryClassifierAgent
from src.document_processor import DocumentProcessor
from src.agents.verification_runner import VerificationRunner
from src.evaluation.packet_generator import SMEPacketGenerator
from src.schemas import ClassificationOutput

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_phase6_week1_2(pdf_path: str):
    """
    Complete test of Phase 6 Week 1-2 infrastructure:
    1. Run production classifier (PDF bytes)
    2. Run primary agent classifier (extracted text)
    3. Compare results
    4. Run verification (V1-V5)
    5. Generate SME packet if ESCALATE_TO_SME
    
    Args:
        pdf_path: Path to PDF file to test
    """
    print("\n" + "="*70)
    print("PHASE 6 WEEK 1-2 COMPREHENSIVE TEST")
    print("="*70)
    print(f"Document: {Path(pdf_path).name}\n")
    
    # ========== WEEK 1: DUAL CLASSIFICATION ==========
    print("▶ WEEK 1: Running Dual Classification...")
    print("-" * 70)
    
    # 1. Production Classifier
    print("\n1️⃣  Production Classifier (gemini-2.5-flash + PDF bytes)")
    production_classifier = ProductionClassifier()
    production_result = production_classifier.classify(pdf_path)
    
    print(f"   ✓ Dominant Type: {production_result.dominant_type}")
    print(f"   ✓ All Types: {', '.join(production_result.all_types)}")
    print(f"   ✓ Vendor: {production_result.vendor}")
    
    # 2. Primary Agent Classifier
    print("\n2️⃣  Primary Agent Classifier (gemini-2.5-flash + extracted text)")
    processor = DocumentProcessor()
    doc_bundle = processor.process_pdf(pdf_path)
    
    # Extract text
    if hasattr(doc_bundle, 'pages'):
        pages = doc_bundle.pages
        document_text = "\n".join([p.text if hasattr(p, 'text') else p.get('text', '') for p in pages])
    else:
        pages = doc_bundle.get("pages", [])
        document_text = "\n".join([p.get("text", "") if isinstance(p, dict) else p.text for p in pages])
    
    primary_classifier = PrimaryClassifierAgent()
    primary_result = primary_classifier.classify(document_text)
    
    print(f"   ✓ Dominant Type: {primary_result.dominant_type_overall}")
    print(f"   ✓ Segments: {primary_result.number_of_segments}")
    
    # 3. Comparison
    print("\n3️⃣  Comparison")
    dominant_match = production_result.dominant_type == primary_result.dominant_type_overall
    match_symbol = "✅" if dominant_match else "❌"
    
    print(f"   {match_symbol} Dominant Type Match: {dominant_match}")
    if not dominant_match:
        print(f"      Production: {production_result.dominant_type}")
        print(f"      Primary Agent: {primary_result.dominant_type_overall}")
    
    # 4. Run Verification (V1-V5)
    print("\n4️⃣  Running Verification Pipeline (V1-V5)...")
    verif_runner = VerificationRunner()
    verification_report = verif_runner.run_all(primary_result, doc_bundle)
    
    print(f"   ✓ V1 Schema Valid: {verification_report.v1_validation_passed}")
    print(f"   ✓ V2 Consistency: {verification_report.v2_consistency_score:.2f}")
    print(f"   ✓ V3 Traps: {verification_report.v3_traps_triggered}")
    print(f"   ✓ V4 Quality: {verification_report.v4_evidence_quality_score:.2f}")
    print(f"   ✓ Total Issues: {verification_report.total_issues}")
    print(f"   ✓ V5 Decision: {verification_report.arbiter_decision.decision}")
    
    # ========== WEEK 2: SME PACKET GENERATION ==========
    print("\n" + "="*70)
    print("▶ WEEK 2: SME Packet Generation")
    print("-" * 70)
    
    packet_result = None
    if verification_report.arbiter_decision.decision == "ESCALATE_TO_SME":
        print("\n✅ Document escalated to SME - Generating review packet...\n")
        
        generator = SMEPacketGenerator()
        packet = generator.generate_packet(
            pdf_path=pdf_path,
            primary_classification=primary_result,
            verification_report=verification_report,
            arbiter_decision=verification_report.arbiter_decision,
            production_result=production_result
        )
        
        # Save packet
        saved_path = generator.save_packet(packet)
        
        print(f"📦 SME Packet Generated:")
        print(f"   ✓ Doc ID: {packet.doc_id}")
        print(f"   ✓ Total Issues: {packet.total_issues}")
        print(f"   ✓ Review Status: {packet.review_status.value}")
        if packet.production_differs is not None:
            diff_symbol = "❌" if packet.production_differs else "✅"
            print(f"   {diff_symbol} Production Differs: {packet.production_differs}")
        
        print(f"\n   Top Issues:")
        for i, issue in enumerate(packet.issues_summary[:3], 1):
            print(f"      {i}. [{issue['severity']}] {issue['agent']}")
            print(f"         {issue['message'][:70]}...")
        
        if packet.total_issues > 3:
            print(f"      ... and {packet.total_issues - 3} more issues")
        
        print(f"\n   💾 Saved to: {saved_path}")
        
        packet_result = {
            "packet_generated": True,
            "packet_path": str(saved_path),
            "total_issues": packet.total_issues,
            "production_differs": packet.production_differs
        }
    else:
        print(f"\n✓ Document {verification_report.arbiter_decision.decision}")
        print("  No SME packet needed.")
        packet_result = {
            "packet_generated": False,
            "reason": verification_report.arbiter_decision.decision
        }
    
    # ========== SUMMARY ==========
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    summary = {
        "document": Path(pdf_path).name,
        "week1_dual_classification": {
            "production_dominant_type": production_result.dominant_type,
            "primary_agent_dominant_type": str(primary_result.dominant_type_overall),
            "dominant_type_match": dominant_match
        },
        "week1_verification": {
            "v5_decision": verification_report.arbiter_decision.decision,
            "total_issues": verification_report.total_issues,
            "consistency_score": verification_report.v2_consistency_score,
            "quality_score": verification_report.v4_evidence_quality_score
        },
        "week2_sme_packet": packet_result
    }
    
    # Save test results
    output_path = Path("output/phase6_week1_2_test_results.json")
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"\n✅ Week 1: Dual classification {'MATCHED' if dominant_match else 'DIFFERED'}")
    print(f"✅ Week 1: Verification complete - {verification_report.arbiter_decision.decision}")
    print(f"✅ Week 2: Packet {'generated' if packet_result['packet_generated'] else 'not needed'}")
    print(f"\n📄 Full results: {output_path}")
    
    return summary


def main():
    """Run tests on multiple documents"""
    import sys
    
    # Test documents
    test_docs = [
        "data/input/raw_documents/doc2_6.pdf",  # Known ESCALATE_TO_SME
        "data/input/raw_documents/doc_3.pdf",   # Known AUTO_ACCEPT
    ]
    
    # If specific doc provided, test only that
    if len(sys.argv) > 1:
        test_docs = [sys.argv[1]]
    
    print("\n" + "🧪" * 35)
    print(" PHASE 6 WEEK 1-2 TESTING SUITE")
    print("🧪" * 35)
    print(f"\nTesting {len(test_docs)} document(s)...\n")
    
    results = []
    for pdf_path in test_docs:
        if not Path(pdf_path).exists():
            print(f"⚠️  Skipping {pdf_path} - file not found")
            continue
        
        try:
            result = test_phase6_week1_2(pdf_path)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error testing {pdf_path}: {e}")
            import traceback
            traceback.print_exc()
    
    # Overall summary
    print("\n" + "="*70)
    print("OVERALL TEST RESULTS")
    print("="*70)
    print(f"Documents Tested: {len(results)}")
    
    escalated = sum(1 for r in results if r['week2_sme_packet']['packet_generated'])
    auto_decisions = len(results) - escalated
    
    print(f"  ✓ Escalated to SME: {escalated}")
    print(f"  ✓ Auto-decisions: {auto_decisions}")
    
    if results:
        matches = sum(1 for r in results if r['week1_dual_classification']['dominant_type_match'])
        print(f"\n  Production/Primary Agreement: {matches}/{len(results)} ({100*matches/len(results):.0f}%)")
        print("\n✅ Phase 6 Week 1-2 infrastructure validated!")
    else:
        print("\n⚠️  No documents successfully tested")


if __name__ == "__main__":
    main()
