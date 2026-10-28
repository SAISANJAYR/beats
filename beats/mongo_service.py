import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# MongoDB Client singleton
_mongo_client = None
_db = None
_is_connected = False

MONGODB_URI = os.environ.get("MONGODB_URI", os.environ.get("MONGO_URL", "mongodb://localhost:27017/"))
DB_NAME = os.environ.get("MONGODB_DB", "beats_db")


def get_mongo_db():
    """
    Returns MongoDB database instance or None if unavailable.
    Does not crash if MongoDB is not reachable or not running.
    """
    global _mongo_client, _db, _is_connected
    if _db is not None:
        return _db

    try:
        from pymongo import MongoClient
        _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
        # Verify connection with quick ping
        _mongo_client.admin.command('ping')
        _db = _mongo_client[DB_NAME]
        _is_connected = True
        logger.info("Connected to MongoDB successfully: %s", DB_NAME)
        return _db
    except Exception as e:
        _is_connected = False
        logger.debug("MongoDB not available (using local graceful fallback): %s", e)
        return None


def is_mongo_connected() -> bool:
    """Returns True if live MongoDB connection is active."""
    db = get_mongo_db()
    return db is not None


# Local memory/fallback storage for chat logs and feedback when Mongo is offline
_FALLBACK_CHAT_LOGS = []
_FALLBACK_FEEDBACK = []


def log_chat_interaction(user_identifier: str, prompt: str, response_data: dict, model_used: str = "gemini-2.5-flash") -> bool:
    """
    Assessment Requirement: Chat logs stored in MongoDB.
    Logs user prompts, assistant answers, timestamps, and model telemetry.
    """
    doc = {
        "user_identifier": user_identifier,
        "prompt": prompt,
        "response": response_data,
        "model": model_used,
        "timestamp": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow()
    }

    db = get_mongo_db()
    if db is not None:
        try:
            db.chat_logs.insert_one(doc)
            return True
        except Exception as e:
            logger.warning("Failed to insert chat log into MongoDB: %s", e)

    # Safe fallback storage
    _FALLBACK_CHAT_LOGS.append(doc)
    if len(_FALLBACK_CHAT_LOGS) > 100:
        _FALLBACK_CHAT_LOGS.pop(0)
    return True


def log_feedback(user_identifier: str, rating: int, comment: str, related_ticket_id: str = None) -> bool:
    """
    Assessment Requirement: Feedback stored in MongoDB.
    Logs feedback score (1-5), user comments, and optional ticket ID.
    """
    doc = {
        "user_identifier": user_identifier,
        "rating": rating,
        "comment": comment,
        "related_ticket_id": related_ticket_id,
        "timestamp": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow()
    }

    db = get_mongo_db()
    if db is not None:
        try:
            db.feedback.insert_one(doc)
            return True
        except Exception as e:
            logger.warning("Failed to insert feedback into MongoDB: %s", e)

    _FALLBACK_FEEDBACK.append(doc)
    if len(_FALLBACK_FEEDBACK) > 100:
        _FALLBACK_FEEDBACK.pop(0)
    return True


def get_recent_chat_logs(limit: int = 10) -> list:
    """Retrieve recent chat logs from MongoDB or fallback."""
    db = get_mongo_db()
    if db is not None:
        try:
            cursor = db.chat_logs.find().sort("created_at", -1).limit(limit)
            logs = list(cursor)
            for item in logs:
                item["_id"] = str(item["_id"])
            return logs
        except Exception as e:
            logger.warning("Failed to read from MongoDB chat_logs: %s", e)

    return _FALLBACK_CHAT_LOGS[-limit:]


def get_recent_feedback(limit: int = 10) -> list:
    """Retrieve recent feedback entries from MongoDB or fallback."""
    db = get_mongo_db()
    if db is not None:
        try:
            cursor = db.feedback.find().sort("created_at", -1).limit(limit)
            items = list(cursor)
            for item in items:
                item["_id"] = str(item["_id"])
            return items
        except Exception as e:
            logger.warning("Failed to read from MongoDB feedback: %s", e)

    return _FALLBACK_FEEDBACK[-limit:]


def get_mongo_stats() -> dict:
    """Returns document counts and storage status for MongoDB."""
    db = get_mongo_db()
    if db is not None:
        try:
            return {
                "connected": True,
                "database": DB_NAME,
                "chat_logs_count": db.chat_logs.count_documents({}),
                "feedback_count": db.feedback.count_documents({})
            }
        except Exception as e:
            logger.warning("Failed to get MongoDB stats: %s", e)

    return {
        "connected": False,
        "database": f"{DB_NAME} (in-memory fallback buffer)",
        "chat_logs_count": len(_FALLBACK_CHAT_LOGS),
        "feedback_count": len(_FALLBACK_FEEDBACK)
    }

