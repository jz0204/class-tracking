import logging
from datetime import datetime
from typing import Optional, List

async def initialize_watch(watch_id: str, db, email_sender, get_course_sections):
    """Initialize a new course watch by fetching initial data and sending confirmation email"""
    try:
        # Get watch details
        watch = await db.get_watch_by_id(watch_id)
        if not watch:
            logging.error(f"Watch {watch_id} not found")
            return
        
        # Fetch initial course data
        sections = await get_course_sections(
            subject=watch.get('subject'),
            course_number=watch.get('course_number'),
            crns=watch.get('crns')
        )
        
        if sections:
            # Update watch with course info
            await db.update_course_info(watch_id, sections)
            
            # Send confirmation email
            await email_sender.send_confirmation_email(watch['email'], sections)
            
            # Update status to active
            await db.update_watch_status(watch_id, "active")
        else:
            logging.error(f"No sections found for watch {watch_id}")
            await db.update_watch_status(watch_id, "failed")
            
    except Exception as e:
        logging.error(f"Error initializing watch {watch_id}: {e}")
        # Update watch status to failed
        await db.update_watch_status(watch_id, "failed") 