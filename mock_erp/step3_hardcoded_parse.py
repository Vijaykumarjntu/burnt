# step3_hardcoded_parse.py
import re

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

def hardcoded_parse(body):
    # Simple pattern matching
    items = []
    
    # Look for "X cases of Y" pattern
    case_match = re.search(r'(\d+)\s+cases?\s+of\s+(\w+)', body, re.IGNORECASE)
    if case_match:
        items.append({
            "product": case_match.group(2),
            "quantity": int(case_match.group(1)),
            "unit": "case",
            "notes": ""
        })
    
    # Look for "X bags of Y"
    bag_match = re.search(r'(\d+)\s+bags?\s+of\s+(\w+)', body, re.IGNORECASE)
    if bag_match:
        items.append({
            "product": bag_match.group(2),
            "quantity": int(bag_match.group(1)),
            "unit": "bag",
            "notes": ""
        })
    
    # Look for "X lbs of Y"
    lb_match = re.search(r'(\d+)\s*lbs?\s+of\s+(\w+)', body, re.IGNORECASE)
    if lb_match:
        items.append({
            "product": lb_match.group(2),
            "quantity": float(lb_match.group(1)),
            "unit": "lb",
            "notes": ""
        })
    
    return items

if __name__ == "__main__":
    email_content = read_email_from_file("mock_email.txt")
    body = extract_body(email_content)
    items = hardcoded_parse(body)
    
    print("=== PARSED ITEMS ===")
    for item in items:
        print(f"Product: {item['product']}, Qty: {item['quantity']} {item['unit']}")
    print("====================")
    print(f"Total items found: {len(items)}")