from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from typing import List
from .database import Database
from .course_checker import CourseChecker
from .email_sender import EmailSender

app = FastAPI()

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize components
db = Database()
email_sender = EmailSender()
course_checker = CourseChecker(db, email_sender)

@app.get("/")
async def home_page(request: Request):
    watches = await db.get_all_watches()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "watches": watches}
    )

@app.post("/watch")
async def add_watch(
    background_tasks: BackgroundTasks,
    subject: str = Form(...),
    course_number: str = Form(...),
    crns: str = Form(...),
    email: str = Form(...)
):
    crn_list = [crn.strip() for crn in crns.split(",")]
    await db.add_watch(subject, course_number, crn_list, email)
    background_tasks.add_task(course_checker.check_courses)
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete/{watch_id}")
async def delete_watch(watch_id: str):
    await db.delete_watch(watch_id)
    return RedirectResponse(url="/", status_code=303)
