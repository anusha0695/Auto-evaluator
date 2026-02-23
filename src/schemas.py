"""Pydantic schemas for type-safe data structures"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum


class DocumentType(str, Enum):
    """Document classification types"""
    CLINICAL_NOTE = "Clinical Note"
    PATHOLOGY_REPORT = "Pathology Report"
    GENOMIC_REPORT = "Genomic Report"
    RADIOLOGY_REPORT = "Radiology Report"
    OTHER = "Other"


class PresenceLevel(str, Enum):
    """Presence level of document type in segment"""
    PRIMARY = "PRIMARY"
    EMBEDDED_RAW = "EMBEDDED_RAW"
    MENTION_ONLY = "MENTION_ONLY"
    NO_EVIDENCE = "NO_EVIDENCE"


class Evidence(BaseModel):
    """Evidence snippet supporting classification"""
    page: int = Field(ge=1, description="1-indexed page number")
    snippet: str = Field(max_length=500, description="Evidence text snippet")
    anchors_found: List[str] = Field(description="Structural anchors identified")


class SegmentComposition(BaseModel):
    """Classification of a document type within a segment"""
    document_type: DocumentType
    presence_level: PresenceLevel
    confidence: float = Field(ge=0.0, le=1.0)
    segment_share: float = Field(ge=0.0, le=1.0)
    top_evidence: List[Evidence] = Field(default_factory=list)
    reasoning: str


class Segment(BaseModel):
    """Document segment with page range and classifications"""
    segment_index: int = Field(ge=1)
    start_page: int = Field(ge=1)
    end_page: int = Field(ge=1)
    segment_page_count: int = Field(ge=1)
    dominant_type: DocumentType
    embedded_types: List[DocumentType] = Field(default_factory=list)
    segment_composition: List[SegmentComposition]
    notes: Optional[str] = None
    
    @field_validator('segment_composition')
    @classmethod
    def validate_composition(cls, v):
        """Ensure all 5 document types present and shares sum to 1.0"""
        # Must have all 5 document types
        types_present = {comp.document_type for comp in v}
        required_types = set(DocumentType)
        if types_present != required_types:
            raise ValueError(f"segment_composition must include all 5 document types")
        
        # Shares must sum to ~1.0
        total_share = sum(comp.segment_share for comp in v)
        if not (0.99 <= total_share <= 1.01):
            raise ValueError(f"segment_share values must sum to 1.0, got {total_share}")
        
        return v


class DocumentMixture(BaseModel):
    """Overall document mixture classification"""
    document_type: DocumentType
    presence_level: PresenceLevel
    confidence: float = Field(ge=0.0, le=1.0)
    overall_share: float = Field(ge=0.0, le=1.0)
    overall_share_explanation: str
    top_evidence: List[Evidence] = Field(default_factory=list)
    reasoning: str


class SelfEvaluation(BaseModel):
    """LLM self-evaluation of classification"""
    evaluation_summary: str
    changes_made: str


class ClassificationOutput(BaseModel):
    """Primary classifier output schema matching primary_classifier_agent_prompt.txt"""
    dominant_type_overall: DocumentType
    segments: List[Segment]
    document_mixture: List[DocumentMixture]
    vendor_signals: List[str] = Field(default_factory=list)
    number_of_segments: int = Field(ge=1)
    self_evaluation: SelfEvaluation
    
    @field_validator('document_mixture')
    @classmethod
    def validate_mixture(cls, v):
        """Ensure all 5 document types present and shares sum to 1.0"""
        # Must have all 5 document types
        types_present = {mix.document_type for mix in v}
        if types_present != set(DocumentType):
            raise ValueError("document_mixture must include all 5 document types")
        
        # Overall shares should sum to ~1.0
        total_share = sum(mix.overall_share for mix in v)
        if not (0.99 <= total_share <= 1.01):
            raise ValueError(f"overall_share values must sum to 1.0, got {total_share}")
        
        return v


class DocumentBundle(BaseModel):
    """Parsed PDF document with metadata"""
    doc_id: str
    file_path: str
    total_pages: int
    pages: List[dict]  # List of {page_num, text, paragraphs, layout_metadata}
    processing_timestamp: str
    document_type: Optional[str] = Field(default=None, description="Classified document type (assigned after classification)")


# ===== Verification Agent Schemas =====

class IssueSeverity(str, Enum):
    """Issue severity levels for verification agents"""
    BLOCKER = "BLOCKER"    # Critical failure, must escalate
    MAJOR = "MAJOR"        # Significant error, needs fix
    MINOR = "MINOR"        # Minor issue, tolerable


class Issue(BaseModel):
    """Single validation issue from a verification agent (V1-V4)"""
    # Core fields (match prompt output format)
    ig_id: str = Field(description="IG code or identifier (e.g., 'IG-6', 'X1')")
    issue_id: str = Field(description="Unique ID with agent prefix (e.g., 'V2-0001')")
    agent: str = Field(description="Agent that detected issue (V1, V2, V3, or V4)")
    severity: IssueSeverity
    message: str = Field(description="Clear description of the issue")
    
    # Location context (optional)
    location: Optional[dict] = Field(default=None, description="Where issue occurs (e.g., {'segment_index': 1, 'field': 'segment_share'})")
    
    # Action guidance
    suggested_fix: Optional[str] = Field(default=None, description="How to fix the issue")
    auto_fixable: bool = Field(default=False, description="Whether issue can be auto-corrected")


class VerificationReport(BaseModel):
    """Unified report from all V1-V4 verification agents"""
    issues: List[Issue] = Field(default_factory=list)
    
    # Per-agent summaries
    v1_validation_passed: bool
    v2_consistency_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    v3_traps_triggered: int = Field(default=0, ge=0)
    v4_evidence_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    # Overall status
    has_blocker_issues: bool
    total_issues: int
    
    # Cost tracking
    llm_calls_made: int = Field(default=0, ge=0, description="Number of LLM API calls made")
    
    @property
    def blocker_issues(self) -> List[Issue]:
        """Get all BLOCKER severity issues"""
        return [i for i in self.issues if i.severity == IssueSeverity.BLOCKER]
    
    @property
    def major_issues(self) -> List[Issue]:
        """Get all MAJOR severity issues"""
        return [i for i in self.issues if i.severity == IssueSeverity.MAJOR]
    
    @property
    def minor_issues(self) -> List[Issue]:
        """Get all MINOR severity issues"""
        return [i for i in self.issues if i.severity == IssueSeverity.MINOR]


class ArbiterDecision(BaseModel):
    """V5 Arbiter final decision on classification output"""
    decision: str = Field(description="AUTO_ACCEPT | AUTO_RETRY | ESCALATE_TO_SME")
    reason: str = Field(description="Human-readable explanation for decision")
    issues_analyzed: int = Field(ge=0, description="Total issues reviewed")
    blocker_count: int = Field(ge=0)
    major_count: int = Field(ge=0)
    minor_count: int = Field(ge=0)
    fixable_count: int = Field(ge=0, description="Issues marked as auto_fixable")
