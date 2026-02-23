"""
Production classifier result - simple schema for evaluation
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class ProductionClassification(BaseModel):
    """Simple schema for production prompt output"""
    document_type: str = Field(description="Document type(s) - comma-separated if multiple")
    confidence: float = Field(description="Confidence score 0.0-1.0")
    reasoning: str = Field(description="Classification reasoning")
    starting_page_num: int = Field(description="Starting page (1-indexed)")


class ProductionResult(BaseModel):
    """Result from production classifier"""
    classifications: List[ProductionClassification]
    vendor: Optional[str] = None
    number_of_doctype: int
    
    @property
    def dominant_type(self) -> str:
        """Get the dominant document type (first classification's type)"""
        if not self.classifications:
            return "Other"
        
        # Get first document type, handle comma-separated
        doc_types = self.classifications[0].document_type.split(",")
        return doc_types[0].strip()
    
    @property
    def all_types(self) -> List[str]:
        """Get all document types mentioned across all classifications"""
        types = set()
        for classif in self.classifications:
            for doc_type in classif.document_type.split(","):
                types.add(doc_type.strip())
        return sorted(list(types))
