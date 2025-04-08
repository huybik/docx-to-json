# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

# Define the path for the SQLite database file within the container
DATABASE_DIR = "/app/data"  # Using a subdirectory within /app
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_DIR}/sqlitedb.db"

# Create the directory if it doesn't exist
os.makedirs(DATABASE_DIR, exist_ok=True)
logging.info(f"Database directory: {DATABASE_DIR}")
logging.info(f"Database URL: {SQLALCHEMY_DATABASE_URL}")


# Create the SQLAlchemy engine
# connect_args is needed for SQLite to handle multi-threading correctly with FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a SessionLocal class - instances of this class will be actual database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class - our ORM models will inherit from this class
Base = declarative_base()


# Dependency to get DB session
def get_db():
    """
    Dependency function that provides a database session per request.
    Ensures the session is always closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initializes the database by creating all tables defined in models.
    Should be called once on application startup.
    """
    logging.info("Initializing database and creating tables...")
    try:
        # This creates tables based on models imported elsewhere that inherit from Base
        Base.metadata.create_all(bind=engine)
        logging.info("Database tables created successfully (if they didn't exist).")
    except Exception as e:
        logging.error(f"Error creating database tables: {e}")
        raise
