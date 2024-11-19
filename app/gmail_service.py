import base64
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
from pathlib import Path

class GmailService:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        self.creds = None
        self.service = None
        self.initialize_service()

    def initialize_service(self):
        """Initialize Gmail API service"""
        try:
            if os.getenv('VERCEL'):
                # Use environment variables for credentials in production
                creds_json = os.getenv('GOOGLE_CREDENTIALS')
                if not creds_json:
                    raise ValueError("GOOGLE_CREDENTIALS environment variable not set")
                
                creds_data = json.loads(creds_json)
                self.creds = Credentials.from_authorized_user_info(creds_data, self.SCOPES)
            else:
                # Local development using credentials.json
                credentials_path = Path(__file__).parent.parent / 'credentials.json'
                token_path = Path(__file__).parent.parent / 'token.pickle'

                # Check if credentials file exists
                if not credentials_path.exists():
                    raise FileNotFoundError("credentials.json not found in project root")

                # The file token.pickle stores the user's access and refresh tokens
                if token_path.exists():
                    print("Loading existing credentials from token.pickle")
                    with open(token_path, 'rb') as token:
                        self.creds = pickle.load(token)

                # If there are no (valid) credentials available, let the user log in
                if not self.creds or not self.creds.valid:
                    if self.creds and self.creds.expired and self.creds.refresh_token:
                        print("Refreshing expired credentials")
                        self.creds.refresh(Request())
                    else:
                        print("Initiating new OAuth2 flow")
                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(credentials_path),
                            self.SCOPES,
                            redirect_uri=self.REDIRECT_URI
                        )
                        self.creds = flow.run_local_server(
                            port=self.PORT,
                            access_type='offline',
                            include_granted_scopes='true'
                        )

                    # Save the credentials for the next run
                    print("Saving credentials to token.pickle")
                    with open(token_path, 'wb') as token:
                        pickle.dump(self.creds, token)

            self.service = build('gmail', 'v1', credentials=self.creds)
            print("Gmail service initialized successfully")

        except Exception as e:
            print(f"Error initializing Gmail service: {e}")
            raise

    async def send_email(self, to_email: str, subject: str, content: str):
        """Send an email using Gmail API"""
        try:
            message = EmailMessage()
            message.set_content(content)

            message["To"] = to_email
            message["From"] = "me"
            message["Subject"] = subject

            # Encode the message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": encoded_message}

            # Send the email
            send_message = (
                self.service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            print(f'Message Id: {send_message["id"]} sent to {to_email}')
            return True
        except HttpError as error:
            print(f"An error occurred while sending email: {error}")
            return False 