#!/bin/bash
# Test SME Packet Generation End-to-End

echo "=========================================="
echo "SME PACKET GENERATION TEST"
echo "=========================================="
echo ""

# Step 1: Run classification pipeline on a document
echo "Step 1: Running classification pipeline..."
python run_classification.py data/input/raw_documents/doc2_6.pdf

echo ""
echo "Step 2: Checking V5 decision..."
V5_DECISION=$(python -c "import json; f=open('output/classification_result_verification.json'); d=json.load(f); print(d['arbiter_decision']['decision'])")
echo "V5 Decision: $V5_DECISION"

if [ "$V5_DECISION" = "ESCALATE_TO_SME" ]; then
    echo ""
    echo "Step 3: Generating SME packet..."
    python test_phase6_simple.py
    
    echo ""
    echo "✅ SME Packet Generated!"
    echo "   Location: output/sme_packets/sme_packet_doc2_6.json"
    
    # Display packet summary
    echo ""
    echo "Packet Summary:"
    python -c "
import json
with open('output/sme_packets/sme_packet_doc2_6.json') as f:
    packet = json.load(f)
print(f\"  Doc ID: {packet['doc_id']}\")
print(f\"  Issues: {packet['total_issues']}\")
print(f\"  Status: {packet['review_status']}\")
print(f\"  PDF: {packet['pdf_filename']}\")
"
else
    echo ""
    echo "⚠️  Document was $V5_DECISION, not ESCALATE_TO_SME"
    echo "   SME packet generation is only for escalated cases"
fi

echo ""
echo "=========================================="
echo "READY FOR SME REVIEW INTERFACE TEST"
echo "=========================================="
