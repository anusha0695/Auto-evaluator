"""Test Document AI processor directly"""

from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions
from pathlib import Path

# Configuration
PROJECT_ID = "medical-report-extraction"
LOCATION = "us"
PROCESSOR_ID = "81e83f6783d90bb0"  # Layout Parser
PDF_PATH = "data/input/raw_documents/doc2_1.pdf"

# Initialize client
opts = ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
client = documentai.DocumentProcessorServiceClient(client_options=opts)

# Construct processor name
processor_name = client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)
print(f"Processor path: {processor_name}")

# Read PDF
with open(PDF_PATH, 'rb') as f:
    pdf_content = f.read()

print(f"PDF size: {len(pdf_content)} bytes")

# Create request
raw_document = documentai.RawDocument(
    content=pdf_content,
    mime_type='application/pdf'
)

request = documentai.ProcessRequest(
    name=processor_name,
    raw_document=raw_document
)

# Process
print("Processing document...")
try:
    result = client.process_document(request=request)
    document = result.document
    
    print(f"\n✅ Success!")
    print(f"Total pages: {len(document.pages) if document.pages else 0}")
    print(f"Text length: {len(document.text) if document.text else 0}")
    
    if document.text:
        print(f"\nFirst 500 chars of text:\n{document.text[:500]}")
    
    if document.pages:
        print(f"\nPage 1 info:")
        page = document.pages[0]
        print(f"  Lines: {len(page.lines) if page.lines else 0}")
        print(f"  Paragraphs: {len(page.paragraphs) if page.paragraphs else 0}")
        print(f"  Blocks: {len(page.blocks) if page.blocks else 0}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
