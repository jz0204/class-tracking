import os
import certifi
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
from bson.objectid import ObjectId
from pymongo.errors import ServerSelectionTimeoutError
import backoff  # Add to requirements.txt
import ssl
import asyncio

class Database:
    def __init__(self):
        try:
            load_dotenv(find_dotenv())
            
            connection_string = os.getenv('MONGODB_URI')
            if not connection_string:
                raise ValueError("MONGODB_URI environment variable is not set")
            
            self.client = AsyncIOMotorClient(
                connection_string,
                tlsCAFile=certifi.where(),
                tls=True,
                tlsInsecure=True,
                maxPoolSize=5,
                minPoolSize=0,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                waitQueueTimeoutMS=10000,
                retryWrites=True,
                retryReads=True,
                appName='class-tracking'
            )
            
            self.db = self.client.class_tracking
            
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    async def initialize(self):
        """Initialize database connection"""
        try:
            await self.client.admin.command('ping')
            print("Successfully connected to MongoDB Atlas")
            return True
        except Exception as e:
            logging.error(f"Connection test failed: {str(e)}")
            return False

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
                "course_info": course_info,
                "created_at": datetime.utcnow()
            }
            
            # Insert into watches collection
            result = await self.db.watches.insert_one(document)
            return str(result.inserted_id)
            
        except Exception as e:
            logging.error(f"Failed to add watch: {e}")
            raise

    @backoff.on_exception(
        backoff.expo,
        (ServerSelectionTimeoutError, TimeoutError, ssl.SSLError),
        max_tries=3,
        max_time=20,
        jitter=backoff.full_jitter,
        giveup=lambda e: isinstance(e, ssl.SSLError) and "alert internal error" not in str(e)
    )
    async def get_all_watches(self):
        try:
            cursor = self.db.watches.find({})
            return await cursor.to_list(length=100)  # Limit to 100 watches per query
        except Exception as e:
            logging.error(f"Failed to get watches: {str(e)}")
            return []

    async def update_course_info(self, watch_id, course_info):
        try:
            # Convert string ID to ObjectId if needed
            if isinstance(watch_id, str):
                watch_id = ObjectId(watch_id)
                
            result = await self.db.watches.update_one(
                {"_id": watch_id},
                {
                    "$set": {
                        "course_info": course_info,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count == 0:
                logging.warning(f"No watch found with ID {watch_id}")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Failed to update course info for watch {watch_id}: {e}")
            return False

    async def delete_watch(self, watch_id):
        try:
            if isinstance(watch_id, str):
                watch_id = ObjectId(watch_id)
                
            result = await self.db.watches.delete_one({"_id": watch_id})
            return result.deleted_count > 0
            
        except Exception as e:
            logging.error(f"Failed to delete watch {watch_id}: {e}")
            return False

    async def test_connection(self):
        try:
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            logging.error(f"Connection test failed: {str(e)}")
            return False

    @backoff.on_exception(
        backoff.expo,
        (ServerSelectionTimeoutError, TimeoutError),
        max_tries=5,
        max_time=30,
        jitter=backoff.full_jitter
    )
    async def add_watch_minimal(self, subject, course_number, crns, email):
        try:
            document = {
                "subject": subject,
                "course_number": course_number,
                "crns": crns,
                "email": email,
                "course_info": [],
                "status": "initializing",
                "created_at": datetime.utcnow()
            }
            
            result = await self.db.watches.insert_one(document)
            return str(result.inserted_id)
            
        except Exception as e:
            logging.error(f"Failed to add watch: {e}")
            raise

    async def get_watch_by_id(self, watch_id):
        try:
            if isinstance(watch_id, str):
                watch_id = ObjectId(watch_id)
            return await self.db.watches.find_one({"_id": watch_id})
        except Exception as e:
            logging.error(f"Failed to get watch by ID: {e}")
            return None

    async def update_watch_status(self, watch_id, status):
        try:
            if isinstance(watch_id, str):
                watch_id = ObjectId(watch_id)
                
            await self.db.watches.update_one(
                {"_id": watch_id},
                {"$set": {"status": status}}
            )
            return True
        except Exception as e:
            logging.error(f"Failed to update watch status: {e}")
            return False

db = Database()
