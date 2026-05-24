# step6_confidence_scoring.py
import requests
import json
import os
from datetime import datetime
from openai import OpenAI

# client = OpenAI(
#     api_key=os.getenv("MISTRAL_API_KEY"),
#     base_url="https://api.x.ai/v1"
# )

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
    with open(filename, 'r') as f:
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

def llm_parse_with_confidence(body):
    """Parse order AND return confidence score"""
    
    prompt = f"""
You are an order parser for a food distribution company.

Extract order items from this email body and rate your confidence.

Email body:
{body}

Return ONLY valid JSON in this format:
{{
  "items": [
    {{"product": "bananas", "quantity": 10, "unit": "case", "notes": "no green ones"}}
  ],
  "confidence": 0.95,
  "missing_info": [],
  "ambiguous_fields": []
}}

Confidence rules (0 to 1):
- 0.95-1.00: All products, quantities, units clearly stated with standard terms
- 0.80-0.94: Minor shorthand or common variations, but still clear
- 0.65-0.79: Some ambiguity (e.g., "10 bannys" could be bananas or plantains)
- 0.50-0.64: Significant ambiguity or missing units
- <0.50: Unclear what customer wants

missing_info: List what's missing (e.g., ["quantity for potatoes", "unit for eggs"])
ambiguous_fields: List what's unclear (e.g., ["product: 'bannys'", "unit: 'cs' could be case or carton"])
"""

    try:
        response = client.chat.completions.create(
            model="mistral-small-latest",  # or "grok-2-latest"
            messages=[
                {"role": "system", "content": "You are an order parsing assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=800
        )
        
        result_text = response.choices[0].message.content
        result_text = result_text.replace("```json", "").replace("```", "").strip()
        
        parsed = json.loads(result_text)
        return parsed
    
    except Exception as e:
        print(f"LLM Error: {e}")
        return {"items": [], "confidence": 0.0, "missing_info": ["LLM error"], "ambiguous_fields": []}

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

def generate_clarification_email(original_body, missing_info, ambiguous_fields):
    """Draft an email asking customer for clarification"""
    
    prompt = f"""
Customer sent this order:
{original_body}

Missing information: {missing_info}
Ambiguous fields: {ambiguous_fields}

Write a short, professional email asking for clarification.
Be specific about what's unclear.
Keep it to 3-4 sentences.
"""
    
    try:
        response = client.chat.completions.create(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": "You write clear, professional customer service emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        return response.choices[0].message.content
    except:
        return f"Could you please clarify the following: {missing_info + ambiguous_fields}?"

if __name__ == "__main__":
    if not os.getenv("MISTRAL_API_KEY"):
        print("❌ Please set GROK_API_KEY environment variable")
        exit(1)
    
    # Test with different emails
    test_emails = [
        "mock_email.txt",  # Clear order
        "mock_email2.txt",  # More complex
        "mock_email3.txt",   # Shorthand
        "mock_email_missing.txt",
        "mock_email_ambiguous.txt",
        "mock_email_clear.txt"
    ]
    
    for email_file in test_emails:
        print(f"\n{'='*50}")
        print(f"📧 Testing: {email_file}")
        print('='*50)
        
        if not os.path.exists(email_file):
            print(f"⚠️ File {email_file} not found, skipping")
            continue
        
        email_content = read_email_from_file(email_file)
        body = extract_body(email_content)
        
        print(f"Body: {body[:100]}...")
        
        # Parse with confidence
        result = llm_parse_with_confidence(body)
        items = result.get("items", [])
        confidence = result.get("confidence", 0.0)
        missing = result.get("missing_info", [])
        ambiguous = result.get("ambiguous_fields", [])
        
        print(f"\n📊 Confidence: {confidence}")
        print(f"❓ Missing: {missing if missing else 'None'}")
        print(f"⚠️ Ambiguous: {ambiguous if ambiguous else 'None'}")
        
        # Decision logic
        if confidence >= 0.85 and items:
            print(f"✅ High confidence - sending to ERP")
            erp_result = send_to_erp(
                customer="Acme Foods",
                items=items,
                confidence=confidence,
                email_id=f"email_{datetime.now().timestamp()}"
            )
            print(f"   Order ID: {erp_result.get('order_id')}")
            
        elif confidence >= 0.60 and items:
            print(f"⚠️ Medium confidence - sending but flagging for review")
            erp_result = send_to_erp(
                customer="Acme Foods",
                items=items,
                confidence=confidence,
                email_id=f"email_{datetime.now().timestamp()}"
            )
            print(f"   Order ID: {erp_result.get('order_id')} (needs review)")
            
        else:
            print(f"❌ Low confidence - asking for clarification")
            clarification = generate_clarification_email(body, missing, ambiguous)
            print(f"\n📝 Draft clarification email:\n{'-'*40}\n{clarification}\n{'-'*40}")