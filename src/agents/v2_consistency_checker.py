"""V2: Consistency Checker - Hybrid rule-based + LLM approach"""

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


class V2ConsistencyChecker:
    """
    Validates internal consistency using hybrid approach:
    - Fast rule-based pre-filtering for math/logic errors
    - LLM semantic validation for nuanced consistency checks
    """
    
    SHARE_TOLERANCE = 0.01
    
    def __init__(self, client: genai.Client):
        self.client = client
        # Load prompt
        prompt_path = Path("Prompts/V2_Internal_Consistency_Auditor.txt")
        if not prompt_path.exists():
            raise FileNotFoundError(f"V2 prompt not found: {prompt_path}")
        with open(prompt_path, "r") as f:
            self.prompt_base = f.read()
    
    def validate(
        self,
        classification: ClassificationOutput,
        doc_bundle: DocumentBundle
    ) -> Tuple[List[Issue], float]:
        """
        Run consistency checks
        
        Returns:
            (issues, consistency_score)
            consistency_score: 0.0-1.0, where 1.0 = perfect consistency
        """
        issues = []
        issue_counter = 0
        
        # PHASE 1: Rule-based pre-filter (fast, zero cost)
        rule_issues = self._run_rule_checks(classification, issue_counter)
        issues.extend(rule_issues)
        issue_counter = len(issues)
        
        # If critical rule violations, skip LLM
        has_blocker = any(i.severity == IssueSeverity.BLOCKER for i in rule_issues)
        if has_blocker:
            print("    V2: BLOCKER issues found in rules, skipping LLM validation")
            return issues, 0.0
        
        # PHASE 2: LLM semantic validation
        try:
            llm_issues = self._run_llm_check(classification, doc_bundle, issue_counter)
            issues.extend(llm_issues)
        except Exception as e:
            print(f"    V2: LLM check failed: {e}")
            # Continue with rule-based issues only
        
        # Compute score
        score = self._compute_score(issues)
        
        return issues, score
    
    def _run_rule_checks(
        self,
        classification: ClassificationOutput,
        start_counter: int
    ) -> List[Issue]:
        """Fast rule-based consistency checks"""
        issues = []
        
        # Check 1: Segment shares sum to 1.0
        for seg in classification.segments:
            total = sum(comp.segment_share for comp in seg.segment_composition)
            if not (1.0 - self.SHARE_TOLERANCE <= total <= 1.0 + self.SHARE_TOLERANCE):
                issues.append(Issue(
                    ig_id="IG-8",
                    issue_id=f"V2-{start_counter + len(issues):04d}",
                    agent="V2",
                    severity=IssueSeverity.MAJOR,
                    message=f"Segment {seg.segment_index} shares sum to {total:.3f} instead of 1.0",
                    location={"segment_index": seg.segment_index, "field": "segment_share"},
                    suggested_fix="Normalize shares to sum to 1.0",
                    auto_fixable=True
                ))
        
        # Check 2: Overall shares sum to 1.0
        total_overall = sum(mix.overall_share for mix in classification.document_mixture)
        if not (1.0 - self.SHARE_TOLERANCE <= total_overall <= 1.0 + self.SHARE_TOLERANCE):
            issues.append(Issue(
                ig_id="IG-8",
                issue_id=f"V2-{start_counter + len(issues):04d}",
                agent="V2",
                severity=IssueSeverity.MAJOR,
                message=f"Document mixture overall_share sums to {total_overall:.3f} instead of 1.0",
                location={"field": "document_mixture"},
                suggested_fix="Normalize overall_share values",
                auto_fixable=True
            ))
        
        # Check 3: Page ranges (no overlaps, start <= end)
        segments = sorted(classification.segments, key=lambda s: s.start_page)
        for i, seg in enumerate(segments):
            # Check start <= end
            if seg.start_page > seg.end_page:
                issues.append(Issue(
                    ig_id="IG-6",
                    issue_id=f"V2-{start_counter + len(issues):04d}",
                    agent="V2",
                    severity=IssueSeverity.BLOCKER,
                    message=f"Segment {seg.segment_index}: start_page ({seg.start_page}) > end_page ({seg.end_page})",
                    location={"segment_index": seg.segment_index},
                    suggested_fix="Swap or adjust page range",
                    auto_fixable=False
                ))
            
            # Check for overlaps with next segment
            if i < len(segments) - 1:
                next_seg = segments[i + 1]
                if seg.end_page >= next_seg.start_page:
                    issues.append(Issue(
                        ig_id="IG-6",
                        issue_id=f"V2-{start_counter + len(issues):04d}",
                        agent="V2",
                        severity=IssueSeverity.BLOCKER,
                        message=f"Segment {seg.segment_index} ends at {seg.end_page}, overlaps with Segment {next_seg.segment_index} starting at {next_seg.start_page}",
                        location={"segment_index": seg.segment_index},
                        suggested_fix="Adjust page ranges to eliminate overlap",
                        auto_fixable=False
                    ))
        
        return issues
    
    def _run_llm_check(
        self,
        classification: ClassificationOutput,
        doc_bundle: DocumentBundle,
        start_counter: int
    ) -> List[Issue]:
        """LLM-based semantic validation"""
        
        # Prepare input
        classification_json = classification.model_dump_json(indent=2)
        
        # NEW: Get full text from all segments (not just 3000 char preview)
        segment_texts = {}
        for seg in classification.segments:
            seg_text = ""
            for page_num in range(seg.start_page, seg.end_page + 1):
                if page_num <= len(doc_bundle.pages):
                    page_data = doc_bundle.pages[page_num - 1]
                    seg_text += f"--- PAGE {page_num} ---\n{page_data['text']}\n\n"
            segment_texts[seg.segment_index] = seg_text
        
        segment_texts_json = json.dumps(segment_texts, indent=2)
        
        # Build full prompt with INPUT/OUTPUT format
        full_prompt = f"""{self.prompt_base}

===== INPUT FORMAT =====

You will receive:
1. "classification_output": The complete ClassificationOutput JSON
2. "segment_texts": Full text from all segments for semantic validation

===== OUTPUT FORMAT =====

Return a JSON array of issue objects. Each issue must have:
{{
  "ig_id": "IG-6",
  "issue_id": "V2-LLM-0001",
  "severity": "BLOCKER",
  "location": {{"segment_index": 1, "field": "segment_share"}},
  "message": "...",
  "suggested_fix": "...",
  "auto_fixable": true
}}

Severity: BLOCKER | MAJOR | MINOR
If no issues: return []

===== INPUT DATA =====

CLASSIFICATION OUTPUT:
{classification_json}

SEGMENT TEXTS (full text from document):
{segment_texts_json}

===== YOUR OUTPUT (JSON array only) =====
"""
        
        # Call LLM
        try:
            response = self.client.models.generate_content(
                model=settings.gemini_model,
                contents=full_prompt,
                config=GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            
            # Parse JSON
            llm_issues_raw = json.loads(response.text)
            
            # Convert to Issue objects
            issues = []
            for raw_issue in llm_issues_raw:
                issues.append(Issue(
                    ig_id=raw_issue.get("ig_id", "IG-9"),
                    issue_id=raw_issue.get("issue_id", f"V2-LLM-{start_counter + len(issues):04d}"),
                    agent="V2",
                    severity=IssueSeverity(raw_issue.get("severity", "MAJOR")),
                    message=raw_issue.get("message", "Unknown issue"),
                    location=raw_issue.get("location"),
                    suggested_fix=raw_issue.get("suggested_fix"),
                    auto_fixable=raw_issue.get("auto_fixable", False)
                ))
            
            return issues
            
        except json.JSONDecodeError as e:
            print(f"    V2 LLM: Failed to parse JSON response: {e}")
            return []
        except Exception as e:
            print(f"    V2 LLM: Error: {e}")
            raise
    
    def _compute_score(self, issues: List[Issue]) -> float:
        """Compute consistency score from issues"""
        if not issues:
            return 1.0
        
        penalty = 0.0
        for issue in issues:
            if issue.severity == IssueSeverity.BLOCKER:
                penalty += 0.4
            elif issue.severity == IssueSeverity.MAJOR:
                penalty += 0.2
            else:
                penalty += 0.05
        
        return max(0.0, 1.0 - penalty)
