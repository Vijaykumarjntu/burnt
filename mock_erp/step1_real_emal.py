# step1_read_email.py
def read_email_from_file(filename):
    with open(filename, 'r') as f:
        content = f.read()
    return content

if __name__ == "__main__":
    email_content = read_email_from_file("mock_email.txt")
    print("=== EMAIL CONTENT ===")
    print(email_content)
    print("=====================")
    print(f"Total characters: {len(email_content)}")