"""
Test SME Review Interface Programmatically
"""

from pathlib import Path
import json
from src.evaluation.review_helper import SMEReviewHelper

print("="*60)
print("SME REVIEW INTERFACE TEST")
print("="*60)

# Initialize helper
helper = SMEReviewHelper()

# Step 1: Check review queue
print("\n📋 Step 1: Checking Review Queue...")
stats = helper.get_review_stats()
print(f"   Total Packets: {stats['total_packets']}")
print(f"   Pending: {stats['pending']}")
print(f"   Completed: {stats['completed']}")
print(f"   Completion Rate: {stats['completion_rate']:.1%}")

pending = helper.list_pending_reviews()
if pending:
    print(f"\n   Pending Documents:")
    for p in pending:
        print(f"     • {p['doc_id']} - {p['total_issues']} issue(s)")
else:
    print("\n   ⚠️  No pending reviews found")
    print("   Run: ./test_sme_packet_generation.sh first")
    exit(0)

# Step 2: Load a packet
print("\n📦 Step 2: Loading Packet...")
doc_id = pending[0]['doc_id']
packet = helper.load_packet(doc_id)

print(f"   ✅ Loaded: {packet.doc_id}")
print(f"   PDF: {packet.pdf_filename}")
print(f"   Pages: {packet.total_pages}")
print(f"   V5 Decision: {packet.v5_decision}")
print(f"   Total Issues: {packet.total_issues}")

# Step 3: Display classification
print("\n🏥 Step 3: Primary Agent Classification...")
classif = packet.primary_agent_classification
print(f"   Dominant Type: {classif.dominant_type_overall}")
print(f"   Segments: {classif.number_of_segments}")

# Step 4: Display issues
print(f"\n⚠️  Step 4: Issues ({packet.total_issues})...")
for i, issue in enumerate(packet.issues_summary[:3], 1):
    print(f"   {i}. [{issue['severity']}] {issue['agent']}")
    print(f"      {issue['message'][:60]}...")

# Step 5: Submit a test review
print("\n✍️  Step 5: Submitting Test Review...")
helper.save_review(
    doc_id=doc_id,
    reviewer_name="Test Reviewer",
    agrees_with_primary=True,
    review_notes="Test review - classification looks correct",
    confidence=1.0
)

# Step 6: Verify ground truth created
print("\n✅ Step 6: Verifying Ground Truth...")
gt_file = Path(f"output/ground_truth/gt_{doc_id}.json")
if gt_file.exists():
    with open(gt_file) as f:
        gt = json.load(f)
    
    print(f"   Ground Truth Created: {gt_file}")
    print(f"   Source: {gt['ground_truth_source']}")
    print(f"   Reviewer: {gt['sme_review']['reviewer_name']}")
    print(f"   Agrees: {gt['sme_review']['agrees_with_primary_agent']}")
else:
    print("   ❌ Ground truth not created")

# Step 7: Check updated stats
print("\n📊 Step 7: Updated Statistics...")
stats = helper.get_review_stats()
print(f"   Pending: {stats['pending']}")
print(f"   Completed: {stats['completed']}")
print(f"   Completion Rate: {stats['completion_rate']:.1%}")

print("\n" + "="*60)
print("✅ SME REVIEW INTERFACE TEST COMPLETE")
print("="*60)
print("\nNext: Test the Jupyter notebook interface")
print("   jupyter lab notebooks/sme_review_interface.ipynb")
