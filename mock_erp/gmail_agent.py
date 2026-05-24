# ozai_gmail_agent.py
import os
import json
import requests
from datetime import datetime
from openai import OpenAI
from gmail_connector import GmailConnector

# Initialize Grok
# client = OpenAI(
#     api_key=os.getenv("GROK_API_KEY"),
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

def parse_with_grok(body):
    """Parse order with confidence scoring"""
    prompt = f"""
Parse this order email and return confidence score.

Email: {body}

Return ONLY valid JSON in this format:
{{
  "items": [
    {{"product": "bananas", "quantity": 10, "unit": "case", "notes": "no green ones"}}
  ],
  "confidence": 0.95,
  "missing_info": [],
  "ambiguous_fields": []
}}
"""
    try:
        response = client.chat.completions.create(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content
        result_text = result_text.replace("```json", "").replace("```", "").strip()
        return json.loads(result_text)
    
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return {"items": [], "confidence": 0.0, "missing_info": ["LLM error"], "ambiguous_fields": []}

def send_to_erp(customer, items, confidence, email_id):
    """Send order to mock ERP"""
    try:
        response = requests.post(
            "http://localhost:8000/api/orders",
            json={
                "customer": customer,
                "line_items": items,
                "confidence": confidence,
                "source_email_id": email_id
            },
            timeout=5
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def run_ozai_agent():
    """Main agent loop"""
    print("🤖 Ozai Agent Starting...")
    print("="*50)
    
    # Check ERP
    try:
        requests.get("http://localhost:8000/api/health", timeout=2)
        print("✅ ERP connected")
    except:
        print("❌ ERP not running. Start with: uvicorn mock_erp.main:app --reload --port 8000")
        return
    
    # Connect to Gmail
    gmail = GmailConnector()
    try:
        gmail.authenticate()
    except Exception as e:
        print(f"❌ Gmail auth failed: {e}")
        return
    
    # Fetch emails
    print("\n📬 Checking for unread emails...")
    emails = gmail.get_unread_emails(max_results=5)
    
    if not emails:
        print("📭 No unread emails found")
        return
    
    print(f"📨 Found {len(emails)} unread email(s)\n")
    
    # Process each email
    for email in emails:
        print(f"{'='*50}")
        print(f"From: {email['from']}")
        print(f"Subject: {email['subject']}")
        print(f"Body: {email['body'][:100]}...")
        
        # Parse with Grok
        print("\n🤖 Calling Grok LLM to parse order...")
        result = parse_with_grok(email['body'])
        items = result.get('items', [])
        confidence = result.get('confidence', 0.0)
        missing = result.get('missing_info', [])
        ambiguous = result.get('ambiguous_fields', [])
        
        print(f"\n📊 Confidence: {confidence}")
        print(f"📦 Items found: {len(items)}")
        
        if items:
            for item in items:
                print(f"   - {item.get('quantity')} {item.get('unit')} of {item.get('product')}")
        
        # Decision logic
        if confidence >= 0.85 and items:
            print("\n✅ High confidence - auto-submitting to ERP")
            erp_result = send_to_erp(
                email['from'].split('<')[-1].strip('>'), 
                items, 
                confidence, 
                email['id']
            )
            if 'order_id' in erp_result:
                print(f"   🎉 Order created: {erp_result['order_id']}")
                gmail.mark_as_processed(email['id'])
            else:
                print(f"   ❌ ERP error: {erp_result}")
                
        elif confidence >= 0.60 and items:
            print("\n⚠️ Medium confidence - submitting but needs review")
            erp_result = send_to_erp(
                email['from'].split('<')[-1].strip('>'), 
                items, 
                confidence, 
                email['id']
            )
            if 'order_id' in erp_result:
                print(f"   📦 Order created (needs review): {erp_result['order_id']}")
                gmail.mark_as_processed(email['id'])
            else:
                print(f"   ❌ ERP error: {erp_result}")
        else:
            print("\n❌ Low confidence - would ask for clarification")
            print(f"   Missing: {missing}")
            print(f"   Ambiguous: {ambiguous}")
            gmail.mark_as_processed(email['id'])
        
        print()

if __name__ == "__main__":
    if not os.getenv("MISTRAL_API_KEY"):
        print("❌ MISTRAL_API_KEY not set")
        print("Set it with: export GROK_API_KEY='your-key' (Mac/Linux)")
        print("Or: set MISTRAL_API_KEY=your-key (Windows)")
        exit(1)
    
    run_ozai_agent()