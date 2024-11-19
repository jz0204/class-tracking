from .gmail_service import GmailService

class EmailSender:
    def __init__(self):
        try:
            self.gmail_service = GmailService()
            print("Email configuration loaded successfully")
        except Exception as e:
            print(f"Failed to initialize email configuration: {e}")
            raise

    async def send_watch_confirmation(self, email: str, sections: list):
        try:
            subject = "Course Watch Confirmation - Initial Status"
            message_content = "Thank you for using TAMU Course Watch!\n\n"
            message_content += "You have started watching the following courses:\n\n"
            
            for section in sections:
                message_content += f"Course: {section['Title']}\n"
                message_content += f"CRN: {section['CRN']}\n"
                message_content += f"Subject: {section['Subject']} {section['Course']}-{section['Section']}\n"
                message_content += f"Instructor: {section['Instructor']}\n"
                message_content += f"Current Status: {section['Status']}\n"
                message_content += f"Location: {section['Location']}\n"
                message_content += "-" * 50 + "\n\n"
            
            message_content += "You will receive an email notification when the status of any of these courses changes.\n"
            message_content += "To stop watching these courses, visit the course watch website.\n\n"
            message_content += "Best regards,\nTAMU Course Watch"

            success = await self.gmail_service.send_email(
                to_email=email,
                subject=subject,
                content=message_content
            )
            
            if success:
                print(f"Watch confirmation email sent to {email}")
            return success
        except Exception as e:
            print(f"Failed to send watch confirmation email: {e}")
            return False

    async def send_status_update(self, email: str, changes: list):
        try:
            subject = "Course Status Change Alert"
            message_content = "Course Status Update Alert!\n\n"
            message_content += "The following courses have changed status:\n\n"
            
            for change in changes:
                message_content += f"Course: {change['Title']}\n"
                message_content += f"CRN: {change['CRN']}\n"
                message_content += f"Subject: {change['Subject']} {change['Course']}-{change['Section']}\n"
                message_content += f"New Status: {change['Status']}\n"
                message_content += "-" * 50 + "\n\n"
            
            message_content += "Visit the course watch website to manage your watches.\n\n"
            message_content += "Best regards,\nTAMU Course Watch"

            success = await self.gmail_service.send_email(
                to_email=email,
                subject=subject,
                content=message_content
            )
            
            if success:
                print(f"Status update email sent to {email}")
            return success
        except Exception as e:
            print(f"Failed to send status update email: {e}")
            return False