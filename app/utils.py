# app/utils.py
import io
import logging
import os
import json
from PyPDF2 import PdfReader
from docx import Document
from fastapi import UploadFile, HTTPException
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, SafetySetting, HarmCategory

# --- Constants ---
SUPPORTED_DOC_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logging.warning(
        "GEMINI_API_KEY environment variable not set. JSON generation will fail."
    )
    # raise ValueError("GEMINI_API_KEY environment variable is required.") # Or handle gracefully
else:
    # Configure the Gemini client library
    genai.configure(api_key=GEMINI_API_KEY)


# --- Text Extraction Functions ---


def extract_text_from_pdf(file_stream: io.BytesIO) -> str:
    """Extracts text content from a PDF file stream."""
    try:
        reader = PdfReader(file_stream)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"  # Add newline between pages
        logging.info(f"Successfully extracted text from PDF. Length: {len(text)}")
        return text.strip()
    except Exception as e:
        logging.error(f"Error reading PDF file: {e}")
        return ""  # Return empty string on failure


def extract_text_from_docx(file_stream: io.BytesIO) -> str:
    """Extracts text content from a DOCX file stream."""
    try:
        document = Document(file_stream)
        text = ""
        for para in document.paragraphs:
            text += para.text + "\n"
        logging.info(f"Successfully extracted text from DOCX. Length: {len(text)}")
        return text.strip()
    except Exception as e:
        logging.error(f"Error reading DOCX file: {e}")
        return ""  # Return empty string on failure


async def extract_text_from_upload(file: UploadFile) -> str:
    """Extracts text from an uploaded file (PDF or DOCX)."""
    if file.content_type not in SUPPORTED_DOC_TYPES:
        logging.warning(
            f"Unsupported file type uploaded: {file.content_type}. Filename: {file.filename}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Please upload PDF or DOCX.",
        )

    try:
        content = await file.read()
        file_stream = io.BytesIO(content)
        # It's good practice to reset file pointer if the stream might be read again,
        # though for BytesIO it might not be strictly necessary here.
        file_stream.seek(0)

        text = ""
        if file.content_type == "application/pdf":
            logging.info(f"Processing uploaded PDF: {file.filename}")
            text = extract_text_from_pdf(file_stream)
        elif (
            file.content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            logging.info(f"Processing uploaded DOCX: {file.filename}")
            text = extract_text_from_docx(file_stream)

        file_stream.close()  # Close the stream

        if not text:
            logging.warning(
                f"Could not extract text from file: {file.filename} (Type: {file.content_type})"
            )
            # Return empty string, let the caller decide if it's an error

        return text

    except HTTPException as e:
        raise e  # Re-raise HTTP exceptions
    except Exception as e:
        logging.error(f"Failed to read or process uploaded file {file.filename}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error processing file {file.filename}: {str(e)}"
        )


async def parse_json_upload(file: UploadFile) -> dict:
    """Parses an uploaded JSON file."""
    if file.content_type != "application/json":
        logging.warning(
            f"Incorrect content type for JSON upload: {file.content_type}. Filename: {file.filename}"
        )
        raise HTTPException(
            status_code=400,
            detail="JSON file must have content type 'application/json'",
        )

    try:
        content = await file.read()
        json_data = json.loads(content)
        logging.info(f"Successfully parsed uploaded JSON file: {file.filename}")
        return json_data
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON file uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="Invalid JSON file format")
    except Exception as e:
        logging.error(f"Failed to read or parse JSON file {file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing JSON file {file.filename}: {str(e)}",
        )


# --- Gemini API Interaction ---


async def generate_json_with_gemini(
    input_text: str, examples: list, model_name: str = "gemini-1.5-flash"
) -> dict:
    """
    Generates JSON using the Gemini API based on input text and examples.

    Args:
        input_text: The new text input for which to generate JSON.
        examples: A list of TrainingPair objects to use as few-shot examples.
        model_name: The specific Gemini model to use.

    Returns:
        A dictionary containing the generated JSON or an error message.
    """
    if not GEMINI_API_KEY:
        logging.error("Gemini API key is not configured. Cannot generate JSON.")
        return {"error": "Gemini API key not configured on server."}

    try:
        # --- 1. Construct the Prompt ---
        prompt_parts = [
            "You are an assistant that analyzes text documents and generates structured JSON output based on the content.",
            "Follow the format of the examples provided.",
            "Given the following text input, generate the corresponding JSON object.",
            "Output ONLY the JSON object itself, without any introductory text, explanation, or markdown formatting like ```json.",
            "\n--- Examples ---",
        ]

        if not examples:
            prompt_parts.append(
                "\nNo examples provided. Analyze the input text and generate a suitable JSON structure."
            )
        else:
            for i, example in enumerate(examples):
                # Ensure example.json_data is loaded if stored as string
                json_example_str = json.dumps(example.json_data, indent=2)
                prompt_parts.append(f"\nExample {i+1}:")
                prompt_parts.append("Input Text:")
                prompt_parts.append(f"```\n{example.text_content}\n```")
                prompt_parts.append("Output JSON:")
                prompt_parts.append(f"```json\n{json_example_str}\n```")

        prompt_parts.append("\n--- New Input Text ---")
        prompt_parts.append(f"```\n{input_text}\n```")
        prompt_parts.append("\n--- Generated JSON Output ---")
        # The model should place its JSON output after this line

        full_prompt = "\n".join(prompt_parts)
        logging.info(
            f"Constructed prompt for Gemini (length: {len(full_prompt)} chars). Examples used: {len(examples)}"
        )
        # For debugging, you might want to log the full prompt, but be mindful of length and sensitive data
        # logging.debug(f"Full Prompt:\n{full_prompt}")

        # --- 2. Configure Generation ---
        # Adjust these settings as needed
        generation_config = GenerationConfig(
            temperature=0.5,  # Lower temperature for more deterministic JSON output
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,  # Adjust based on expected JSON size
            response_mime_type="application/json",  # Request JSON output directly if model supports it
        )

        # Configure safety settings (optional, adjust as needed)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        # --- 3. Call the Gemini API ---
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

        logging.info(f"Sending request to Gemini model: {model_name}")
        response = await model.generate_content_async(full_prompt)  # Use async version

        # --- 4. Process the Response ---
        logging.info("Received response from Gemini.")

        # Check for safety blocks or empty response
        if not response.candidates:
            logging.warning(
                "Gemini response blocked due to safety settings or other reasons."
            )
            # Access prompt feedback if available
            feedback = (
                response.prompt_feedback
                if hasattr(response, "prompt_feedback")
                else "No feedback available"
            )
            return {"error": f"Content generation blocked. Feedback: {feedback}"}

        # Assuming the first candidate has the content
        generated_content = response.text

        # --- 5. Parse the Generated JSON ---
        try:
            # The model should ideally return only the JSON string due to the prompt
            # and response_mime_type="application/json"
            # Remove potential markdown fences if they still appear
            if generated_content.strip().startswith("```json"):
                generated_content = generated_content.strip()[7:]
            if generated_content.strip().endswith("```"):
                generated_content = generated_content.strip()[:-3]

            generated_json = json.loads(generated_content.strip())
            logging.info("Successfully parsed JSON from Gemini response.")
            return generated_json
        except json.JSONDecodeError as json_err:
            logging.error(f"Failed to parse JSON from Gemini response: {json_err}")
            logging.error(f"Raw Gemini response text:\n{generated_content}")
            return {
                "error": "Failed to parse JSON from AI response.",
                "raw_response": generated_content,
            }
        except Exception as e:
            # Catch other potential errors during response processing
            logging.error(f"Error processing Gemini response: {e}")
            return {
                "error": f"An unexpected error occurred while processing the AI response: {str(e)}",
                "raw_response": generated_content,
            }

    except Exception as e:
        # Catch errors during API call setup or execution
        logging.error(f"Error calling Gemini API: {e}")
        # You might want to check for specific API error types from the library
        return {
            "error": f"An error occurred while communicating with the AI service: {str(e)}"
        }
