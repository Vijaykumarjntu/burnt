# step4_call_api.py
import requests
import re
from datetime import datetime

def hardcoded_parse(body):
    items = []
    
    case_match = re.search(r'(\d+)\s+cases?\s+of\s+(\w+)', body, re.IGNORECASE)
    if case_match:
        items.append({
            "product": case_match.group(2),
            "quantity": int(case_match.group(1)),
            "unit": "case",
            "notes": ""
        })
    
    bag_match = re.search(r'(\d+)\s+bags?\s+of\s+(\w+)', body, re.IGNORECASE)
    if bag_match:
        items.append({
            "product": bag_match.group(2),
            "quantity": int(bag_match.group(1)),
            "unit": "bag",
            "notes": ""
        })
    
    lb_match = re.search(r'(\d+)\s*lbs?\s+of\s+(\w+)', body, re.IGNORECASE)
    if lb_match:
        items.append({
            "product": lb_match.group(2),
            "quantity": float(lb_match.group(1)),
            "unit": "lb",
            "notes": ""
        })
    
    return items

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
    # Simulate email body
    body = "Need 10 cases of bananas, no green ones. Also 5 bags of ice and 20lbs of potatoes."
    
    items = hardcoded_parse(body)
    
    if items:
        result = send_to_erp(
            customer="Acme Foods",
            items=items,
            confidence=0.85,
            email_id=f"email_{datetime.now().timestamp()}"
        )
        print("=== API RESPONSE ===")
        print(result)
    else:
        print("No items found to send")