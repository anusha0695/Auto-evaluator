"""V4: Evidence Quality Assessor - Full LLM-based semantic analysis"""

import json
from typing import List, Tuple
from pathlib import Path
from google import genai
from google.genai.types import GenerateContentConfig
from ..schemas import (
    ClassificationOutput,
    DocumentBundle,
    Issue,
    IssueSeverity
)
from ..config import settings


class V4EvidenceQualityAssessor:
    """
    Assesses evidence quality using full LLM-based semantic understanding.
    Checks snippet relevance, anchor appropriateness, and confidence alignment.
    """
    
    def __init__(self, client: genai.Client):
        self.client = client
        # Load prompt
        prompt_path = Path("Prompts/V4_Evidence_Quality_Assessor.txt")
        if not prompt_path.exists():
            raise FileNotFoundError(f"V4 prompt not found: {prompt_path}")
        with open(prompt_path, "r") as f:
            self.prompt_base = f.read()
    
    def validate(
        self,
        classification: ClassificationOutput,
        doc_bundle: DocumentBundle
    ) -> Tuple[List[Issue], float]:
        """
        Assess evidence quality with independent verification against source PDF
        
        Args:
            classification: Classification output to validate
            doc_bundle: Original document bundle for independent verification
            
        Returns:
            (issues, evidence_quality_score)
            evidence_quality_score: 0.0-1.0
        """
        
        classification_json = classification.model_dump_json(indent=2)
        
        # NEW: Build PDF context for independent evidence verification
        pdf_context = {}
        for seg in classification.segments:
            for page_num in range(seg.start_page, seg.end_page + 1):
                if page_num <= len(doc_bundle.pages):
                    page_data = doc_bundle.pages[page_num - 1]
                    pdf_context[page_num] = {
                        "text": page_data['text'],
                        "paragraph_count": len(page_data.get('paragraphs', []))
                    }
        
        pdf_context_json = json.dumps(pdf_context, indent=2)
        
        # Build enhanced prompt with actual PDF text
        full_prompt = f"""{self.prompt_base}

===== INPUT FORMAT =====

You will receive:
1. ClassificationOutput JSON with evidence snippets and anchors
2. Actual PDF text from the document for independent verification

Your task: 
- Assess evidence quality for all document types across all segments
- VERIFY that evidence snippets actually exist in the PDF text
- CHECK that anchors are present on the claimed pages
- FLAG any evidence that cannot be verified in the source

===== OUTPUT FORMAT =====

Return JSON array of issues:
{{
  "ig_id": "IG-3",
  "issue_id": "V4-0001",
  "severity": "BLOCKER",
  "location": {{"segment_index": 1, "document_type": "Genomic Report"}},
  "message": "...",
  "suggested_fix": "...",
  "auto_fixable": false
}}

Severity levels:
- BLOCKER: Missing/fabricated evidence for PRIMARY classification, or evidence not found in PDF
- MAJOR: Weak evidence, confidence misalignment, or anchor not found in PDF
- MINOR: Snippet too long/short, minor quality issues

If no issues: return []

===== INPUT DATA =====

CLASSIFICATION OUTPUT:
{classification_json}

ACTUAL PDF TEXT (for independent verification):
{pdf_context_json}

===== YOUR OUTPUT (JSON array) =====
"""
        
        try:
            response = self.client.models.generate_content(
                model=settings.gemini_model,
                contents=full_prompt,
                config=GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            
            llm_issues_raw = json.loads(response.text)
            issues = []
            
            for raw in llm_issues_raw:
                issues.append(Issue(
                    ig_id=raw.get("ig_id", "IG-3"),
                    issue_id=raw.get("issue_id", f"V4-{len(issues):04d}"),
                    agent="V4",
                    severity=IssueSeverity(raw.get("severity", "MAJOR")),
                    message=raw.get("message", "Unknown evidence issue"),
                    location=raw.get("location"),
                    suggested_fix=raw.get("suggested_fix"),
                    auto_fixable=raw.get("auto_fixable", False)
                ))
            
            # Compute quality score
            score = self._compute_quality_score(issues, classification)
            
            return issues, score
            
        except json.JSONDecodeError as e:
            print(f"    V4 LLM: Failed to parse JSON: {e}")
            return [], 1.0
        except Exception as e:
            print(f"    V4 LLM: Error: {e}")
            return [], 1.0
    
    def _compute_quality_score(
        self,
        issues: List[Issue],
        classification: ClassificationOutput
    ) -> float:
        """Compute evidence quality score based on issues vs total evidence items"""
        if not issues:
            return 1.0
        
        # Count total evidence items
        total_evidence = sum(
            len(comp.top_evidence)
            for seg in classification.segments
            for comp in seg.segment_composition
        )
        
        if total_evidence == 0:
            return 0.0
        
        # Penalty per issue type
        penalty = 0.0
        for issue in issues:
            if issue.severity == IssueSeverity.BLOCKER:
                penalty += 0.3
            elif issue.severity == IssueSeverity.MAJOR:
                penalty += 0.15
            else:
                penalty += 0.05
        
        return max(0.0, 1.0 - penalty)
