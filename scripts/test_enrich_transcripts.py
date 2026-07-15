import io
import json
import pytest
from enrich_transcripts import TranscriptEnricher, LLMStrategy


class MockLLMStrategy(LLMStrategy):
    """Fake strategy that returns canned data instead of calling a real LLM."""

    def call_llm(self, raw_text: str) -> str:
        return '{"tech_stack": ["Snowflake"], "literature_references": []}'

    def parse_response(self, raw_response: str) -> dict:
        return json.loads(raw_response)


def test_enricher_processes_single_line(monkeypatch, capsys):
    input_line = json.dumps({"video_id": "v001", "raw_text": "some transcript text"}) + "\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(input_line))

    engine = TranscriptEnricher(MockLLMStrategy())
    engine.run_stream()

    output = capsys.readouterr().out.strip()
    result = json.loads(output)

    assert result["video_id"] == "v001"

    # Completed TODO #1: assert the enriched_data key is present and matches the mock's canned output
    assert result["enriched_data"] == {
        "tech_stack": ["Snowflake"],
        "literature_references": []
    }

    # Completed TODO #2: assert the pipeline emitted a SUCCESS status
    assert result["pipeline_status"] == "SUCCESS"

