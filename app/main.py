from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.background import BackgroundTasks
from typing import Optional
import logging
from pathlib import Path
from .database import Database
from .email_sender import EmailSender
from .course_checker import CourseChecker

app = FastAPI()

# Mount static directory
static_path = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

templates = Jinja2Templates(directory="templates")
db = Database()

@app.get("/")
async def home(request: Request):
    try:
        watches = await db.get_all_watches()
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "watches": watches}
        )
    except Exception as e:
        logging.error(f"Error in home route: {e}")
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "watches": [],
                "error": "Unable to load watches. Please try again."
            }
        )

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
        
        watch_id = await db.add_watch_minimal(subject, course_number, crn_list, email)
        
        background_tasks.add_task(
            initialize_watch,
            watch_id,
            db,
            email_sender,
            get_course_sections
        )
        
        return RedirectResponse(url="/", status_code=303)
        
    except Exception as e:
        logging.error(f"Error in add_watch: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to process request. Please try again."
        )
