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
            
            connection_string = os.getenv('MONGODB_URI')
            if not connection_string:
                raise ValueError("MONGODB_URI environment variable is not set")
            
            # Standard MongoDB client configuration
            self.client = AsyncIOMotorClient(
                connection_string,
                tlsCAFile=certifi.where(),
                tls=True,
                maxPoolSize=10,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
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
