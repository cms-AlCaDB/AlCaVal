import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pymongo.collection import Collection


DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 27017))
DB_NAME = 'relval'


try:
    # Create the client instance. This object manages a connection pool.
    mongo_client = MongoClient(
        DB_HOST,
        DB_PORT,
        username=os.getenv('DATABASE_USER', None),
        password=os.getenv('DATABASE_PASSWORD', None),
        authSource="admin",
        authMechanism="SCRAM-SHA-256",
    )

except ConnectionFailure as e:
    sys.exit("Database connection failed. Exiting.")

def get_collection(collection_name: str) -> Collection:
    """
    Returns a handle to a database.
    """
    db = mongo_client[DB_NAME]
    return db[collection_name]
