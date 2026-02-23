"""Primary classifier agent using Google Gen AI SDK"""

from google import genai
from google.genai import types
import json
from pathlib import Path
from typing import Optional
from .config import settings
from .schemas import ClassificationOutput, DocumentBundle


class PrimaryClassifierAgent:
    """Call Gemini using Google Gen AI SDK with primary_classifier_agent_prompt.txt"""
    
    def __init__(self):
        """Initialize Gen AI SDK client with Vertex AI"""
        # Initialize client with Vertex AI and ADC
        self.client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location
        )
        print(f"Using Google Gen AI SDK with Vertex AI project: {settings.gcp_project_id}")
        
        # Load prompt template
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """Load primary classifier prompt from file"""
        prompt_path = Path(settings.prompt_dir) / settings.primary_prompt_file
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def classify(
        self,
        document_text: str,
        max_retries: int = 2
    ) -> ClassificationOutput:
        """
        Classify document using primary classifier prompt
        
        Args:
            document_text: Formatted document text (from DocumentBundle)
            max_retries: Maximum retry attempts for API failures
            
        Returns:
            Validated ClassificationOutput
            
        Raises:
            ValueError: If LLM output doesn't match schema after retries
        """
        for attempt in range(max_retries):
            try:
                # Construct full prompt
                full_prompt = self._construct_prompt(document_text)
                
                # Call Gemini using new SDK
                response = self.client.models.generate_content(
                    model=settings.gemini_model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=settings.gemini_temperature,
                        max_output_tokens=settings.gemini_max_tokens,
                    )
                )
                
                # Extract JSON from response
                classification_json = self._extract_json(response.text)
                
                # Validate against schema
                classification = ClassificationOutput(**classification_json)
                
                return classification
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    continue
                else:
                    raise ValueError(f"Classification failed after {max_retries} attempts: {e}")
    
    def _construct_prompt(self, document_text: str) -> str:
        """Combine prompt template with document text"""
        return f"{self.prompt_template}\n\n---\n\nDOCUMENT TO CLASSIFY:\n\n{document_text}"
    
    def _extract_json(self, response_text: str) -> dict:
        """
        Extract JSON from LLM response
        
        Handles cases where LLM wraps JSON in markdown code blocks
        """
        # Remove markdown code blocks if present
        text = response_text.strip()
        
        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        elif text.startswith("```"):
            text = text[3:]  # Remove ```
        
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        # Parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from LLM response: {e}\nResponse: {text[:500]}")
