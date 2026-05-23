#!/usr/bin/env python3
"""
One-time migration script for BrokerOS.
Assigns all cases with no assigned_broker_id to the first admin user.

Usage:
    MONGO_URL=<your_mongo_url> DB_NAME=brokeros python scripts/migrate_assign_cases.py

Safe to run multiple times — idempotent.
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")

    if not mongo_url or not db_name:
        print("ERROR: MONGO_URL and DB_NAME environment variables must be set.")
        sys.exit(1)

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    # Find the first admin user
    admin_user = await db.users.find_one({"role": "admin"})
    if not admin_user:
        print("ERROR: No admin user found in the database.")
        sys.exit(1)

    from bson import ObjectId
    admin_id = str(admin_user["_id"])
    admin_email = admin_user.get("email", "<unknown>")

    # Update all cases where assigned_broker_id is null, missing, or empty string
    result = await db.cases.update_many(
        {"$or": [
            {"assigned_broker_id": None},
            {"assigned_broker_id": {"$exists": False}},
            {"assigned_broker_id": ""}
        ]},
        {"$set": {"assigned_broker_id": admin_id}}
    )

    updated = result.modified_count
    if updated == 0:
        print("No unassigned cases found — nothing to do")
    else:
        print(f"Updated {updated} cases → assigned to admin user [{admin_email}]")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
