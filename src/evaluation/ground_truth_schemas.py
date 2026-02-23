"""
Ground Truth and SME Review Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from src.schemas import ClassificationOutput


class GroundTruthSource(str, Enum):
    """Source of ground truth label"""
    PRIMARY_AGENT_AUTO_ACCEPT = "primary_agent_auto_accept"  # V5 AUTO_ACCEPT
    SME_CORRECTED = "sme_corrected"  # SME reviewed and corrected
    SME_VALIDATED = "sme_validated"  # SME reviewed and agreed with primary agent


class SMEReviewStatus(str, Enum):
    """Status of SME review"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class SMECorrections(BaseModel):
    """SME corrections to primary agent classification"""
    corrected_dominant_type: Optional[str] = None
    corrected_segments: Optional[List[Dict[str, Any]]] = None
    corrected_document_mixture: Optional[List[Dict[str, Any]]] = None
    correction_notes: str = Field(description="Explanation of corrections")


class SMEReview(BaseModel):
    """SME review of a classification"""
    reviewer_name: str
    review_date: datetime
    agrees_with_primary_agent: bool
    corrections: Optional[SMECorrections] = None
    review_notes: str = Field(description="Overall review comments")
    confidence_in_review: float = Field(ge=0.0, le=1.0, description="SME's confidence in their review")


class SMEPacket(BaseModel):
    """Packet of information for SME review"""
    # Document info
    doc_id: str
    pdf_filename: str
    pdf_path: str
    total_pages: int
    
    # Primary agent classification (to be validated)
    primary_agent_classification: ClassificationOutput
    
    # Verification report
    v5_decision: str  # ESCALATE_TO_SME
    total_issues: int
    issues_summary: List[Dict[str, Any]]  # Formatted issues from V1-V4
    
    # Optional: Production comparison
    production_classification: Optional[Dict[str, Any]] = None
    production_differs: Optional[bool] = None
    
    # Optional: DocumentBundle path for accessing actual PDF text
    document_bundle_path: Optional[str] = None
    
    # Review status
    review_status: SMEReviewStatus = SMEReviewStatus.PENDING
    sme_review: Optional[SMEReview] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class GroundTruthRecord(BaseModel):
    """Final ground truth record for a document"""
    # Document identification
    doc_id: str
    pdf_filename: str
    pdf_path: str
    
    # Production classification (what we're evaluating)
    production_classification: Optional[Dict[str, Any]] = None
    
    # Primary agent classification (baseline)
    primary_agent_classification: ClassificationOutput
    
    # Verification details
    v5_decision: str
    verification_report: Dict[str, Any]
    
    # SME review (if escalated)
    sme_review: Optional[SMEReview] = None
    
    # Final ground truth
    ground_truth_source: GroundTruthSource
    ground_truth_classification: ClassificationOutput = Field(
        description="Final validated classification - either primary agent or SME-corrected"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class ComparisonResult(BaseModel):
    """Result of comparing production vs ground truth"""
    doc_id: str
    
    # Classifications being compared
    production_dominant_type: str
    ground_truth_dominant_type: str
    
    # Comparison metrics
    dominant_type_match: bool
    segment_count_match: Optional[bool] = None
    
    # Per-type comparison
    per_type_agreement: Dict[str, str] = Field(
        description="For each document type, whether production got it right"
    )
    
    # Differences
    differences: List[str] = Field(
        description="List of specific differences found"
    )
    
    # Score
    overall_agreement_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall agreement score (1.0 = perfect match)"
    )
