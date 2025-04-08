# app/main.py
import logging
import os
import json
from fastapi import FastAPI, File, UploadFile, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# Import database functions, models, crud, and utility functions
from . import models, utils, crud
from .database import (
    SessionLocal,
    engine,
    init_db,
    get_db,
)  # Ensure init_db is called if needed

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- FastAPI App Initialization ---
app = FastAPI(title="PDF/DOCX JSON Training and Query API with Gemini")

# --- Database Initialization ---
# Ensure tables are created (idempotent operation)
try:
    # init_db() # Call the function to create tables
    # Alternatively, rely on the import side effect if database.py runs create_all
    models.Base.metadata.create_all(bind=engine)
    logging.info("Database tables checked/created successfully on startup.")
except Exception as e:
    logging.error(f"CRITICAL: Failed to initialize database on startup: {e}")
    # Consider exiting if the DB is essential and fails to initialize
    # raise SystemExit(f"Failed to initialize database: {e}")


# --- Templates and Static Files ---
# Assume templates are in 'app/templates' relative to this file
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.isdir(templates_dir):
    logging.error(f"Templates directory not found at: {templates_dir}")
    raise RuntimeError(f"Templates directory not found: {templates_dir}")
else:
    logging.info(f"Loading templates from: {templates_dir}")

templates = Jinja2Templates(directory=templates_dir)

# Optional: Mount static files directory if you have CSS/JS
# static_dir = os.path.join(os.path.dirname(__file__), "static")
# if os.path.isdir(static_dir):
#     app.mount("/static", StaticFiles(directory=static_dir), name="static")
#     logging.info(f"Serving static files from: {static_dir}")


# --- API Endpoints ---


@app.get("/", response_class=HTMLResponse, summary="Show Training Page")
async def read_root(request: Request):
    """Serves the main training page (index.html)."""
    logging.info("Serving training page (index.html)")
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/query", response_class=HTMLResponse, summary="Show Query Page")
async def read_query_page(request: Request):
    """Serves the query page (query.html)."""
    logging.info("Serving query page (query.html)")
    return templates.TemplateResponse("query.html", {"request": request})


@app.post(
    "/upload_training_data",
    summary="Upload Document and JSON for Training",
    status_code=201,
)
async def upload_training_data(
    request: Request,
    doc_file: UploadFile = File(..., description="Document file (PDF or DOCX)"),
    json_file: UploadFile = File(..., description="Corresponding JSON data file"),
    db: Session = Depends(get_db),
):
    """
    Handles the upload of a document (PDF/DOCX) and its corresponding JSON file.
    Extracts text from the document and stores the text-JSON pair in the database.
    """
    logging.info(
        f"Received training upload request. Document: {doc_file.filename}, JSON: {json_file.filename}"
    )

    # 1. Extract text from the document
    try:
        extracted_text = await utils.extract_text_from_upload(doc_file)
        # Handle case where text extraction returns empty but no error was raised
        if (
            not extracted_text and extracted_text != ""
        ):  # Check if truly empty vs. failed extraction handled by utils
            logging.warning(
                f"Text extraction yielded empty content for: {doc_file.filename}"
            )
            # Decide if this is an error or acceptable
            # return JSONResponse(status_code=400, content={"message": f"Could not extract text from document: {doc_file.filename}"})

    except HTTPException as e:
        # Pass through HTTP exceptions (e.g., unsupported file type)
        logging.error(f"HTTPException during text extraction: {e.detail}")
        raise e
    except Exception as e:
        logging.error(f"Unexpected error extracting text from {doc_file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Server error extracting text from document: {str(e)}",
        )

    # 2. Parse the JSON file
    try:
        json_data = await utils.parse_json_upload(json_file)
    except HTTPException as e:
        logging.error(f"HTTPException during JSON parsing: {e.detail}")
        raise e
    except Exception as e:
        logging.error(f"Unexpected error parsing JSON file {json_file.filename}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Server error parsing JSON file: {str(e)}"
        )

    # 3. Store the pair in the database
    try:
        crud.create_training_pair(
            db=db,
            text_content=extracted_text,
            json_data=json_data,  # Pass the parsed dictionary
            original_filename=doc_file.filename,
        )
        logging.info(f"Successfully stored training pair for: {doc_file.filename}")
        # Use status_code=201 Created
        return JSONResponse(
            status_code=201,
            content={
                "message": f"Training data from '{doc_file.filename}' and '{json_file.filename}' uploaded and stored successfully."
            },
        )
    except Exception as e:
        logging.error(
            f"Database error storing training pair for {doc_file.filename}: {e}"
        )
        # Don't expose raw DB errors to the client
        raise HTTPException(
            status_code=500, detail="Failed to store training data in database."
        )


@app.post("/process_query", summary="Process Query Document and Generate JSON")
async def process_query(
    request: Request,
    doc_file: UploadFile = File(
        ..., description="Document file (PDF or DOCX) to query"
    ),
    db: Session = Depends(get_db),
):
    """
    Handles the upload of a query document, extracts text, retrieves examples,
    calls the Gemini API to generate JSON, and returns the result.
    """
    logging.info(f"Received query request for document: {doc_file.filename}")

    # 1. Extract text from the uploaded query document
    try:
        input_text = await utils.extract_text_from_upload(doc_file)
        if not input_text and input_text != "":
            logging.warning(f"Query document {doc_file.filename} yielded no text.")
            # Return an error or specific response if no text is found
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract text from query document: {doc_file.filename}",
            )
    except HTTPException as e:
        raise e  # Re-raise client errors (4xx)
    except Exception as e:
        logging.error(
            f"Error extracting text from query document {doc_file.filename}: {e}"
        )
        raise HTTPException(
            status_code=500, detail="Server error processing query document."
        )

    # 2. Retrieve training examples from the database
    try:
        # Retrieve a limited number of recent examples (e.g., 5)
        examples = crud.get_training_examples(db=db, limit=5)
        logging.info(f"Retrieved {len(examples)} examples for the prompt.")
    except Exception as e:
        logging.error(f"Failed to retrieve training examples from database: {e}")
        # Proceed without examples, or return an error depending on requirements
        examples = []
        # raise HTTPException(status_code=500, detail="Failed to retrieve training examples.") # Option to fail hard

    # 3. Call the Gemini API utility function
    try:
        logging.info("Calling Gemini API utility function...")
        generated_json_result = await utils.generate_json_with_gemini(
            input_text=input_text,
            examples=examples,
            # Optionally pass model_name if you want to configure it per request
        )

        # Check if the result contains an error message from the utility function
        if isinstance(generated_json_result, dict) and "error" in generated_json_result:
            logging.error(f"Gemini generation failed: {generated_json_result['error']}")
            # Return a 500 error or a more specific error code if applicable
            raise HTTPException(status_code=500, detail=generated_json_result["error"])

        logging.info(
            f"Successfully received generated JSON for query: {doc_file.filename}"
        )
        # Return the successfully generated JSON
        return JSONResponse(content=generated_json_result)

    except HTTPException as e:
        # Handle HTTPExceptions raised by generate_json_with_gemini or earlier steps
        raise e
    except Exception as e:
        logging.error(
            f"Unexpected error during Gemini JSON generation for {doc_file.filename}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected server error occurred during JSON generation: {str(e)}",
        )


# --- Root endpoint for basic check ---
@app.get("/health", summary="Health Check")
async def health_check():
    """Simple health check endpoint."""
    logging.info("Health check endpoint accessed.")
    return {"status": "ok"}
