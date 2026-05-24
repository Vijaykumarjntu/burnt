# step5_llm_parse.py
import requests
import json
import os
from datetime import datetime
from openai import OpenAI

# ====================== GROK CLIENT SETUP ======================
# client = OpenAI(
#     api_key=os.getenv("GROK_API_KEY"),
#     base_url="https://api.x.ai/v1"
# )

# ====================== MISTRAL CLIENT SETUP ======================
mistral_key = os.getenv("MISTRAL_API_KEY")

if not mistral_key:
    print("❌ MISTRAL_API_KEY not found!")
    print("Please set it using:")
    print('   $env:MISTRAL_API_KEY = "your-mistral-key-here"')
    exit(1)

print("✅ Mistral API Key loaded successfully!")

client = OpenAI(
    api_key=mistral_key,
    base_url="https://api.mistral.ai/v1"     # ← Changed to Mistral
)

def read_email_from_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def extract_body(email_content):
    lines = email_content.split('\n')
    body_lines = []
    found_blank_line = False
   
    for line in lines:
        if not found_blank_line and line.strip() == '':
            found_blank_line = True
            continue
        if found_blank_line:
            body_lines.append(line)
   
    return '\n'.join(body_lines).strip()

def llm_parse_order(body):
    """Use Grok to parse order - Best available model"""
   
    prompt = f"""
You are an order parser for a food distribution company.
Extract order items from this email body. Return ONLY valid JSON.

Email body:
{body}

Output format:
{{
  "items": [
    {{"product": "bananas", "quantity": 10, "unit": "case", "notes": "no green ones"}}
  ]
}}

Rules:
- Unit can be: case, bag, lb, each, box, carton
- If unit not specified, assume "case"
- Extract any special instructions in "notes"
- Convert shorthand (e.g., "10cs" = 10 cases, "5lb" = 5 lbs)
"""

    try:
        response = client.chat.completions.create(
            model="mistral-small-latest",          # Best balance for free tier right now
            messages=[
                {"role": "system", "content": "You are an order parsing assistant. Always return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=700
        )
       
        result_text = response.choices[0].message.content.strip()
        result_text = result_text.replace("```json", "").replace("```", "").strip()
       
        parsed = json.loads(result_text)
        return parsed.get("items", [])
   
    except Exception as e:
        print(f"❌ Grok API Error: {e}")
        return []

def send_to_erp(customer, items, confidence, email_id):
    url = "http://localhost:8000/api/orders"
    payload = {
        "customer": customer,
        "line_items": items,
        "confidence": confidence,
        "source_email_id": email_id
    }
   
    response = requests.post(url, json=payload)
    return response.json()

if __name__ == "__main__":
    # if not os.getenv("GROK_API_KEY"):
    #     print("❌ GROK_API_KEY not found!")
    #     print("1. Go to https://console.x.ai")
    #     print("2. Create API key")
    #     print("3. Run this command:")
    #     print("   $env:GROK_API_KEY='gsk-your-key-here'   # (Windows PowerShell)")
    #     print("   export GROK_API_KEY='gsk-your-key-here' # (Mac/Linux)")
    #     exit(1)

    # Read and parse email
    email_content = read_email_from_file("mock_email2.txt")
    body = extract_body(email_content)
   
    print("=== EMAIL BODY ===")
    print(body)
    print("\n=== PARSING WITH GROK (grok-4.1-fast) ===")
   
    items = llm_parse_order(body)
   
    if items:
        print(f"✅ Found {len(items)} items:")
        for item in items:
            print(f" - {item.get('quantity')} {item.get('unit')} of {item.get('product')}")
            if item.get('notes'):
                print(f"   📝 Note: {item['notes']}")
       
        result = send_to_erp(
            customer="Acme Foods",
            items=items,
            confidence=0.92,
            email_id=f"grok_email_{datetime.now().timestamp()}"
        )
       
        print("\n=== API RESPONSE ===")
        print(json.dumps(result, indent=2))
    else:
        print("❌ No items parsed")