from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
import logging
import asyncio

class SendGridService:
    def __init__(self):
        self.sg = None
        self.from_email = None
        self.initialize_service()

    def initialize_service(self):
        try:
            api_key = os.getenv('SENDGRID_API_KEY')
            self.from_email = os.getenv('SENDGRID_FROM_EMAIL')
            
            if not api_key:
                raise ValueError("SENDGRID_API_KEY environment variable is not set")
            if not self.from_email:
                raise ValueError("SENDGRID_FROM_EMAIL environment variable is not set")
                
            self.sg = SendGridAPIClient(api_key)
            logging.info("SendGrid service initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize SendGrid service: {str(e)}")
            raise

    async def send_email(self, to, subject, body):
        try:
            if not self.sg:
                raise ValueError("SendGrid service not initialized")

            message = Mail(
                from_email=self.from_email,
                to_emails=to,
                subject=subject,
                plain_text_content=body
            )
            
            # Run the synchronous SendGrid send operation in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.sg.send(message))
            
            if response.status_code in [200, 201, 202]:
                logging.info(f"Email sent successfully to {to}")
                return True
            else:
                logging.error(f"Failed to send email. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            logging.error(f"Failed to send email: {str(e)}")
            return False 