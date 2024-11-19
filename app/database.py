from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from bson import ObjectId

class Database:
    def __init__(self):
        load_dotenv()
        try:
            # Use MongoDB Atlas connection string for production
            mongodb_url = os.getenv("MONGODB_URL")
            if not mongodb_url:
                raise ValueError("MONGODB_URL environment variable not set")
            
            self.client = AsyncIOMotorClient(mongodb_url)
            self.db = self.client.course_watch
            print("Successfully connected to MongoDB")
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            raise

    async def add_watch(self, subject: Optional[str], course_number: Optional[str], crns: List[str], email: str) -> str:
        try:
            # Fetch initial course information
            from .utils import get_course_sections
            course_info = await get_course_sections(subject, course_number, crns)
            print(f"Initial course info for new watch: {course_info}")
            
            document = {
                "subject": subject,
                "course_number": course_number,
                "crns": crns,
                "email": email,
                "course_info": course_info
            }
            
            result = await self.db.watches.insert_one(document)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Failed to add watch: {e}")
            raise

    async def get_all_watches(self):
        try:
            cursor = self.db.watches.find({})
            watches = []
            async for watch in cursor:
                watch["_id"] = str(watch["_id"])
                print(f"Retrieved watch: {watch}")
                watches.append(watch)
            return watches
        except Exception as e:
            print(f"Failed to get watches: {e}")
            raise

    async def delete_watch(self, watch_id: str) -> bool:
        try:
            result = await self.db.watches.delete_one({"_id": ObjectId(watch_id)})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Failed to delete watch: {e}")
            raise

    async def update_course_info(self, watch_id: str, course_info: List[Dict]) -> bool:
        try:
            result = await self.db.watches.update_one(
                {"_id": ObjectId(watch_id)},
                {"$set": {"course_info": course_info}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Failed to update course info: {e}")
            return False

db = Database()
