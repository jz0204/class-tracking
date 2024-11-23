import os
import certifi
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
from bson.objectid import ObjectId
from pymongo.errors import ServerSelectionTimeoutError
import backoff

class Database:
    def __init__(self):
        try:
            load_dotenv(find_dotenv())
            
            # Railway provides DATABASE_URL, but we'll fallback to MONGODB_URI
            connection_string = os.getenv('DATABASE_URL') or os.getenv('MONGODB_URI')
            if not connection_string:
                raise ValueError("No database connection string found")
            
            # Clean up the connection string if it contains invalid options
            if '?' in connection_string:
                base_uri = connection_string.split('?')[0]
                connection_string = f"{base_uri}?retryWrites=true&w=majority"
            
            self.client = AsyncIOMotorClient(
                connection_string,
                tlsCAFile=certifi.where(),
                tls=True,
                maxPoolSize=50,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                retryWrites=True,
                retryReads=True,
                appName='class-tracking'
            )
            
            self.db = self.client.class_tracking
            print("Successfully connected to MongoDB Atlas")
            
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    @backoff.on_exception(
        backoff.expo,
        ServerSelectionTimeoutError,
        max_tries=3
    )
    async def get_all_watches(self):
        try:
            cursor = self.db.watches.find({})
            return await cursor.to_list(length=None)
        except Exception as e:
            logging.error(f"Failed to get watches: {str(e)}")
            return []

    async def add_watch_minimal(self, subject, course_number, crns, email):
        """Add a new watch with minimal information"""
        try:
            document = {
                "subject": subject,
                "course_number": course_number,
                "crns": crns,
                "email": email,
                "status": "initializing",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await self.db.watches.insert_one(document)
            return result.inserted_id
            
        except Exception as e:
            logging.error(f"Failed to add watch: {str(e)}")
            raise

    async def update_watch_status(self, watch_id, status):
        """Update the status of a watch"""
        try:
            if isinstance(watch_id, str):
                watch_id = ObjectId(watch_id)
                
            result = await self.db.watches.update_one(
                {"_id": watch_id},
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
            
        except Exception as e:
            logging.error(f"Failed to update watch status: {str(e)}")
            return False

    async def get_watch_by_id(self, watch_id):
        """Get a watch by its ID"""
        try:
            if isinstance(watch_id, str):
                watch_id = ObjectId(watch_id)
                
            return await self.db.watches.find_one({"_id": watch_id})
            
        except Exception as e:
            logging.error(f"Failed to get watch: {str(e)}")
            return None

    async def update_course_info(self, watch_id, sections):
        """Update the course information for a watch"""
        try:
            if isinstance(watch_id, str):
                watch_id = ObjectId(watch_id)
                
            result = await self.db.watches.update_one(
                {"_id": watch_id},
                {
                    "$set": {
                        "course_info": sections,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
            
        except Exception as e:
            logging.error(f"Failed to update course info: {str(e)}")
            return False

    async def delete_watch(self, watch_id):
        """Delete a watch by its ID"""
        try:
            if isinstance(watch_id, str):
                watch_id = ObjectId(watch_id)
                
            result = await self.db.watches.delete_one({"_id": watch_id})
            return result.deleted_count > 0
            
        except Exception as e:
            logging.error(f"Failed to delete watch: {str(e)}")
            return False
