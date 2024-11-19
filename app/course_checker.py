from typing import List, Dict
import asyncio
from .database import Database
from .email_sender import EmailSender
from .utils import get_course_sections

class CourseChecker:
    def __init__(self, db: Database, email_sender: EmailSender):
        self.db = db
        self.email_sender = email_sender

    async def check_courses(self):
        try:
            print("Starting course check...")
            watches = await self.db.get_all_watches()
            
            for watch in watches:
                try:
                    current_sections = await get_course_sections(
                        subject=watch.get('subject'),
                        course_number=watch.get('course_number'),
                        crns=watch['crns']
                    )
                    
                    # Get previous status
                    previous_sections = watch.get('course_info', [])
                    
                    # Compare status
                    changes = []
                    for current in current_sections:
                        previous = next(
                            (s for s in previous_sections if s['CRN'] == current['CRN']), 
                            None
                        )
                        
                        if previous and previous['Status'] != current['Status']:
                            changes.append(current)
                    
                    # If there are changes, notify user and update database
                    if changes:
                        print(f"Status changes detected for watch {watch['_id']}")
                        await self.email_sender.send_status_update(watch['email'], changes)
                        
                        # Update the stored course info
                        await self.db.update_course_info(watch['_id'], current_sections)
                    
                except Exception as e:
                    print(f"Error checking courses for watch {watch['_id']}: {e}")
                    continue
                
            print("Course check completed")
            
        except Exception as e:
            print(f"Error in course checker: {e}")