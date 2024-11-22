from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from typing import List, Optional
import os
from pathlib import Path
from .database import Database
from .course_checker import CourseChecker
from .email_sender import EmailSender
from .utils import get_course_sections, format_status_message
from dotenv import load_dotenv
from .sendgrid_service import SendGridService

load_dotenv()
app = FastAPI()


# Configure templates directory
if os.getenv('VERCEL'):
    # Vercel deployment
    templates = Jinja2Templates(directory="templates")
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    # Local development
    templates = Jinja2Templates(directory="templates")
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize services with error handling
try:
    db = Database()
    sendgrid_service = SendGridService()
    email_sender = EmailSender(email_service=sendgrid_service)
    course_checker = CourseChecker(db, email_sender)
    print("All services initialized successfully")
except Exception as e:
    print(f"Failed to initialize services: {e}")
    raise

@app.get("/api/healthcheck")
async def healthcheck():
    return {"status": "healthy"}

@app.get("/")
async def home(request: Request):
    try:
        watches = await db.get_all_watches()
        # Update course info for each watch
        for watch in watches:
            sections = await get_course_sections(watch.get('subject'), watch.get('course_number'), watch['crns'])
            watch['course_info'] = sections
            print(f"Updated course info for watch: {watch['_id']}")
            print(f"Course info: {sections}")
        return templates.TemplateResponse("index.html", {"request": request, "watches": watches})
    except Exception as e:
        print(f"Error in home route: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/watch")
async def add_watch(
    background_tasks: BackgroundTasks,
    subject: Optional[str] = Form(None),
    course_number: Optional[str] = Form(None),
    crns: str = Form(...),
    email: str = Form(...)
):
    try:
        print(f"Received watch request - Subject: {subject}, Course: {course_number}, CRNs: {crns}, Email: {email}")
        crn_list = [crn.strip() for crn in crns.split(",") if crn.strip()]
        
        # Get initial status
        sections = await get_course_sections(
            subject=subject,
            course_number=course_number,
            crns=crn_list if not (subject and course_number) else None
        )
        print(f"Fetched sections: {sections}")
        
        if sections:
            # Changed from send_watch_confirmation to send_confirmation_email
            email_sent = await email_sender.send_confirmation_email(
                to=email,
                sections=sections
            )
            
            if email_sent:
                print(f"Confirmation email sent to {email}")
            else:
                print("Failed to send confirmation email")
            
            # Add watch to database with course info
            watch_id = await db.add_watch(subject, course_number, crn_list, email)
            print(f"Added watch with ID: {watch_id}")
            
            background_tasks.add_task(course_checker.check_courses)
            return RedirectResponse(url="/", status_code=303)
        else:
            raise HTTPException(
                status_code=404, 
                detail="No courses found with the provided information"
            )
    except Exception as e:
        print(f"Error in add_watch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete/{watch_id}")
async def delete_watch(watch_id: str):
    try:
        success = await db.delete_watch(watch_id)
        if not success:
            raise HTTPException(status_code=404, detail="Watch not found")
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        print(f"Error in delete_watch: {e}")
        raise HTTPException(status_code=500, detail=str(e))
