import os
import certifi
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv, find_dotenv

class Database:
    def __init__(self):
        try:
            load_dotenv(find_dotenv())
            
            connection_string = os.getenv('MONGODB_URI')
            if not connection_string:
                raise ValueError("MONGODB_URI environment variable is not set")
            
            # Parse the connection string to add required parameters
            if "?" in connection_string:
                connection_string += "&retryWrites=true"
            else:
                connection_string += "?retryWrites=true"
            
            self.client = AsyncIOMotorClient(
                connection_string,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                maxPoolSize=1,
                minPoolSize=0,
                tlsAllowInvalidCertificates=True
            )
            
            self.db = self.client.class_tracking
            print("Successfully connected to MongoDB Atlas")
            
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    async def add_watch(self, subject, course_number, crns, email):
        try:
            # Get initial course info
            from .utils import get_course_sections
            course_info = await get_course_sections(subject, course_number, crns)
            
            # Create document
            document = {
                "subject": subject,
                "course_number": course_number,
                "crns": crns,
                "email": email,
                "course_info": course_info
            }
            
            # Insert into watches collection
            result = await self.db.watches.insert_one(document)
            return str(result.inserted_id)
            
        except Exception as e:
            logging.error(f"Failed to add watch: {e}")
            raise

    async def get_all_watches(self):
        try:
            cursor = self.db.watches.find({})
            watches = []
            async for watch in cursor:
                watch["_id"] = str(watch["_id"])
                watches.append(watch)
            return watches
        except Exception as e:
            logging.error(f"Failed to get watches: {e}")
            raise

db = Database()
