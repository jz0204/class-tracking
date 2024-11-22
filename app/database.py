import os
import certifi
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
from bson.objectid import ObjectId
from pymongo.errors import ServerSelectionTimeoutError
import backoff
from typing import Optional

class DatabaseConnection:
    _instance = None
    _initialized = False
    
    @classmethod
    async def get_instance(cls):
        if not cls._instance or not cls._initialized:
            cls._instance = await cls._initialize()
        return cls._instance
    
    @classmethod
    async def _initialize(cls):
        try:
            load_dotenv(find_dotenv())
            connection_string = os.getenv('MONGODB_URI')
            if not connection_string:
                raise ValueError("MONGODB_URI environment variable is not set")
            
            client = AsyncIOMotorClient(
                connection_string,
                tlsCAFile=certifi.where(),
                tls=True,
                maxPoolSize=1,  # Minimal pool size for serverless
                minPoolSize=0,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                retryWrites=True,
                retryReads=True
            )
            
            # Test connection
            await client.admin.command('ping')
            cls._initialized = True
            return client.class_tracking
            
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")
            raise

class Database:
    def __init__(self):
        self._db = None
    
    async def _get_db(self):
        if not self._db:
            self._db = await DatabaseConnection.get_instance()
        return self._db
    
    @backoff.on_exception(
        backoff.expo,
        (ServerSelectionTimeoutError, TimeoutError),
        max_tries=3,
        max_time=10
    )
    async def get_all_watches(self):
        try:
            db = await self._get_db()
            cursor = db.watches.find({})
            return await cursor.to_list(length=50)  # Limit results
        except Exception as e:
            logging.error(f"Failed to get watches: {str(e)}")
            return []

    @backoff.on_exception(
        backoff.expo,
        (ServerSelectionTimeoutError, TimeoutError),
        max_tries=3,
        max_time=10
    )
    async def add_watch_minimal(self, subject, course_number, crns, email):
        try:
            db = await self._get_db()
            document = {
                "subject": subject,
                "course_number": course_number,
                "crns": crns,
                "email": email,
                "course_info": [],
                "status": "initializing",
                "created_at": datetime.utcnow()
            }
            result = await db.watches.insert_one(document)
            return str(result.inserted_id)
        except Exception as e:
            logging.error(f"Failed to add watch: {e}")
            raise

    async def get_watch_by_id(self, watch_id):
        try:
            db = await self._get_db()
            if isinstance(watch_id, str):
                watch_id = ObjectId(watch_id)
            return await db.watches.find_one({"_id": watch_id})
        except Exception as e:
            logging.error(f"Failed to get watch by ID: {e}")
            return None

    async def update_course_info(self, watch_id, course_info):
        try:
            db = await self._get_db()
            if isinstance(watch_id, str):
                watch_id = ObjectId(watch_id)
            
            result = await db.watches.update_one(
                {"_id": watch_id},
                {
                    "$set": {
                        "course_info": course_info,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"Failed to update course info: {e}")
            return False
