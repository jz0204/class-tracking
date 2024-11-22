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
    return {"status": "healthy"}

@app.get("/")
async def home(request: Request):
    try:
        # Increase timeout and add retry logic
        watches = await asyncio.wait_for(
            db.get_all_watches(),
            timeout=15.0
        )
        
        async def process_watch(watch):
            """Process a single watch entry"""
            try:
                if watch.get('status') == 'initializing':
                    return watch
                
                # If no course info, try to fetch it
                if not watch.get('course_info'):
                    sections = await get_course_sections(
                        subject=watch.get('subject'),
                        course_number=watch.get('course_number'),
                        crns=watch.get('crns')
                    )
                    if sections:
                        await db.update_course_info(watch['_id'], sections)
                        watch['course_info'] = sections
                return watch
            except Exception as e:
                logging.error(f"Error processing watch {watch.get('_id')}: {e}")
                return watch

        # Process watches in batches of 5
        processed_watches = []
        batch_size = 5
        
        for i in range(0, len(watches), batch_size):
            batch = watches[i:i + batch_size]
            tasks = [process_watch(watch) for watch in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out any exceptions and add successful results
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
        
        # Add watch with timeout
        watch_id = await asyncio.wait_for(
            db.add_watch_minimal(subject, course_number, crn_list, email),
            timeout=5.0
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
        
    except asyncio.TimeoutError:
        logging.error("Timeout adding watch")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again."
        )
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
