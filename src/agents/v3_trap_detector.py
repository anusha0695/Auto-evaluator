"""V3: Trap Detector - Hybrid pattern matching + LLM approach"""

import re
import json
from typing import List, Tuple
from pathlib import Path
from google import genai
from google.genai.types import GenerateContentConfig
from ..schemas import (
    ClassificationOutput,
    DocumentBundle,
    Issue,
    IssueSeverity,
    PresenceLevel,
    DocumentType
)
from ..config import settings


class V3TrapDetector:
    """
    Detects domain-specific classification traps using hybrid approach:
    - Rule-based pattern matching for obvious traps (vendors, keywords)
    - LLM contextual analysis for subtle traps (gene names in history, etc.)
    """
    
    # Trap patterns for rule-based detection
    VENDOR_ROUTINE_LABS = ["quest", "labcorp", "lab corp"]
    ADMIN_KEYWORDS = ["requisition", "authorization number", "fax cover", "test request", "specimen receipt"]
    
    def __init__(self, client: genai.Client):
        self.client = client
        # Load prompt
        prompt_path = Path("Prompts/V3_Trap_Detector_and_Rule_Violation_Checker.txt")
        if not prompt_path.exists():
            raise FileNotFoundError(f"V3 prompt not found: {prompt_path}")
        with open(prompt_path, "r") as f:
            self.prompt_base = f.read()
    
    def validate(
        self,
        classification: ClassificationOutput,
        doc_bundle: DocumentBundle
    ) -> Tuple[List[Issue], int]:
        """
        Run trap detection checks
        
        Returns:
            (issues, traps_triggered_count)
        """
        issues = []
        issue_counter = 0
        
        # Get full text
        full_text = self._get_full_text(doc_bundle)
        
        # PHASE 1: Rule-based trap detection
        rule_issues = self._run_rule_traps(classification, full_text, issue_counter)
        issues.extend(rule_issues)
        issue_counter = len(issues)
        
        # PHASE 2: LLM contextual analysis
        try:
            llm_issues = self._run_llm_check(classification, full_text, issue_counter)
            issues.extend(llm_issues)
        except Exception as e:
            print(f"    V3: LLM check failed: {e}")
        
        return issues, len(issues)
    
    def _get_full_text(self, doc_bundle: DocumentBundle) -> str:
        """Combine all page texts"""
        return "\n".join(page['text'] for page in doc_bundle.pages)
    
    def _run_rule_traps(
        self,
        classification: ClassificationOutput,
        full_text: str,
        start_counter: int
    ) -> List[Issue]:
        """Pattern-based trap detection"""
        issues = []
        
        # Trap 1: Routine lab vendors + Genomic PRIMARY
        for mix in classification.document_mixture:
            if mix.document_type == DocumentType.GENOMIC_REPORT and mix.presence_level == PresenceLevel.PRIMARY:
                # Check vendor signals
                has_routine_vendor = any(
                    vendor in vendor_sig.lower()
                    for vendor in self.VENDOR_ROUTINE_LABS
                    for vendor_sig in classification.vendor_signals
                )
                
                if has_routine_vendor:
                    issues.append(Issue(
                        ig_id="IG-5",
                        issue_id=f"V3-{start_counter + len(issues):04d}",
                        agent="V3",
                        severity=IssueSeverity.BLOCKER,
                        message=f"Routine lab vendor detected ({', '.join(classification.vendor_signals)}) but Genomic Report marked PRIMARY - likely routine labs, not genomic",
                        location={"document_type": "Genomic Report", "field": "presence_level"},
                        suggested_fix="Reclassify as 'Other' or downgrade to MENTION_ONLY",
                        auto_fixable=False
                    ))
        
        # Trap 2: Admin keywords + Report classification
        has_admin = any(keyword in full_text.lower() for keyword in self.ADMIN_KEYWORDS)
        if has_admin:
            for mix in classification.document_mixture:
                if mix.document_type in [DocumentType.GENOMIC_REPORT, DocumentType.PATHOLOGY_REPORT]:
                    if mix.presence_level != PresenceLevel.NO_EVIDENCE:
                        issues.append(Issue(
                            ig_id="IG-2",
                            issue_id=f"V3-{start_counter + len(issues):04d}",
                            agent="V3",
                            severity=IssueSeverity.BLOCKER,
                            message=f"Administrative keywords found (requisition/authorization/fax) but {mix.document_type.value} marked as {mix.presence_level.value}",
                            location={"document_type": mix.document_type.value},
                            suggested_fix="Reclassify as 'Other' (administrative document)",
                            auto_fixable=False
                        ))
        
        # Trap 3: Header/footer content check (basic pattern)
        header_footer_patterns = [
            r'page \d+ of \d+',
            r'fax.*?\d{3}[-.]?\d{3}[-.]?\d{4}',
            r'medical record number|mrn',
            r'date of birth.*?\d{2}/\d{2}/\d{4}'
        ]
        
        # Check evidence snippets for header/footer content
        for seg in classification.segments:
            for comp in seg.segment_composition:
                for evidence in comp.top_evidence:
                    snippet_lower = evidence.snippet.lower()
                    for pattern in header_footer_patterns:
                        if re.search(pattern, snippet_lower, re.IGNORECASE):
                            issues.append(Issue(
                                ig_id="IG-2",
                                issue_id=f"V3-{start_counter + len(issues):04d}",
                                agent="V3",
                                severity=IssueSeverity.MINOR,
                                message=f"Evidence snippet in Segment {seg.segment_index} appears to contain header/footer content: '{evidence.snippet[:50]}...'",
                                location={"segment_index": seg.segment_index, "document_type": comp.document_type.value},
                                suggested_fix="Exclude header/footer content from evidence",
                                auto_fixable=False
                            ))
                            break  # Only flag once per evidence
        
        return issues
    
    def _run_llm_check(
        self,
        classification: ClassificationOutput,
        full_text: str,
        start_counter: int
    ) -> List[Issue]:
        """LLM-based contextual trap detection"""
        
        classification_json = classification.model_dump_json(indent=2)
        
        full_prompt = f"""{self.prompt_base}

===== INPUT FORMAT =====

You will receive:
1. "classification_output": Complete ClassificationOutput JSON
2. "document_text": First 4000 characters for context

===== OUTPUT FORMAT =====

Return JSON array of issues:
{{
  "ig_id": "IG-4",
  "issue_id": "V3-LLM-0001",
  "severity": "BLOCKER",
  "location": {{"document_type": "Genomic Report"}},
  "message": "...",
  "suggested_fix": "...",
  "auto_fixable": false
}}

Severity: BLOCKER | MAJOR | MINOR
If no traps: return []

===== INPUT DATA =====

CLASSIFICATION OUTPUT:
{classification_json}

DOCUMENT TEXT (first 4000 chars):
{full_text[:4000]}

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
                    ig_id=raw.get("ig_id", "X1"),
                    issue_id=raw.get("issue_id", f"V3-LLM-{start_counter + len(issues):04d}"),
                    agent="V3",
                    severity=IssueSeverity(raw.get("severity", "MAJOR")),
                    message=raw.get("message", "Unknown trap"),
                    location=raw.get("location"),
                    suggested_fix=raw.get("suggested_fix"),
                    auto_fixable=raw.get("auto_fixable", False)
                ))
            
            return issues
            
        except json.JSONDecodeError as e:
            print(f"    V3 LLM: Failed to parse JSON: {e}")
            return []
        except Exception as e:
            print(f"    V3 LLM: Error: {e}")
            raise
