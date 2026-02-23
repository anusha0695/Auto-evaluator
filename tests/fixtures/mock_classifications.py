"""
Mock classification data generators for testing

These generators create ClassificationOutput objects with intentional issues
for testing verification agents.
"""

from src.schemas import ClassificationOutput


def load_valid_classification_from_file(filepath: str = "output/classification_result.json") -> ClassificationOutput:
    """
    Load a real, valid classification from file.
    This is easier than manually constructing the complex nested structure.
    """
    import json
    from pathlib import Path
    
    path = Path(filepath)
    if not path.exists():
        # Fallback to sample output
        path = Path("output/sample_classification_output.json")
    
    if path.exists():
        with open(path, 'r') as f:
            data = json.load(f)
        return ClassificationOutput(**data)
    
    raise FileNotFoundError(f"No valid classification file found. Run classification on a document first.")


def create_valid_classification() -> ClassificationOutput:
    """
    Create or load a valid classification with no issues.
    Uses real output as template.
    """
    return load_valid_classification_from_file()


def create_classification_with_issue(issue_type: str) -> ClassificationOutput:
    """
    Create a classification with a specific issue injected.
    
    Args:
        issue_type: Type of issue to inject
            - 'invalid_confidence': Set confidence > 1.0
            - 'invalid_shares': Make shares not sum to 1.0
            - 'page_overlap': Create overlapping segments
            - 'missing_evidence': Remove evidence for PRIMARY type
            - 'out_of_bounds_page': Page number beyond document
    
    Returns:
        Modified ClassificationOutput with injected issue
    """
    # Load valid classification as base
    classification = load_valid_classification_from_file()
    data = classification.model_dump()
    
    # Inject specific issue
    if issue_type == 'invalid_confidence':
        # Set first segment's first composition confidence to >1.0
        data['segments'][0]['segment_composition'][0]['confidence'] = 1.5
        
    elif issue_type == 'invalid_shares':
        # Make shares not sum to 1.0
        data['segments'][0]['segment_composition'][0]['segment_share'] = 0.60
        # Other shares stay the same, sum will be off
        
    elif issue_type == 'page_overlap':
        # If only 1 segment, add another that overlaps
        if len(data['segments']) == 1:
            seg1 = data['segments'][0]
            data['number_of_segments'] = 2
            data['segments'].append({
                **seg1,
                'segment_index': 2,
                'start_page': seg1['end_page'],  # Overlap: same page
                'end_page': min(seg1['end_page'] + 2, classification.number_of_segments * 3),
                'segment_page_count': 3
            })
        else:
            # Make existing segments overlap
            data['segments'][1]['start_page'] = data['segments'][0]['end_page']
            
    elif issue_type == 'missing_evidence':
        # Clear evidence for the PRIMARY type
        for seg in data['segments']:
            seg['top_evidence'] = []
            
    elif issue_type == 'out_of_bounds_page':
        # Set page beyond document range
        data['segments'][0]['end_page'] = 999
    
    # Reconstruct with modified data
    # Note: This may fail validation if schema is strict
    try:
        return ClassificationOutput(**data)
    except Exception as e:
        # For some issues (like invalid_confidence), Pydantic will reject during construction
        # In those cases, we need to test V1 differently (with raw dicts or by modifying after construction)
        raise ValueError(f"Cannot create classification with issue '{issue_type}': {e}")


def modify_classification_dict(classification: ClassificationOutput, issue_type: str) -> dict:
    """
    Alternative approach: return dict with issue (bypasses Pydantic validation).
    Useful for testing V1's ability to catch schema violations.
    """
    data = classification.model_dump()
    
    if issue_type == 'invalid_confidence':
        data['segments'][0]['segment_composition'][0]['confidence'] = 1.5
    elif issue_type == 'negative_confidence':
        data['segments'][0]['segment_composition'][0]['confidence'] = -0.5
    elif issue_type == 'invalid_shares':
        data['segments'][0]['segment_composition'][0]['segment_share'] = 0.60
        
    return data
