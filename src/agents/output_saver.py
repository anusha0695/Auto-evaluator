"""Agent Output Saver - Save individual agent outputs for debugging and analysis"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..schemas import ClassificationOutput, Issue


class AgentOutputSaver:
    """Save individual agent outputs to structured directory for debugging"""
    
    def __init__(self, doc_id: str, output_dir: Path = None):
        """
        Initialize output saver for a document
        
        Args:
            doc_id: Document identifier
            output_dir: Base output directory (defaults to output/agent_outputs)
        """
        if output_dir is None:
            output_dir = Path("output/agent_outputs")
        
        self.doc_id = doc_id
        self.output_dir = output_dir / doc_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Agent outputs will be saved to: {self.output_dir}")
    
    def save_primary_classification(self, classification: ClassificationOutput):
        """
        Save primary agent classification output
        
        Args:
            classification: Primary classifier output
        """
        path = self.output_dir / "primary_classification.json"
        
        output = {
            "doc_id": self.doc_id,
            "timestamp": datetime.utcnow().isoformat(),
            "classification": classification.model_dump(mode='json')
        }
        
        with open(path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"   ✓ Saved primary classification to {path.name}")
    
    def save_agent_output(
        self, 
        agent_name: str, 
        issues: List[Issue], 
        score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Save individual verification agent output
        
        Args:
            agent_name: Agent identifier (e.g., 'v1_schema_validation')
            issues: List of issues found by agent
            score: Optional quality/consistency score
            metadata: Optional additional metadata
        """
        output = {
            "agent": agent_name,
            "doc_id": self.doc_id,
            "timestamp": datetime.utcnow().isoformat(),
            "issues_count": len(issues),
            "issues": [issue.model_dump(mode='json') for issue in issues],
            "score": score,
            "metadata": metadata or {}
        }
        
        path = self.output_dir / f"{agent_name}.json"
        
        with open(path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"   ✓ Saved {agent_name} output ({len(issues)} issues)")
    
    def save_verification_report(self, report: Dict[str, Any]):
        """
        Save final verification report
        
        Args:
            report: Complete verification report
        """
        path = self.output_dir / "verification_report.json"
        
        output = {
            "doc_id": self.doc_id,
            "timestamp": datetime.utcnow().isoformat(),
            "report": report
        }
        
        with open(path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"   ✓ Saved verification report to {path.name}")
    
    def save_arbiter_decision(self, decision: str, reasoning: str, metadata: Optional[Dict] = None):
        """
        Save V5 arbiter decision
        
        Args:
            decision: Arbiter decision (e.g., 'APPROVE', 'ESCALATE_TO_SME')
            reasoning: Decision reasoning
            metadata: Optional additional metadata
        """
        output = {
            "agent": "v5_arbiter",
            "doc_id": self.doc_id,
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "reasoning": reasoning,
            "metadata": metadata or {}
        }
        
        path = self.output_dir / "v5_arbiter_decision.json"
        
        with open(path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"   ✓ Saved arbiter decision: {decision}")
