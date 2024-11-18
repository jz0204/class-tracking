from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
        self.db = self.client.course_tracker

    async def add_watch(self, subject: str, course_number: str, crns: List[str], email: str):
        watch = {
            "subject": subject.upper(),
            "course_number": course_number,
            "crns": crns,
            "email": email,
            "last_status": {}
        }
        await self.db.watches.insert_one(watch)

    async def get_all_watches(self):
        cursor = self.db.watches.find({})
        return await cursor.to_list(length=None)

    async def update_last_status(self, watch_id, status: Dict[str, bool]):
        await self.db.watches.update_one(
            {"_id": watch_id},
            {"$set": {"last_status": status}}
        )

    async def delete_watch(self, watch_id):
        await self.db.watches.delete_one({"_id": watch_id})

db = Database()
