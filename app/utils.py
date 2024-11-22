from pydantic import BaseModel
from typing import List, Dict, Optional
import requests
import json
import re
import aiohttp

class CourseWatch(BaseModel):
    subject: Optional[str] = None
    course_number: Optional[str] = None
    crns: Optional[List[str]] = None
    email: str
    last_status: dict = {}  # Stores the last known status of sections


# Your existing get_course_sections function goes here, but make it async
async def get_course_sections(subject: Optional[str] = None, course_number: Optional[str] = None, crns: Optional[List[str]] = None, term: str = "202511") -> List[Dict]:
    try:
        # Add timeout for the request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://howdy.tamu.edu/api/course-sections",
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                json={
                    "startRow": 0,
                    "endRow": 50,
                    "termCode": term,
                    "publicSearch": "Y",
                    **({"subject": subject, "courseNumber": str(course_number)} if subject and course_number else {})
                },
                timeout=aiohttp.ClientTimeout(total=3)
            ) as response:
                response.raise_for_status()
                courses = await response.json()
                
                # Filter courses based on search criteria
                if crns:
                    filtered_courses = [c for c in courses if c["SWV_CLASS_SEARCH_CRN"] in crns]
                elif subject and course_number:
                    filtered_courses = [
                        c for c in courses 
                        if (c["SWV_CLASS_SEARCH_SUBJECT"] == subject and 
                            c["SWV_CLASS_SEARCH_COURSE"] == str(course_number))
                    ]
                else:
                    return []

                # Use list comprehension with await
                formatted_courses = []
                for course in filtered_courses:
                    formatted = await format_course(course)
                    if formatted:
                        formatted_courses.append(formatted)
                return formatted_courses
    except Exception as e:
        print(f"Error fetching course sections: {e}")
        return []

async def format_course(course):
    try:
        instructor_info = course["SWV_CLASS_SEARCH_INSTRCTR_JSON"]
        if instructor_info:
            instructor_data = json.loads(instructor_info)
            instructor_name = instructor_data[0]["NAME"] if instructor_data else "No instructor assigned"
        else:
            instructor_name = "No instructor assigned"
            
        return {
            "CRN": course["SWV_CLASS_SEARCH_CRN"],
            "Subject": course["SWV_CLASS_SEARCH_SUBJECT"],
            "Course": course["SWV_CLASS_SEARCH_COURSE"],
            "Section": course["SWV_CLASS_SEARCH_SECTION"],
            "Title": course["SWV_CLASS_SEARCH_TITLE"],
            "Instructor": instructor_name,
            "Status": "Open" if course["STUSEAT_OPEN"] == "Y" else "Closed",
            "Location": course["SWV_CLASS_SEARCH_ATTRIBUTES"]
        }
    except Exception as e:
        print(f"Error formatting course: {e}")
        return None

async def format_status_message(sections: List[Dict]) -> str:
    message = "Current course status:\n\n"
    for section in sections:
        message += f"Course: {section['Title']}\n"
        message += f"CRN: {section['CRN']}\n"
        message += f"Subject: {section['Subject']} {section['Course']}-{section['Section']}\n"
        message += f"Instructor: {section['Instructor']}\n"
        message += f"Status: {section['Status']}\n"
        message += f"Location: {section['Location']}\n\n"
    return message