"""Test raw Document AI REST API directly to see response"""

import requests
import subprocess
import json
import base64

# Get access token
token = subprocess.check_output(['gcloud', 'auth', 'print-access-token']).decode().strip()

# Read PDF
with open('data/input/raw_documents/doc2_1.pdf', 'rb') as f:
    pdf_content = f.read()

# Encode PDF to base64
pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

# Prepare request
url = "https://us-documentai.googleapis.com/v1/projects/medical-report-extraction/locations/us/processors/81e83f6783d90bb0:process"

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

payload = {
    "rawDocument": {
        "content": pdf_base64,
        "mimeType": "application/pdf"
    }
}

print("Sending request to Document AI REST API...")
print(f"URL: {url}")
print(f"PDF size: {len(pdf_content)} bytes")
print(f"Base64 size: {len(pdf_base64)} chars\n")

response = requests.post(url, headers=headers, json=payload)

print(f"Response status: {response.status_code}")
print(f"Response headers: {dict(response.headers)}\n")

if response.status_code == 200:
    result = response.json()
    
    # Check document field
    if 'document' in result:
        doc = result['document']
        print(f"✅ Document field exists")
        print(f"  - text length: {len(doc.get('text', ''))}")
        print(f"  - pages: {len(doc.get('pages', []))}")
        print(f"  - mimeType: {doc.get('mimeType', 'None')}")
        
        if doc.get('text'):
            print(f"\n📝 First 300 chars of text:")
            print(f"  {doc['text'][:300]}")
        
        if doc.get('pages'):
            print(f"\n📄 First page info:")
            page = doc['pages'][0]
            print(f"  - blocks: {len(page.get('blocks', []))}")
            print(f"  - paragraphs: {len(page.get('paragraphs', []))}")
            print(f"  - lines: {len(page.get('lines', []))}")
    else:
        print(f"❌ No 'document' field in response")
        print(f"Response keys: {list(result.keys())}")
    
    # Save full response
    with open('rest_api_response.json', 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\n💾 Full response saved to rest_api_response.json")
    
else:
    print(f"❌ Error: {response.text}")
