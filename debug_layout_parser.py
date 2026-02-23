"""Debug Layout Parser processor to understand why it returns 0 pages"""

from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions
import json

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
print(f"Processor path: {processor_name}\n")

# Read PDF
with open(PDF_PATH, 'rb') as f:
    pdf_content = f.read()

print(f"PDF size: {len(pdf_content)} bytes\n")

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
print("Processing document with Layout Parser...\n")
try:
    result = client.process_document(request=request)
    document = result.document
    
    print("=" * 60)
    print("DOCUMENT AI RESPONSE ANALYSIS")
    print("=" * 60)
    
    # Basic info
    print(f"\n📊 Basic Info:")
    print(f"  document.text length: {len(document.text) if document.text else 0}")
    print(f"  document.pages count: {len(document.pages) if document.pages else 0}")
    print(f"  document.entities count: {len(document.entities) if document.entities else 0}")
    
    # Check if there's text
    if document.text:
        print(f"\n✅ Document has text!")
        print(f"  First 500 chars:\n  {document.text[:500]}\n")
    else:
        print(f"\n❌ No text in document.text field")
    
    # Check pages in detail
    if document.pages:
        print(f"\n📄 Page Details:")
        for idx, page in enumerate(document.pages):
            print(f"\n  Page {idx + 1}:")
            print(f"    - Blocks: {len(page.blocks) if page.blocks else 0}")
            print(f"    - Paragraphs: {len(page.paragraphs) if page.paragraphs else 0}")
            print(f"    - Lines: {len(page.lines) if page.lines else 0}")
            print(f"    - Tokens: {len(page.tokens) if page.tokens else 0}")
            print(f"    - Has layout: {bool(page.layout)}")
            
            if page.layout and page.layout.text_anchor:
                print(f"    - Text anchors: {len(page.layout.text_anchor.text_segments)}")
                
            # Try to extract text from first page
            if idx == 0 and page.layout and page.layout.text_anchor and page.layout.text_anchor.text_segments:
                for segment in page.layout.text_anchor.text_segments:
                    start = int(segment.start_index) if segment.start_index else 0
                    end = int(segment.end_index) if segment.end_index else len(document.text)
                    seg_text = document.text[start:end] if document.text else ""
                    print(f"    - Segment text ({start}:{end}): {seg_text[:100]}")
                    break
    else:
        print(f"\n❌ No pages in document.pages")
    
    # Check raw response structure
    print(f"\n🔍 Document Structure:")
    print(f"  Has mimeType: {bool(document.mime_type)}")
    print(f"  MimeType: {document.mime_type if document.mime_type else 'None'}")
    print(f"  Has uri: {bool(document.uri)}")
    
    # Save full response for inspection
    print(f"\n💾 Saving full response to debug_response.json...")
    # Can't directly serialize, so just save key info
    with open('debug_response.json', 'w') as f:
        json.dump({
            'text_length': len(document.text) if document.text else 0,
            'pages_count': len(document.pages) if document.pages else 0,
            'mime_type': document.mime_type,
            'sample_text': document.text[:500] if document.text else None
        }, f, indent=2)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
