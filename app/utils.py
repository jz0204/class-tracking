from pydantic import BaseModel
from typing import List, Dict, Optional
import requests
import json
import re

class CourseWatch(BaseModel):
    subject: Optional[str] = None
    course_number: Optional[str] = None
    crns: Optional[List[str]] = None
    email: str
    last_status: dict = {}  # Stores the last known status of sections


# Your existing get_course_sections function goes here, but make it async
async def get_course_sections(subject: Optional[str] = None, course_number: Optional[str] = None, crns: Optional[List[str]] = None, term: str = "202511") -> List[Dict]:
    url = "https://howdy.tamu.edu/api/course-sections"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=UTF-8",
        "Origin": "https://howdy.tamu.edu",
        "Referer": "https://howdy.tamu.edu/uPortal/p/public-class-search-ui.ctf1/max/render.uP"
    }
    
    data = {
        "startRow": 0,
        "endRow": 50,
        "termCode": term,
        "publicSearch": "Y"
    }
    
    # Add search parameters based on search type
    if subject and course_number:
        data["subject"] = subject
        data["courseNumber"] = str(course_number)
    
    try:
        print(f"Fetching courses with data: {data}")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        courses = response.json()
        print(f"Found {len(courses)} courses in initial response")
        
        # Filter courses based on search type
        if subject and course_number:
            filtered_courses = [
                course for course in courses 
                if (course["SWV_CLASS_SEARCH_SUBJECT"] == subject and 
                    course["SWV_CLASS_SEARCH_COURSE"] == str(course_number))
            ]
        elif crns:
            filtered_courses = [
                course for course in courses 
                if course["SWV_CLASS_SEARCH_CRN"] in crns
            ]
        else:
            return []
        
        print(f"Filtered to {len(filtered_courses)} relevant courses")
        
        # Format the output
        formatted_results = []
        for course in filtered_courses:
            instructor_info = course["SWV_CLASS_SEARCH_INSTRCTR_JSON"]
            if instructor_info:
                instructor_data = json.loads(instructor_info)
                instructor_name = instructor_data[0]["NAME"] if instructor_data else "No instructor assigned"
            else:
                instructor_name = "No instructor assigned"
                
            formatted_course = {
                "CRN": course["SWV_CLASS_SEARCH_CRN"],
                "Subject": course["SWV_CLASS_SEARCH_SUBJECT"],
                "Course": course["SWV_CLASS_SEARCH_COURSE"],
                "Section": course["SWV_CLASS_SEARCH_SECTION"],
                "Title": course["SWV_CLASS_SEARCH_TITLE"],
                "Instructor": instructor_name,
                "Status": "Open" if course["STUSEAT_OPEN"] == "Y" else "Closed",
                "Location": course["SWV_CLASS_SEARCH_ATTRIBUTES"]
            }
            formatted_results.append(formatted_course)
            
        print(f"Returning {len(formatted_results)} formatted courses")
        return formatted_results
    except requests.exceptions.RequestException as e:
        print(f"Error accessing the API: {e}")
        return []

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