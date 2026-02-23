"""
Pytest fixtures for verification agent testing
"""

import pytest
from pathlib import Path
from typing import Optional
from src.schemas import ClassificationOutput, DocumentBundle


@pytest.fixture
def sample_doc_bundle():
    """Create a simple document bundle for testing"""
    from datetime import datetime
    return DocumentBundle(
        doc_id="test-doc-123",
        pdf_filename="test_doc.pdf",
        file_path="/tmp/test_doc.pdf",
        total_pages=5,
        processing_timestamp=datetime.now().isoformat(),
        pages=[
            {"page_number": i+1, "text": f"Page {i+1} content for testing..."}
            for i in range(5)
        ]
    )



@pytest.fixture
def clean_classification():
    """Valid classification with no issues"""
    from tests.fixtures.mock_classifications import create_valid_classification
    return create_valid_classification()


@pytest.fixture
def classification_invalid_confidence():
    """Classification with confidence > 1.0 (V1 should catch)"""
    from tests.fixtures.mock_classifications import create_classification_with_issue
    return create_classification_with_issue('invalid_confidence')


@pytest.fixture
def classification_share_sum_error():
    """Classification with share sums != 1.0 (V2 should catch)"""
    from tests.fixtures.mock_classifications import create_classification_with_issue
    return create_classification_with_issue('invalid_shares')


@pytest.fixture
def classification_page_overlap():
    """Classification with overlapping page ranges (V2 BLOCKER)"""
    from tests.fixtures.mock_classifications import create_classification_with_issue
    return create_classification_with_issue('page_overlap')


@pytest.fixture
def classification_missing_evidence():
    """Classification with no evidence for PRIMARY type (V1/V4 should catch)"""
    from tests.fixtures.mock_classifications import create_classification_with_issue
    return create_classification_with_issue('missing_evidence')
