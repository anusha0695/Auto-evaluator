"""
Dual Classification Runner - Run both production and primary agent on same document
"""

from pathlib import Path
from src.production_classifier import ProductionClassifier
from src.primary_classifier_agent import PrimaryClassifierAgent
from src.document_processor import DocumentProcessor
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_dual_classification(pdf_path: str):
    """
    Run both production and primary classifiers on the same document
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        dict with both results and simple comparison
    """
    logger.info(f"Running dual classification on: {pdf_path}")
    
    # 1. Production Classifier (PDF bytes → gemini-2.5-flash)
    logger.info("Running PRODUCTION classifier...")
    production_classifier = ProductionClassifier()
    production_result = production_classifier.classify(pdf_path)
    
    # 2. Primary Agent (text extraction → gemini model from settings)
    logger.info("Running PRIMARY AGENT classifier...")
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
    
    # 3. Simple comparison
    comparison = {
        "dominant_type_match": production_result.dominant_type == primary_result.dominant_type_overall,
        "production_type": production_result.dominant_type,
        "primary_agent_type": primary_result.dominant_type_overall,
        "all_production_types": production_result.all_types,
        "primary_agent_segments": primary_result.number_of_segments
    }
    
    logger.info(f"Comparison: {comparison}")
    
    return {
        "pdf_file": Path(pdf_path).name,
        "production_result": {
            "dominant_type": production_result.dominant_type,
            "all_types": production_result.all_types,
            "classifications": [
                {
                    "document_type": c.document_type,
                    "confidence": c.confidence,
                    "starting_page": c.starting_page_num
                }
                for c in production_result.classifications
            ],
            "vendor": production_result.vendor
        },
        "primary_agent_result": primary_result.model_dump(),
        "comparison": comparison
    }


def main():
    """Test dual classification"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python run_dual_classification.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print("\n" + "="*70)
    print("DUAL CLASSIFICATION COMPARISON")
    print("="*70)
    print(f"Document: {Path(pdf_path).name}\n")
    
    result = run_dual_classification(pdf_path)
    
    print("\n" + "-"*70)
    print("PRODUCTION PROMPT RESULT")
    print("-"*70)
    print(f"Dominant Type: {result['production_result']['dominant_type']}")
    print(f"All Types: {', '.join(result['production_result']['all_types'])}")
    print(f"Vendor: {result['production_result']['vendor']}")
    
    print("\n" + "-"*70)
    print("PRIMARY AGENT RESULT")
    print("-"*70)
    print(f"Dominant Type: {result['primary_agent_result']['dominant_type_overall']}")
    print(f"Segments: {result['primary_agent_result']['number_of_segments']}")
    
    print("\n" + "-"*70)
    print("COMPARISON")
    print("-"*70)
    comp = result['comparison']
    match_symbol = "✅" if comp['dominant_type_match'] else "❌"
    print(f"{match_symbol} Dominant Type Match: {comp['dominant_type_match']}")
    print(f"   Production: {comp['production_type']}")
    print(f"   Primary Agent: {comp['primary_agent_type']}")
    
    # Save full results
    output_path = Path("output/dual_classification_result.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n📄 Full results saved to: {output_path}")
    
    if comp['dominant_type_match']:
        print("\n✅ MATCH - Both prompts agree on dominant type")
    else:
        print("\n❌ MISMATCH - Production prompt differs from primary agent")
        print("   → This case demonstrates the value of Phase 6 evaluation")


if __name__ == "__main__":
    main()
