# step2_extract_body.py
def read_email_from_file(filename):
    with open(filename, 'r') as f:
        return f.read()

def extract_body(email_content):
    lines = email_content.split('\n')
    body_lines = []
    found_blank_line = False
    
    for line in lines:
        # Headers end with a blank line
        if not found_blank_line and line.strip() == '':
            found_blank_line = True
            continue
        
        if found_blank_line:
            body_lines.append(line)
    
    return '\n'.join(body_lines).strip()

if __name__ == "__main__":
    email_content = read_email_from_file("mock_email.txt")
    body = extract_body(email_content)
    
    print("=== BODY ONLY ===")
    print(body)
    print("=================")
    print(f"Body length: {len(body)} characters")