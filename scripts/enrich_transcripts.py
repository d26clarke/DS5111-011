'''
DS5111 LAB04 and LAB05
Derrick Clarke (thq3hn)

'''
import sys
import os
import json
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load local environment configurations (.env)
load_dotenv()

# Configure internal pipeline logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("pipeline_enrichment.log"), logging.StreamHandler(sys.stderr)]
)

def main():
    # Validate API initialization requirements
    if not os.getenv("GEMINI_API_KEY"):
        logging.critical("GEMINI_API_KEY environment variable is missing. Terminating pipeline.")
        sys.exit(1)

    # Initialize the Google GenAI client
    client = genai.Client()

    # Process streaming IDs line-by-line from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            # Unpack the incoming stream JSON record
            payload = json.loads(line)
            video_id = payload.get("video_id")
            raw_text = payload.get("raw_text")

            if not video_id or not raw_text:
                logging.warning(f"Malformed stream entry skipped. Missing keys in payload: {line}")
                continue

            # Define the strict processing prompt for unstructured text mining
            prompt = f"""
            Analyze the following lecture transcript snippet. Extract all tech stack components mentioned
            (e.g., Snowflake, AWS Lambda) and any books/literature referenced.

            Transcript: "{raw_text}"
            """

            # Enforce a strict JSON extraction schema to guarantee structure
            # This ensures your validate_schema.py step won't break on unpredictable text strings.
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "tech_stack": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"},
                                "description": "Software, databases, cloud tools, or libraries mentioned."
                            },
                            "literature_references": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"},
                                "description": "Books, textbooks, papers, or specific authors cited."
                            }
                        },
                        "required": ["tech_stack", "literature_references"]
                    }
                )
            )

            # Parse Gemini's structured output and append it to our pipeline's object
            enrichment_data = json.loads(response.text)

            payload["enriched_data"] = enrichment_data
            payload["pipeline_status"] = "SUCCESS"

            # Display the final payload to stdout with an explicit trailing newline
            sys.stdout.write(json.dumps(payload) + "\n")
            sys.stdout.flush()

        except Exception as e:
            logging.error(f"Failed processing record for video_id {video_id if 'video_id' in locals() else 'UNKNOWN'}: {str(e)}")

            # Error Recovery fallback: emit original payload marked as FAILED to prevent pipeline stalls
            if 'payload' in locals():
                payload["pipeline_status"] = "FAILED"
                payload["error_log"] = str(e)
                sys.stdout.write(json.dumps(payload) + "\n")
                sys.stdout.flush()

if __name__ == "__main__":
    main()

