# gmail_connector.py
import os
import pickle
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailConnector:
    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        
    def authenticate(self):
        """Authenticate and create Gmail service"""
        creds = None
        
        # Load existing token if available
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"credentials.json not found. Download from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('gmail', 'v1', credentials=creds)
        print("✅ Gmail authenticated successfully")
        return self.service
    
    def get_unread_emails(self, max_results=5):
        """Fetch unread emails from inbox"""
        if not self.service:
            self.authenticate()
        
        results = self.service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            q='is:unread',
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        emails = []
        
        for msg in messages:
            msg_data = self.service.users().messages().get(
                userId='me', 
                id=msg['id'], 
                format='full'
            ).execute()
            
            # Extract email body
            body = self._extract_body(msg_data)
            
            # Extract subject and sender
            subject = None
            sender = None
            for header in msg_data['payload'].get('headers', []):
                if header['name'] == 'Subject':
                    subject = header['value']
                elif header['name'] == 'From':
                    sender = header['value']
            
            emails.append({
                'id': msg['id'],
                'subject': subject,
                'from': sender,
                'body': body,
                'received_at': msg_data.get('internalDate')
            })
        
        return emails
    
    def _extract_body(self, msg_data):
        """Extract plain text body from email"""
        body = ""
        
        # Check for parts
        if 'parts' in msg_data['payload']:
            for part in msg_data['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8')
        elif 'body' in msg_data['payload']:
            data = msg_data['payload']['body'].get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body.strip()
    
    def mark_as_read(self, email_id):
        """Mark email as read"""
        if not self.service:
            self.authenticate()
        
        self.service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
    
    def mark_as_processed(self, email_id):
        """Mark email as processed (add label)"""
        if not self.service:
            self.authenticate()
        
        # Create label if it doesn't exist
        try:
            self.service.users().labels().create(
                userId='me',
                body={'name': 'PROCESSED', 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
            ).execute()
        except:
            pass  # Label already exists
        
        self.service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['PROCESSED'], 'removeLabelIds': ['UNREAD']}
        ).execute()
    
    def send_email(self, to, subject, body):
        """Send an email"""
        from email.mime.text import MIMEText
        
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        self.service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()


# Test the connector
if __name__ == "__main__":
    print("🔐 Testing Gmail Connector...")
    gmail = GmailConnector()
    
    try:
        gmail.authenticate()
        print("📬 Fetching unread emails...")
        emails = gmail.get_unread_emails(max_results=3)
        
        if not emails:
            print("📭 No unread emails found")
        else:
            print(f"📨 Found {len(emails)} unread email(s)\n")
            for i, email in enumerate(emails, 1):
                print(f"{'='*50}")
                print(f"Email #{i}")
                print(f"From: {email['from']}")
                print(f"Subject: {email['subject']}")
                print(f"Body preview: {email['body'][:150]}...")
                print('='*50)
        
    except Exception as e:
        print(f"❌ Error: {e}")     