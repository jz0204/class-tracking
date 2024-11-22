from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv, find_dotenv
from bson import ObjectId
import certifi
import logging

class Database:
    def __init__(self):
        try:
            # Load environment variables with explicit path
            env_path = find_dotenv()
            print(f"Loading .env file from: {env_path}")
            load_dotenv(env_path)
            
            connection_string = os.getenv('MONGODB_URI')
            print(f"Connection string found: {'Yes' if connection_string else 'No'}")
            
            if not connection_string:
                raise ValueError("MONGODB_URI environment variable is not set")
            
            # Configure client based on connection string
            if 'mongodb+srv://' in connection_string:
                # Atlas connection (with SSL)
                self.client = AsyncIOMotorClient(
                    connection_string,
                    tlsCAFile=certifi.where(),
                    serverSelectionTimeoutMS=5000
                )
            else:
                # Local connection (without SSL)
                self.client = AsyncIOMotorClient(
                    connection_string,
                    serverSelectionTimeoutMS=5000
                )
                
            self.db = self.client.class_tracking
            print("Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {str(e)}")
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
