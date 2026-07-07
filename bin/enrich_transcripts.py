import sys
import os
import json
import logging
import argparse

# For Lab6b
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


# Abstract interface contract

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


# Concrete strategy: Google Gemini

class GeminiStrategy(LLMStrategy):
    """Concrete LLM strategy implementation utilizing the Google Gemini API.

    Attributes:
        client (genai.Client): The initialized Google GenAI client instance.

    Raises:
        EnvironmentError: If the mandatory 'GEMINI_API_KEY' environment variable
            is missing during initialization.
    """

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

    def call_llm(self, raw_text: str) -> str:
        """Construct the extraction prompt and invoke the Gemini model.

        Args:
            raw_text: The unstructured transcript snippet to be analyzed.

        Returns:
            The raw JSON string returned by the Gemini model.
        """
        prompt = f"""
        Analyze the following lecture transcript snippet. Extract all tech stack components mentioned
        (e.g., Snowflake, AWS Lambda) and any books/literature referenced.

        Transcript: "{raw_text}"
        """

        logging.info("Sending transcript to Gemini for enrichment.")

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

    def parse_response(self, raw_response: str) -> dict:
        """Parse the Gemini JSON response and validate its structure.

        Args:
            raw_response: The raw JSON string returned by the Gemini model.

        Returns:
            A validated dictionary with keys 'tech_stack' and 'literature_references'.

        Raises:
            json.JSONDecodeError: If the response is not valid JSON.
            ValueError: If required keys are missing or are not lists.
        """
        enrichment_data = json.loads(raw_response)

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


# Pipeline engine

class TranscriptEnricher:
    """Pipeline engine that processes a JSONL stream using a pluggable LLM strategy.

    This class is intentionally strategy-agnostic — it references only the
    ``LLMStrategy`` abstract interface and never imports or instantiates a
    concrete implementation directly. The concrete strategy is injected at
    construction time by the orchestrator.

    Attributes:
        strategy (LLMStrategy): The injected enrichment strategy.
    """

    def __init__(self, strategy: LLMStrategy):
        self.strategy = strategy

    def run_stream(self):
        """Read newline-delimited JSON records from stdin, enrich each one, and
        write the augmented payload to stdout.

        Each input record must contain:
            - ``video_id`` (str): Unique identifier for the video.
            - ``raw_text`` (str): Unstructured transcript text to enrich.

        Each output record adds:
            - ``enriched_data`` (dict): Structured extraction result from the LLM.
            - ``pipeline_status`` (str): ``"SUCCESS"`` or ``"FAILED"``.
            - ``error_log`` (str): Present only on ``"FAILED"`` records.
        """
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            # Declare payload here so the except block can reference it safely
            payload = None
            video_id = "UNKNOWN"

            try:
                # Unpack the incoming stream JSON record
                payload = json.loads(line)
                video_id = payload.get("video_id", "UNKNOWN")
                raw_text = payload.get("raw_text")

                if not video_id or not raw_text:
                    logging.warning(
                        "Malformed stream entry skipped. "
                        "Missing 'video_id' or 'raw_text' in payload: %s", line
                    )
                    continue

                # Delegate to the abstract interface — no concrete type referenced here
                raw_response = self.strategy.call_llm(raw_text)
                enrichment_data = self.strategy.parse_response(raw_response)

                # Merge structured result into the original payload
                payload["enriched_data"] = enrichment_data
                payload["pipeline_status"] = "SUCCESS"

                # Emit the enriched payload to stdout
                sys.stdout.write(json.dumps(payload) + "\n")
                sys.stdout.flush()

            except Exception as e:
                logging.error(
                    "Failed processing record for video_id %s: %s", video_id, str(e)
                )

                # FAILED-payload fallback: emit the original payload marked as FAILED
                # so downstream consumers are never silently starved of a record.
                if payload is not None:
                    payload["pipeline_status"] = "FAILED"
                    payload["error_log"] = str(e)
                    sys.stdout.write(json.dumps(payload) + "\n")
                    sys.stdout.flush()


# Orchestrator

class PipelineOrchestrator:
    """Orchestrates strategy selection and pipeline execution.

    This class is the only component that knows about concrete strategy
    implementations. It reads the runtime ``--engine`` flag, instantiates
    the appropriate ``LLMStrategy`` subclass, injects it into a
    ``TranscriptEnricher``, and delegates all stream processing to the engine.

    The ``TranscriptEnricher`` and all downstream components reference only
    the ``LLMStrategy`` abstract interface — they are completely decoupled
    from this selection logic.

    Supported engines:
        gemini: Google Gemini 2.5 Flash via the ``google-genai`` SDK.

    Raises:
        ValueError: If an unsupported engine name is provided.
        EnvironmentError: If the selected engine's required API key is absent.
    """

    # Registry maps CLI flag values to their concrete strategy constructors.
    # To add a new engine (e.g., OpenAI), register it here — nothing else changes.
    _STRATEGY_REGISTRY: dict[str, type[LLMStrategy]] = {
        "gemini": GeminiStrategy,
    }

    def __init__(self, engine: str):
        """Resolve the engine name to a concrete strategy and build the pipeline.

        Args:
            engine: The engine identifier supplied via ``--engine`` at runtime.

        Raises:
            ValueError: If ``engine`` is not a registered strategy key.
        """
        if engine not in self._STRATEGY_REGISTRY:
            supported = ", ".join(self._STRATEGY_REGISTRY.keys())
            raise ValueError(
                f"Unsupported engine '{engine}'. "
                f"Supported engines: {supported}"
            )

        logging.info("Initializing pipeline with engine: %s", engine)

        # Instantiate the concrete strategy — only the orchestrator does this
        strategy: LLMStrategy = self._STRATEGY_REGISTRY[engine]()

        # Inject the strategy into the engine via the abstract interface
        self.enricher = TranscriptEnricher(strategy)

    def run(self):
        """Start the pipeline stream processor."""
        self.enricher.run_stream()


def build_arg_parser() -> argparse.ArgumentParser:
    """Construct and return the CLI argument parser.

    Flags:
        --engine  (required): Selects the LLM backend at runtime.
                              Choices are drawn from the orchestrator's registry.
                              Example: --engine gemini

    Returns:
        A configured ``argparse.ArgumentParser`` instance.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Transcript Enrichment Pipeline — reads a JSONL stream from stdin, "
            "enriches each record using the selected LLM engine, and writes "
            "augmented JSONL to stdout."
        )
    )
    parser.add_argument(
        "--engine",
        required=True,
        choices=list(PipelineOrchestrator._STRATEGY_REGISTRY.keys()),
        help=(
            "LLM backend to use for enrichment. "
            "Currently supported: %(choices)s. "
            "Example: --engine gemini"
        )
    )
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        orchestrator = PipelineOrchestrator(engine=args.engine)
        orchestrator.run()
    except (EnvironmentError, ValueError) as e:
        logging.critical("Pipeline initialization failed: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
