"""Document processor using Google Cloud Document AI"""

from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions
from typing import List, Dict
import os
from datetime import datetime
from .config import settings
from .schemas import DocumentBundle


class DocumentProcessor:
    """Extract structured text from PDFs using Document AI"""
    
    def __init__(self):
        """Initialize Document AI client"""
        opts = ClientOptions(
            api_endpoint=f"{settings.document_ai_location}-documentai.googleapis.com"
        )
        self.client = documentai.DocumentProcessorServiceClient(client_options=opts)
        
        # Construct processor name
        self.processor_name = self.client.processor_path(
            settings.gcp_project_id,
            settings.document_ai_location,
            settings.document_ai_processor_id
        )
    
    def process_pdf(self, pdf_path: str) -> DocumentBundle:
        """
        Process PDF using Document AI and return structured document bundle
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            DocumentBundle with extracted text and layout metadata
        """
        # Read PDF file
        with open(pdf_path, 'rb') as file:
            pdf_content = file.read()
        
        # Create Document AI request
        raw_document = documentai.RawDocument(
            content=pdf_content,
            mime_type='application/pdf'
        )
        
        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document
        )
        
        # Process document
        result = self.client.process_document(request=request)
        document = result.document
        
        # Debug: Print document info
        print(f"Document AI response - Total pages in document: {len(document.pages) if document.pages else 0}")
        print(f"Document AI response - Text length: {len(document.text) if document.text else 0}")
        
        # Extract page-wise text and layout
        pages = self._extract_pages(document)
        
        # Create document bundle
        doc_id = os.path.splitext(os.path.basename(pdf_path))[0]
        bundle = DocumentBundle(
            doc_id=doc_id,
            file_path=pdf_path,
            total_pages=len(pages),
            pages=pages,
            processing_timestamp=datetime.utcnow().isoformat()
        )
        
        return bundle
    
    def _extract_pages(self, document: documentai.Document) -> List[Dict]:
        """
        Extract text and layout metadata from Layout Parser response
        
        Layout Parser returns data in documentLayout.blocks with nested structure:
        - Heading blocks can contain nested paragraph blocks
        - Table blocks contain cells with paragraph blocks
        
        We need to recursively process ALL blocks to capture full content.
        
        Returns list of page dictionaries with:
        - page_num: 1-indexed page number
        - text: Full text content
        - paragraphs: List of paragraph texts (including content from all block types)
        - layout_metadata: Block types and structure
        """
        pages_dict = {}
        
        # Extract blocks from documentLayout
        if hasattr(document, 'document_layout') and document.document_layout:
            layout = document.document_layout
            
            if hasattr(layout, 'blocks') and layout.blocks:
                # Process all blocks recursively
                self._process_blocks_recursively(layout.blocks, pages_dict)
        
        # Convert dict to sorted list
        pages = [pages_dict[page_num] for page_num in sorted(pages_dict.keys())]
        
        # If no pages extracted, fall back to legacy pages array (for OCR processor)
        if not pages and hasattr(document, 'pages') and document.pages:
            pages = self._extract_pages_legacy(document)
        
        return pages
    
    def _process_blocks_recursively(self, blocks, pages_dict: Dict, parent_type: str = None):
        """
        Recursively process blocks and nested sub-blocks
        
        Args:
            blocks: List of blocks to process
            pages_dict: Dictionary to accumulate page data
            parent_type: Type of parent block (for context)
        """
        for block in blocks:
            # Get page number
            page_num = 1  # default
            if hasattr(block, 'page_span') and block.page_span:
                page_num = block.page_span.page_start if hasattr(block.page_span, 'page_start') else 1
            
            # Initialize page if not exists
            if page_num not in pages_dict:
                pages_dict[page_num] = {
                    'page_num': page_num,
                    'text': '',
                    'paragraphs': [],
                    'layout_metadata': {
                        'block_types': [],
                        'has_tables': False
                    }
                }
            
            # Process text blocks
            if hasattr(block, 'text_block') and block.text_block:
                text_block = block.text_block
                text = text_block.text if hasattr(text_block, 'text') else ''
                block_type = text_block.type if hasattr(text_block, 'type') else 'unknown'
                
                # Add text to page (if not empty)
                if text.strip():
                    pages_dict[page_num]['text'] += text + '\n'
                    
                    # Add to paragraphs array for ALL text content
                    # (headings, paragraphs, everything with actual text)
                    pages_dict[page_num]['paragraphs'].append(text)
                    
                    # Track block type
                    pages_dict[page_num]['layout_metadata']['block_types'].append(block_type)
                
                # Process nested blocks if present
                if hasattr(text_block, 'blocks') and text_block.blocks:
                    self._process_blocks_recursively(text_block.blocks, pages_dict, block_type)
            
            # Process table blocks
            elif hasattr(block, 'table_block') and block.table_block:
                pages_dict[page_num]['layout_metadata']['has_tables'] = True
                
                # Extract text from table cells
                table_block = block.table_block
                if hasattr(table_block, 'body_rows') and table_block.body_rows:
                    for row in table_block.body_rows:
                        if hasattr(row, 'cells') and row.cells:
                            for cell in row.cells:
                                if hasattr(cell, 'blocks') and cell.blocks:
                                    # Recursively process blocks in table cells
                                    self._process_blocks_recursively(cell.blocks, pages_dict, 'table')
    
    def _extract_pages_legacy(self, document: documentai.Document) -> List[Dict]:
        """
        Legacy extraction for OCR Processor (uses document.pages)
        """
        pages = []
        
        for page_num, page in enumerate(document.pages, start=1):
            # Extract page text
            page_text = self._get_page_text(document.text, page)
            
            # Extract paragraphs
            paragraphs = []
            if page.paragraphs:
                for para in page.paragraphs:
                    para_text = self._get_layout_text(document.text, para.layout)
                    if para_text:
                        paragraphs.append(para_text)
            
            # Build layout metadata
            layout_metadata = {
                'has_tables': bool(page.tables),
                'paragraph_count': len(page.paragraphs) if page.paragraphs else 0,
                'line_count': len(page.lines) if page.lines else 0
            }
            
            pages.append({
                'page_num': page_num,
                'text': page_text,
                'paragraphs': paragraphs,
                'layout_metadata': layout_metadata
            })
        
        return pages
    
    def _get_page_text(self, full_text: str, page: documentai.Document.Page) -> str:
        """Extract text for a specific page"""
        if not page.layout or not page.layout.text_anchor:
            return ""
        
        return self._get_layout_text(full_text, page.layout)
    
    def _get_layout_text(self, full_text: str, layout: documentai.Document.Page.Layout) -> str:
        """Extract text from layout text anchor"""
        if not layout.text_anchor or not layout.text_anchor.text_segments:
            return ""
        
        text = ""
        for segment in layout.text_anchor.text_segments:
            start_idx = int(segment.start_index) if segment.start_index else 0
            end_idx = int(segment.end_index) if segment.end_index else len(full_text)
            text += full_text[start_idx:end_idx]
        
        return text.strip()
    
    def format_for_llm(self, bundle: DocumentBundle) -> str:
        """
        Format document bundle into text for LLM classification
        
        Returns formatted string with page markers
        """
        formatted_text = f"Document ID: {bundle.doc_id}\n"
        formatted_text += f"Total Pages: {bundle.total_pages}\n\n"
        
        for page in bundle.pages:
            formatted_text += f"--- PAGE {page['page_num']} ---\n"
            formatted_text += page['text']
            formatted_text += "\n\n"
        
        return formatted_text
