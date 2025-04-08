# PDF/DOCX to JSON Generator with Gemini & FastAPI

## Overview

This project provides a web application and API to extract text from PDF and DOCX documents and generate structured JSON output using Google's Gemini API. It allows users to:

1.  **Train:** Upload document-JSON pairs (PDF/DOCX + corresponding JSON) to store as examples in an SQLite database.
2.  **Query:** Upload a new document (PDF/DOCX), extract its text, and use the stored examples along with the Gemini API to generate a relevant JSON output based on the document's content.

The entire application is containerized using Docker for easy setup and deployment.

## Features

- **Web Interface:** Simple UI for uploading training data and querying new documents.
  - Training Page (`/`)
  - Query Page (`/query`)
- **FastAPI Backend:** Robust asynchronous API handling file uploads, text extraction, database interaction, and Gemini API calls.
- **Text Extraction:** Supports text extraction from both PDF (`.pdf`) and DOCX (`.docx`) files.
- **Database Storage:** Uses SQLite to store text-JSON training pairs persistently within the container.
- **AI-Powered JSON Generation:** Leverages the Google Gemini API (specifically `gemini-1.5-flash` by default) for few-shot JSON generation based on provided examples and input text.
- **Dockerized:** Fully containerized for consistent environment and simplified deployment.

## Technology Stack

- **Backend:** Python 3.11
- **API Framework:** FastAPI
- **Web Server:** Uvicorn
- **Database:** SQLite (via SQLAlchemy)
- **AI Model:** Google Gemini API (`google-generativeai` SDK)
- **PDF Parsing:** PyPDF2
- **DOCX Parsing:** python-docx
- **Containerization:** Docker
- **Frontend:** HTML, CSS, JavaScript (Fetch API)
- **Templating:** Jinja2

## Project Structure

.├── Dockerfile # Defines the Docker image├── requirements.txt # Python dependencies└── app/ # Main application directory├── init.py├── main.py # FastAPI application, endpoints├── database.py # SQLAlchemy setup, session management├── models.py # SQLAlchemy ORM models (TrainingPair)├── crud.py # Database Create, Read operations├── utils.py # Text extraction, JSON parsing, Gemini API interaction├── templates/ # HTML templates (Jinja2)│ ├── index.html # Training page│ └── query.html # Query page└── data/ # Directory created inside container for SQLite DB└── sqlitedb.db # SQLite database file (created on run)

## Setup and Installation

**Prerequisites:**

- Docker installed and running.
- A Google Gemini API Key. Obtain one from [Google AI Studio](https://aistudio.google.com/).

**Steps:**

1.  **Clone/Download:** Get the project files onto your local machine. Ensure you have the `Dockerfile`, `requirements.txt`, and the `app` directory with all its contents.
2.  **Build the Docker Image:** Open a terminal in the project's root directory (where the `Dockerfile` is located) and run:
    ```bash
    docker build -t pdf-json-gemini-app .
    ```
3.  **Run the Docker Container:** Execute the following command, replacing `'YOUR_ACTUAL_API_KEY'` with your Gemini API key:
    ```bash
    docker run -p 8000:8000 -e GEMINI_API_KEY='YOUR_ACTUAL_API_KEY' --name pdf-json-container pdf-json-gemini-app
    ```
    - `-p 8000:8000`: Maps port 8000 on your host to port 8000 in the container.
    - `-e GEMINI_API_KEY='...'`: **Crucially**, sets the environment variable needed by the application to authenticate with the Gemini API.
    - `--name pdf-json-container`: Assigns a convenient name to the running container.
    - `pdf-json-gemini-app`: The name of the image you built.

## Usage

1.  **Access the Web UI:** Once the container is running, open your web browser and navigate to `http://localhost:8000`.
2.  **Train (Optional but Recommended):**
    - On the main page (`/`), use the form to upload a document file (PDF or DOCX) and a corresponding `.json` file that represents the desired structured output for that document.
    - Click "Upload Training Pair". Repeat this for several examples to provide context for the AI.
3.  **Query:**
    - Navigate to the Query Page (`http://localhost:8000/query`) using the link on the training page.
    - Upload a new document (PDF or DOCX) that you want to process.
    - Click "Process Document".
    - The application will extract the text, fetch recent training examples from the database, send them along with the new text to the Gemini API, and display the generated JSON output (or an error message).

## API Endpoints

- `GET /`: Serves the HTML training page.
- `GET /query`: Serves the HTML query page.
- `POST /upload_training_data`: Accepts `doc_file` (PDF/DOCX) and `json_file` (JSON) uploads, extracts text, and stores the pair in the database.
- `POST /process_query`: Accepts `doc_file` (PDF/DOCX) upload, extracts text, retrieves examples, calls Gemini API, and returns the generated JSON.
- `GET /health`: Simple health check endpoint. Returns `{"status": "ok"}`.

## Configuration

- **`GEMINI_API_KEY`**: This environment variable **must** be set when running the Docker container. It holds your API key for authenticating with the Google Gemini service.

## Notes & Limitations

- The quality of the generated JSON heavily depends on the quality and quantity of the training examples provided and the complexity of the documents.
- Prompt engineering within `app/utils.py` (`generate_json_with_gemini` function) might need tuning for specific use cases.
- The web UI is basic and intended for demonstration purposes.
- Error handling covers common cases, but edge cases might exist.
- Relies on external Google Gemini API availability and quotas.
- SQLite database is stored within the container. If the container is removed without using Docker volumes, the training data will be lost. For persistent storage across container runs, consider mounting a volume to `/app/data`.
