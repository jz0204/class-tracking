from .sendgrid_service import SendGridService
import logging

class EmailSender:
    def __init__(self, email_service=None):
        self.email_service = email_service

    async def send_confirmation_email(self, to, sections):
        try:
            subject = "Course Watch Confirmation"
            body = self._create_confirmation_email_body(sections)
            
            logging.info(f"Attempting to send confirmation email to {to}")
            logging.info(f"Email subject: {subject}")
            logging.info(f"Email body: {body}")
            
            success = await self.email_service.send_email(
                to=to,
                subject=subject,
                body=body
            )
            
            if success:
                logging.info(f"Confirmation email sent successfully to {to}")
                return True
            else:
                logging.error(f"Failed to send confirmation email to {to}")
                return False
                
        except Exception as e:
            logging.error(f"Exception in send_confirmation_email: {str(e)}")
            return False

    def _create_confirmation_email_body(self, sections):
        body = "You are now watching the following sections:\n\n"
        
        for section in sections:
            body += f"CRN: {section['CRN']}\n"
            body += f"Course: {section['Subject']} {section['Course']}-{section['Section']}\n"
            body += f"Title: {section['Title']}\n"
            body += f"Instructor: {section['Instructor']}\n"
            body += f"Status: {section['Status']}\n"
            body += f"Location: {section['Location']}\n\n"
            
        body += "You will receive notifications when the status of any section changes."
        return body

    async def send_status_change_email(self, to, section, old_status, new_status):
        try:
            subject = f"Course Status Change: {section['Subject']} {section['Course']}-{section['Section']}"
            body = self._create_status_change_email_body(section, old_status, new_status)
            
            success = await self.email_service.send_email(
                to=to,
                subject=subject,
                body=body
            )
            
            if success:
                logging.info(f"Status change email sent to {to}")
                return True
            else:
                logging.error("Failed to send status change email")
                return False
                
        except Exception as e:
            logging.error(f"Failed to send status change email: {str(e)}")
            return False

    def _create_status_change_email_body(self, section, old_status, new_status):
        body = f"The status of the following section has changed from {old_status} to {new_status}:\n\n"
        body += f"CRN: {section['CRN']}\n"
        body += f"Course: {section['Subject']} {section['Course']}-{section['Section']}\n"
        body += f"Title: {section['Title']}\n"
        body += f"Instructor: {section['Instructor']}\n"
        body += f"Location: {section['Location']}\n"
        return body