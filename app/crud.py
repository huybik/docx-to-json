# app/crud.py
import logging
from sqlalchemy.orm import Session
from . import models  # Assuming models.py defines TrainingPair


def create_training_pair(
    db: Session, text_content: str, json_data: dict, original_filename: str = None
):
    """
    Creates and saves a new TrainingPair record in the database.

    Args:
        db: The database session.
        text_content: The extracted text from the document.
        json_data: The corresponding JSON data (as a dictionary).
        original_filename: Optional filename for reference.

    Returns:
        The created TrainingPair object.
    """
    try:
        db_pair = models.TrainingPair(
            text_content=text_content,
            json_data=json_data,  # SQLAlchemy handles dict -> JSON
            original_filename=original_filename,
        )
        db.add(db_pair)
        db.commit()
        db.refresh(db_pair)
        logging.info(f"Successfully created training pair with ID: {db_pair.id}")
        return db_pair
    except Exception as e:
        db.rollback()  # Rollback in case of error
        logging.error(f"Error creating training pair in DB: {e}")
        raise  # Re-raise the exception to be handled by the caller


def get_training_examples(db: Session, limit: int = 5):
    """
    Retrieves a specified number of recent training examples from the database.

    Args:
        db: The database session.
        limit: The maximum number of examples to retrieve.

    Returns:
        A list of TrainingPair objects.
    """
    try:
        examples = (
            db.query(models.TrainingPair)
            .order_by(models.TrainingPair.id.desc())
            .limit(limit)
            .all()
        )
        logging.info(
            f"Retrieved {len(examples)} training examples from DB (limit: {limit})."
        )
        return examples
    except Exception as e:
        logging.error(f"Error retrieving training examples from DB: {e}")
        return []  # Return empty list on error


def get_all_training_pairs(db: Session):
    """
    Retrieves all training pairs from the database.
    Use with caution if the database might become large.

    Args:
        db: The database session.

    Returns:
        A list of all TrainingPair objects.
    """
    try:
        pairs = db.query(models.TrainingPair).order_by(models.TrainingPair.id).all()
        logging.info(f"Retrieved all {len(pairs)} training pairs from DB.")
        return pairs
    except Exception as e:
        logging.error(f"Error retrieving all training pairs from DB: {e}")
        return []
