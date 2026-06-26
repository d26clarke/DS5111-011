import sys
import json
import pytest
from io import StringIO
from youtube_transcript_api import YouTubeTranscriptApi
import extract_transcripts

# 1. Create a dummy object to mimic the serialization payload return structure
class DummyFetchedTranscript:
    def to_raw_data(self):
        return [
            {"start": 0.0, "duration": 2.5, "text": "Hello world"},
            {"start": 2.5, "duration": 3.0, "text": "Data engineering testing"}
        ]

# 2. Construct the isolated pytest execution case using monkeypatch
def test_extract_pipeline_stream_serialization(monkeypatch):
    
    # Define a stubbed behavior method that bypasses the live web entirely
    def mock_api_fetch_execution(self, video_id):
        assert video_id == "test_id_123"
        return DummyFetchedTranscript()

    # Intercept the 'fetch' attribute on the target API class right before invocation
    monkeypatch.setattr(YouTubeTranscriptApi, "fetch", mock_api_fetch_execution)

    # Mock system inputs and tracking mechanisms using string stream loops
    mock_input_stream = StringIO("test_id_123\n")
    mock_output_stream = StringIO()

    monkeypatch.setattr(sys, "stdin", mock_input_stream)
    monkeypatch.setattr(sys, "stdout", mock_output_stream)

    # Suppress proxy environment validation variables during isolated CI checks
    monkeypatch.delenv("WEBSHARE_USER", raising=False)
    monkeypatch.delenv("WEBSHARE_PASSWORD", raising=False)

    # Execute the transformation runtime
    extract_transcripts.main()

    # Read back and parse JSONL stream results
    output_lines = mock_output_stream.getvalue().strip().split("\n")
    
    assert len(output_lines) == 1
    
    # Parse the exact payload to guarantee serialization schema integrity
    parsed_payload = json.loads(output_lines[0])
    assert parsed_payload["video_id"] == "test_id_123"
    assert len(parsed_payload["transcript"]) == 2
    assert parsed_payload["transcript"][1]["text"] == "Data engineering testing"

