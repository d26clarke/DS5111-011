import sys
import os
import json
import logging

# For Lab6a
from abc import ABC, abstractmethod

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


class LLMStrategy(ABC):
    """Abstract base class defining the contract for text enrichment strategies.

    Classes implementing this interface are responsible for parsing unstructured
    text—such as automated transcripts—and applying specific extraction, tagging,
    or classification logic to produce structured data.

    Methods:
        call_llm(raw_text): Abstract method to process text and return string.
        parse_response(raw_response): Abstract method to parse response and return dictionary.
    """

    @abstractmethod
    def call_llm(self, raw_text: str) -> str:
        """Must accept raw transcript text and return the LLM's raw text response."""

    @abstractmethod
    def parse_response(self, raw_response: str) -> dict:
        """Must accept the LLM's raw response and return a structured dict."""


class GeminiStrategy(LLMStrategy):
    """Concrete LLM strategy implementation utilizing the Google Gemini API.

    This class manages authentication with Gemini services and orchestrates the
    end-to-end pipeline of prompt construction, model execution, and response parsing.

    Attributes:
        client (genai.Client): The initialized Google GenAI client instance.

    Raises:
        EnvironmentError: If the mandatory 'GEMINI_API_KEY' environment variable
            is missing during initialization.
    """

    # ── Extraction schema shared between call_llm and parse_response ──────────
    _RESPONSE_SCHEMA = {
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

    def __init__(self):
        if not os.getenv("GEMINI_API_KEY"):
            logging.critical("GEMINI_API_KEY environment variable is missing.")
            raise EnvironmentError("Missing GEMINI_API_KEY")
        self.client = genai.Client()

    # Completed TODO 1: prompt construction + generate_content call 
    def call_llm(self, raw_text: str) -> str:
        """Construct the extraction prompt and invoke the Gemini model.

        Builds the strict JSON-extraction prompt from the supplied transcript
        snippet, calls ``client.models.generate_content`` with the shared
        response schema, and returns the model's raw text response for
        downstream parsing.

        Args:
            raw_text: The unstructured transcript snippet to be analyzed.

        Returns:
            The raw JSON string returned by the Gemini model.

        Raises:
            Exception: Propagates any API or network error to the caller so
                the pipeline's per-record error handler can emit a FAILED
                payload rather than silently dropping the record.
        """
        # Mirror the prompt that previously lived inline in main()
        prompt = f"""
        Analyze the following lecture transcript snippet. Extract all tech stack components mentioned
        (e.g., Snowflake, AWS Lambda) and any books/literature referenced.

        Transcript: "{raw_text}"
        """

        logging.info("Sending transcript to Gemini for enrichment.")

        # Mirror the generate_content call that previously lived inline in main()
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=self._RESPONSE_SCHEMA
            )
        )

        logging.info("Received response from Gemini.")
        return response.text

    # Completed TODO 2: json.loads + schema validation 
    def parse_response(self, raw_response: str) -> dict:
        """Parse the Gemini JSON response and validate its structure.

        Deserializes the raw JSON string returned by ``call_llm``, verifies
        that both required keys (``tech_stack`` and ``literature_references``)
        are present and are lists, and returns the validated enrichment dict.

        Args:
            raw_response: The raw JSON string returned by the Gemini model.

        Returns:
            A dictionary with keys ``tech_stack`` (list[str]) and
            ``literature_references`` (list[str]).

        Raises:
            json.JSONDecodeError: If the response is not valid JSON.
            ValueError: If the required keys are missing or are not lists,
                indicating the model deviated from the enforced schema.
        """
        # Mirror the json.loads call that previously lived inline in main()
        enrichment_data = json.loads(raw_response)

        # Schema validation — guard against model deviating from the enforced schema
        required_keys = {"tech_stack", "literature_references"}
        missing_keys = required_keys - enrichment_data.keys()
        if missing_keys:
            raise ValueError(
                f"Gemini response is missing required keys: {missing_keys}. "
                f"Raw response: {raw_response}"
            )

        for key in required_keys:
            if not isinstance(enrichment_data[key], list):
                raise ValueError(
                    f"Expected '{key}' to be a list, got "
                    f"{type(enrichment_data[key]).__name__}. "
                    f"Raw response: {raw_response}"
                )

        logging.info(
            "Parsed enrichment data — tech_stack: %d item(s), "
            "literature_references: %d item(s).",
            len(enrichment_data["tech_stack"]),
            len(enrichment_data["literature_references"])
        )

        return enrichment_data


def main():
    # Validate API initialization requirements
    if not os.getenv("GEMINI_API_KEY"):
        logging.critical("GEMINI_API_KEY environment variable is missing. Terminating pipeline.")
        sys.exit(1)

    # Instantiate the strategy — replaces the bare genai.Client() call
    strategy = GeminiStrategy()

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
                logging.warning(
                    f"Malformed stream entry skipped. Missing keys in payload: {line}"
                )
                continue

            # Delegate to the strategy — replaces the inline prompt + API call
            raw_response = strategy.call_llm(raw_text)

            # Delegate parsing and validation to the strategy
            enrichment_data = strategy.parse_response(raw_response)

            payload["enriched_data"] = enrichment_data
            payload["pipeline_status"] = "SUCCESS"

            # Emit the final payload to stdout with an explicit trailing newline
            sys.stdout.write(json.dumps(payload) + "\n")
            sys.stdout.flush()

        except Exception as e:
            logging.error(
                f"Failed processing record for video_id "
                f"{video_id if 'video_id' in locals() else 'UNKNOWN'}: {str(e)}"
            )

            # Error recovery fallback: emit original payload marked as FAILED
            if 'payload' in locals():
                payload["pipeline_status"] = "FAILED"
                payload["error_log"] = str(e)
                sys.stdout.write(json.dumps(payload) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    main()
