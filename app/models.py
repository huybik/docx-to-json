# app/models.py
from sqlalchemy import Column, Integer, String, Text, JSON
from .database import Base  # Import Base from the database module


class TrainingPair(Base):
    """
    SQLAlchemy model representing a training pair stored in the database.
    It includes the extracted text from a document and its corresponding JSON data.
    """

    __tablename__ = "training_pairs"

    id = Column(Integer, primary_key=True, index=True)
    # Store the extracted text content from the document
    text_content = Column(Text, nullable=False)
    # Store the corresponding JSON data as a JSON type (SQLite handles this)
    # Ensure the JSON data is stored as a string if the DB doesn't natively support JSON
    json_data = Column(JSON, nullable=False)
    # Optional: Store the original filename for reference
    original_filename = Column(String, nullable=True)
