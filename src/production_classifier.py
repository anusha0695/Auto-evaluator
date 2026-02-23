"""
Production Classifier - Uses Document_Classification_prompt.txt
This classifier represents the current production prompt that we want to evaluate.
"""

from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from .production_schemas import ProductionResult
import json
import logging

logger = logging.getLogger(__name__)


class ProductionClassifier:
    """
    Classifier using the production prompt (Document_Classification_prompt.txt).
    This is what we're evaluating against the primary agent baseline.
    
    Note: Returns ProductionResult (simple schema) not ClassificationOutput (complex schema)
    """
    
    def __init__(
        self,
        project_id: str = "medical-report-extraction",
        location: str = "us-central1",
        model_name: str = "gemini-2.5-flash"  # Latest flash model
    ):
        """
        Initialize production classifier
        
        Args:
            project_id: GCP project ID
            location: GCP region
            model_name: Gemini model to use
        """
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        
        # Initialize Gemini client
        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )
        
        # Load production prompt
        self.prompt_template = self._load_production_prompt()
        
        logger.info(f"Production Classifier initialized")
        logger.info(f"Model: {model_name}")
        logger.info(f"Project: {project_id}")
    
    def _load_production_prompt(self) -> str:
        """Load the production classification prompt"""
        prompt_path = Path("Prompts/raw_text/Document_Classification_prompt.txt")
        
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Production prompt not found: {prompt_path}. "
                "Please ensure Document_Classification_prompt.txt exists."
            )
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
        
        logger.info(f"Loaded production prompt: {len(prompt)} characters")
        return prompt
    
    def classify(
        self,
        pdf_path: str,
        doc_id: Optional[str] = None
    ) -> ProductionResult:
        """
        Classify a PDF document using the production prompt with multimodal input
        
        Args:
            pdf_path: Path to PDF file
            doc_id: Optional document identifier
            
        Returns:
            ProductionResult object (simple schema with document_type strings)
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Classifying PDF with production prompt (ID: {doc_id})")
        logger.info(f"PDF path: {pdf_path}")
        
        # Read PDF as bytes
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        logger.info(f"PDF size: {len(pdf_bytes):,} bytes")
        
        try:
            # Build multimodal content with PDF + prompt
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Part.from_bytes(
                        data=pdf_bytes,
                        mime_type="application/pdf"
                    ),
                    self.prompt_template
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            
            # Parse JSON response
            result_json = json.loads(response.text)
            
            # Validate and convert to ProductionResult
            production_result = ProductionResult(**result_json)
            
            logger.info(f"Production classification complete")
            logger.info(f"Dominant type: {production_result.dominant_type}")
            logger.info(f"All types: {production_result.all_types}")
            logger.info(f"Number of classifications: {len(production_result.classifications)}")
            
            return production_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.error(f"Response text: {response.text[:500]}...")
            raise ValueError(f"Invalid JSON from production classifier: {e}")
            
        except Exception as e:
            logger.error(f"Production classification failed: {e}")
            raise


def main():
    """Test the production classifier"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.production_classifier <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Classify directly from PDF
    classifier = ProductionClassifier()
    result = classifier.classify(pdf_path, doc_id=Path(pdf_path).stem)
    
    # Display
    print("\n" + "="*60)
    print("PRODUCTION CLASSIFIER RESULT")
    print("="*60)
    print(f"Document: {Path(pdf_path).name}")
    print(f"Dominant Type: {result.dominant_type}")
    print(f"All Types Found: {', '.join(result.all_types)}")
    print(f"Number of Classifications: {len(result.classifications)}")
    if result.vendor:
        print(f"Vendor: {result.vendor}")
    
    print(f"\nClassifications:")
    for i, classif in enumerate(result.classifications, 1):
        print(f"\n  {i}. {classif.document_type}")
        print(f"     Confidence: {classif.confidence:.2f}")
        print(f"     Starting Page: {classif.starting_page_num}")
        print(f"     Reasoning: {classif.reasoning[:100]}...")


if __name__ == "__main__":
    main()
