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
import asyncio
import nest_asyncio
from .background_tasks import initialize_watch
import logging
from datetime import datetime

load_dotenv()
app = FastAPI()

# Configure templates directory
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

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
    try:
        # Test database connection
        await db.client.admin.command('ping')
        
        # Test SendGrid connection
        if not sendgrid_service.sg:
            raise ValueError("SendGrid not initialized")
            
        # All checks passed
        return {
            "status": "healthy",
            "database": "connected",
            "email_service": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logging.error(f"Healthcheck failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable"
        )

@app.get("/")
async def home(request: Request):
    try:
        # Reduce timeout and add more retries
        for attempt in range(3):  # Try 3 times
            try:
                watches = await asyncio.wait_for(
                    db.get_all_watches(),
                    timeout=5.0  # Reduced from 15.0
                )
                break  # If successful, break the loop
            except asyncio.TimeoutError:
                if attempt == 2:  # Last attempt
                    raise
                continue
        
        async def process_watch(watch):
            if watch.get('status') == 'initializing':
                return watch
            
            if not watch.get('course_info'):
                try:
                    sections = await asyncio.wait_for(
                        get_course_sections(
                            subject=watch.get('subject'),
                            course_number=watch.get('course_number'),
                            crns=watch.get('crns')
                        ),
                        timeout=5.0
                    )
                    if sections:
                        await db.update_course_info(watch['_id'], sections)
                        watch['course_info'] = sections
                except asyncio.TimeoutError:
                    logging.warning(f"Timeout fetching course info for watch {watch.get('_id')}")
            return watch

        # Process watches with smaller batch size
        processed_watches = []
        batch_size = 3  # Reduced from 5
        
        for i in range(0, len(watches), batch_size):
            batch = watches[i:i + batch_size]
            tasks = [process_watch(watch) for watch in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if not isinstance(result, Exception):
                    processed_watches.append(result)

        return templates.TemplateResponse(
            "index.html",
            {"request": request, "watches": processed_watches}
        )
        
    except asyncio.TimeoutError:
        logging.error("Database operation timed out")
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "watches": [],
                "error": "Service temporarily unavailable. Please try again."
            }
        )
    except Exception as e:
        logging.error(f"Error in home route: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/watch")
async def add_watch(
    background_tasks: BackgroundTasks,
    subject: Optional[str] = Form(None),
    course_number: Optional[str] = Form(None),
    crns: Optional[str] = Form(None),
    email: str = Form(...)
):
    try:
        if not crns and not (subject and course_number):
            raise HTTPException(
                status_code=400,
                detail="Must provide either CRNs or both Subject and Course Number"
            )

        crn_list = [crn.strip() for crn in crns.split(",")] if crns else []
        
        # Increased timeout and added retry logic
        try:
            watch_id = await db.add_watch_minimal(subject, course_number, crn_list, email)
        except Exception as e:
            logging.error(f"Database operation failed: {e}")
            raise HTTPException(
                status_code=503,
                detail="Unable to process request. Please try again."
            )
        
        # Queue initialization in background
        background_tasks.add_task(
            initialize_watch,
            watch_id,
            db,
            email_sender,
            get_course_sections
        )
        
        return RedirectResponse(url="/", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in add_watch: {e}")
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
