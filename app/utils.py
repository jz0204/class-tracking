from pydantic import BaseModel
from typing import List, Optional
import requests
import json
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

class CourseWatch(BaseModel):
    subject: Optional[str] = None
    course_number: Optional[str] = None
    crns: Optional[List[str]] = None
    email: str
    last_status: dict = {}  # Stores the last known status of sections

async def notify_status_change(email: str, changes: List[Dict]):
    # Configure your email settings
    conf = ConnectionConfig(
        MAIL_USERNAME = "your-email@example.com",
        MAIL_PASSWORD = "your-password",
        MAIL_FROM = "your-email@example.com",
        MAIL_PORT = 587,
        MAIL_SERVER = "smtp.gmail.com",
        MAIL_TLS = True,
        MAIL_SSL = False,
        USE_CREDENTIALS = True
    )

    # Create message content
    content = "The following sections have changed status:\n\n"
    for change in changes:
        content += f"Course: {change['Subject']} {change['Course']}-{change['Section']}\n"
        content += f"New Status: {change['Open']}\n\n"

    message = MessageSchema(
        subject="Course Status Change Alert",
        recipients=[email],
        body=content,
        subtype="plain"
    )

    fm = FastMail(conf)
    await fm.send_message(message)

# Your existing get_course_sections function goes here, but make it async
async def get_course_sections(subject=None, course_number=None, crns=None, term="202511"):
    # ... (same as your original function, but with async/await) ...