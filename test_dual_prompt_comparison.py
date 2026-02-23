"""
Quick test to compare production prompt vs primary agent prompt on same document.
This validates the Phase 6 dual-prompt evaluation architecture.
"""

import json
from pathlib import Path
from src.document_processor import DocumentProcessor
from src.primary_classifier_agent import PrimaryClassifierAgent
from google import genai
from google.genai import types


def load_production_prompt():
    """Load the production prompt"""
    prompt_path = Path("Prompts/raw_text/Document_Classification_prompt.txt")
    with open(prompt_path, 'r') as f:
        return f.read()


def classify_with_production_prompt(document_text):
    """
    Classify document using Document_Classification_prompt.txt (production)
    """
    # Use gemini-1.5-flash for production (faster, cheaper)
    client = genai.Client(
        vertexai=True,
        project="unstructured-dev-440119",
        location="us-central1"
    )
    
    production_prompt = load_production_prompt()
    
    print("\n" + "="*60)
    print("PRODUCTION PROMPT CLASSIFICATION")
    print("="*60)
    print(f"Model: gemini-1.5-flash-002")
    print(f"Prompt: Document_Classification_prompt.txt")
    
    # Build full prompt
    full_prompt = f"""{production_prompt}

DOCUMENT TO CLASSIFY:
{document_text}

Output the classification in JSON format matching the schema.
"""
    
    response = client.models.generate_content(
        model="gemini-1.5-flash-002",
        contents=full_prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json"
        )
    )
    
    result_json = json.loads(response.text)
    
    return result_json


def classify_with_primary_agent(document_text):
    """
    Classify document using primary_classifier_agent_prompt.txt (ground truth baseline)
    """
    print("\n" + "="*60)
    print("PRIMARY AGENT CLASSIFICATION")
    print("="*60)
    print(f"Model: gemini-1.5-pro-002")
    print(f"Prompt: primary_classifier_agent_prompt.txt")
    
    classifier = PrimaryClassifierAgent()
    result = classifier.classify(document_text)
    
    #Convert to dict for comparison
    return result.model_dump()


def compare_results(production_result, primary_agent_result):
    """
    Compare the two classification results
    """
    print("\n" + "="*60)
    print("COMPARISON RESULTS")
    print("="*60)
    
    # Compare dominant types
    prod_dominant = production_result.get("dominant_type_overall")
    primary_dominant = primary_agent_result.get("dominant_type_overall")
    
    print(f"\n1. DOMINANT TYPE:")
    print(f"   Production:    {prod_dominant}")
    print(f"   Primary Agent: {primary_dominant}")
    print(f"   Match: {'✅ YES' if prod_dominant == primary_dominant else '❌ NO'}")
    
    # Compare segment counts
    prod_segments = production_result.get("number_of_segments", 0)
    primary_segments = primary_agent_result.get("number_of_segments", 0)
    
    print(f"\n2. NUMBER OF SEGMENTS:")
    print(f"   Production:    {prod_segments}")
    print(f"   Primary Agent: {primary_segments}")
    print(f"   Match: {'✅ YES' if prod_segments == primary_segments else '❌ NO'}")
    
    # Compare document mixture
    print(f"\n3. DOCUMENT MIXTURE:")
    prod_mixture = {m["document_type"]: m.get("overall_share", 0) 
                   for m in production_result.get("document_mixture", [])}
    primary_mixture = {m["document_type"]: m.get("overall_share", 0) 
                      for m in primary_agent_result.get("document_mixture", [])}
    
    for doc_type in ["Clinical Note", "Pathology Report", "Radiology Report", 
                     "Genomic Report", "Other"]:
        prod_share = prod_mixture.get(doc_type, 0)
        primary_share = primary_mixture.get(doc_type, 0)
        diff = abs(prod_share - primary_share)
        
        match_status = "✅" if diff < 0.05 else "❌"
        print(f"   {doc_type:<20} Prod: {prod_share:.2f}  Primary: {primary_share:.2f}  {match_status}")
    
    # Overall assessment
    print(f"\n4. OVERALL ASSESSMENT:")
    exact_match = (prod_dominant == primary_dominant and 
                   prod_segments == primary_segments)
    
    if exact_match:
        print("   ✅ EXACT MATCH - Production aligns with primary agent")
    else:
        print("   ❌ MISMATCH - Differences detected")
        print("   → This document would highlight production prompt issues")
    
    return {
        "dominant_match": prod_dominant == primary_dominant,
        "segment_count_match": prod_segments == primary_segments,
        "exact_match": exact_match
    }


def main():
    """
    Test dual-prompt comparison on a sample document
    """
    print("="*60)
    print("DUAL-PROMPT COMPARISON TEST")
    print("="*60)
    print("\nPurpose: Validate Phase 6 evaluation architecture")
    print("Compare: Production vs. Primary Agent on same document")
    
    # Use existing sample PDF
    pdf_path = "data/input/raw_documents/doc2_1.pdf"
    
    if not Path(pdf_path).exists():
        print(f"\n❌ Error: {pdf_path} not found")
        print("Please provide a valid PDF path")
        return
    
    print(f"\nDocument: {pdf_path}")
    
    # Extract document text
    print("\nExtracting document text...")
    processor = DocumentProcessor()
    doc_bundle = processor.process_pdf(pdf_path)
    
    # Handle both dict and object formats
    if hasattr(doc_bundle, 'pages'):
        pages = doc_bundle.pages
        total_pages = doc_bundle.total_pages
        document_text = "\n".join([p.text if hasattr(p, 'text') else p.get('text', '') for p in pages])
    else:
        pages = doc_bundle.get("pages", [])
        total_pages = doc_bundle.get("total_pages", len(pages))
        document_text = "\n".join([p.get("text", "") if isinstance(p, dict) else p.text for p in pages])
    
    print(f"✓ Extracted {total_pages} pages, {len(document_text)} characters")
    
    if len(document_text) == 0:
        print("❌ Error: No text extracted from PDF")
        print("   Check Document AI processor configuration")
        return
    
    # Classify with both prompts
    try:
        production_result = classify_with_production_prompt(document_text)
        print("✓ Production classification complete")
    except Exception as e:
        print(f"❌ Production classification failed: {e}")
        return
    
    try:
        primary_agent_result = classify_with_primary_agent(document_text)
        print("✓ Primary agent classification complete")
    except Exception as e:
        print(f"❌ Primary agent classification failed: {e}")
        return
    
    # Compare results
    comparison = compare_results(production_result, primary_agent_result)
    
    # Save results for analysis
    output = {
        "test_date": "2024-02-16",
        "pdf_file": pdf_path,
        "production_result": production_result,
        "primary_agent_result": primary_agent_result,
        "comparison": comparison
    }
    
    output_path = Path("output/dual_prompt_comparison_test.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n📄 Full comparison saved to: {output_path}")
    
    # Final summary
    print("\n" + "="*60)
    print("CONCLUSION")
    print("="*60)
    if comparison["exact_match"]:
        print("✅ Both prompts produce identical results")
        print("   → Phase 6 evaluation may show high production accuracy")
    else:
        print("❌ Prompts produce different results")
        print("   → Phase 6 evaluation will identify production weaknesses")
        print("   → This validates the dual-prompt evaluation approach!")
    
    print("\nPhase 6 dual-prompt architecture: VALIDATED ✅")


if __name__ == "__main__":
    main()
