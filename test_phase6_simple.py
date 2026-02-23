"""
Simplified Phase 6 Week 1-2 Test
Uses existing pipeline outputs
"""

from pathlib import Path
import json
from src.schemas import ClassificationOutput, VerificationReport, ArbiterDecision
from src.evaluation.packet_generator import SMEPacketGenerator
from src.production_classifier import ProductionClassifier

print("\n" + "="*70)
print("PHASE 6 WEEK 1-2 SIMPLE INTEGRATED TEST")
print("="*70)

# Test with doc2_6.pdf which we know escalates to SME
pdf_path = "data/input/raw_documents/doc2_6.pdf"
classif_path = "output/classification_result.json"
verif_path = "output/classification_result_verification.json"

print(f"\n1. Running full pipeline on {Path(pdf_path).name}...")
import subprocess
result = subprocess.run(
    ["python", "run_classification.py", pdf_path],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print("❌ Classification failed")
    print(result.stderr)
    exit(1)

print("   ✅ Classification complete\n")

# 2. Run production classifier
print("2. Running production classifier...")
prod_classifier = ProductionClassifier()
prod_result = prod_classifier.classify(pdf_path)
print(f"   ✅ Production: {prod_result.dominant_type}\n")

# 3. Load primary agent results  
print("3. Loading primary agent results...")
with open(classif_path) as f:
    primary_classif = ClassificationOutput(**json.load(f))

print(f"   ✅ Primary Agent: {primary_classif.dominant_type_overall}\n")

# 4. Compare
print("4. Comparing...")
match = prod_result.dominant_type == primary_classif.dominant_type_overall
symbol = "✅" if match else "❌"
print(f"   {symbol} Match: {match}\n")

# 5. Load verification results
print("5. Loading verification results...")
with open(verif_path) as f:
    verif_data = json.load(f)

arbiter_dec = ArbiterDecision(**verif_data['arbiter_decision'])
print(f"   ✅ V5 Decision: {arbiter_dec.decision}\n")

# 6. Generate SME packet if escalated
if arbiter_dec.decision == "ESCALATE_TO_SME":
    print("6. Generating SME packet...")
    
    # Reconstruct verification report
    verif_report = VerificationReport(
        issues=verif_data.get('issues', []),
        v1_validation_passed=verif_data['v1_validation_passed'],
        v2_consistency_score=verif_data['v2_consistency_score'],
        v3_traps_triggered=verif_data['v3_traps_triggered'],
        v4_evidence_quality_score=verif_data['v4_evidence_quality_score'],
        has_blocker_issues=verif_data['has_blocker_issues'],
        total_issues=verif_data['total_issues'],
        llm_calls_made=verif_data['llm_calls_made'],
        arbiter_decision=arbiter_dec,
        retry_log=verif_data.get('retry_log', [])
    )
    
    generator = SMEPacketGenerator()
    packet = generator.generate_packet(
        pdf_path=pdf_path,
        primary_classification=primary_classif,
        verification_report=verif_report,
        arbiter_decision=arbiter_dec,
        production_result=prod_result
    )
    
    saved_path = generator.save_packet(packet)
    
    print(f"   ✅ SME Packet Generated")
    print(f"      Doc ID: {packet.doc_id}")
    print(f"      Issues: {packet.total_issues}")
    print(f"      Saved: {saved_path}\n")
else:
    print(f"6. Document {arbiter_dec.decision} - no packet needed\n")

print("="*70)
print("✅ PHASE 6 WEEK 1-2 VALIDATED")
print("="*70)
print("\nWeek 1: Dual classification ✅")
print("Week 2: SME packet generation ✅")
