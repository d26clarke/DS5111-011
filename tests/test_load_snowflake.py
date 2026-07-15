# File location: tests/test_load_snowflake.py
import sys
import io
import json
import pytest
from unittest.mock import MagicMock

# Target the main script module and entrypoint loop
from bin.load_snowflake import main

def test_load_snowflake_pipeline_ingestion_loop(monkeypatch, capsys):
    """
    Verifies that main() correctly processes stringified JSON lines from stdin,
    triggers table structural validation DDL, and executes safe parameter-bound insertions.
    """
    # 1. Setup mock database connector dependencies
    mock_cursor = MagicMock()
    mock_context = MagicMock()
    mock_context.cursor.return_value = mock_cursor
    
    # 2. Prevent the script from attempting real external network calls
    import snowflake.connector
    monkeypatch.setattr(snowflake.connector, "connect", lambda **kwargs: mock_context)
    
    # 3. Intercept and isolate execution shell environment state
    monkeypatch.setenv("SF_USER", "test_user")
    monkeypatch.setenv("SF_PASSWORD", "test_password")
    
    # 4. Fabricate structured incoming JSON Lines streaming content
    mock_input_stream = io.StringIO(
        '{"video_id": "test_id_001", "source": "youtube", "raw_text": "Sample content text A."}\n'
        '{"video_id": "test_id_002", "source": "podcast", "raw_text": "Sample content text B."}\n'
    )
    monkeypatch.setattr(sys, "stdin", mock_input_stream)
    
    # 5. Execute target script processing execution block
    try:
        main()
    except UnboundLocalError:
        pytest.fail("Resource variables referenced before definition. Verify cursor initialization logic.")

    # 6. Structurally assert that the schema verification table statements occurred
    assert mock_cursor.execute.call_count >= 3, "The database cursor should trigger table generation plus one call per row entry."
    
    # Extract the distinct raw query text argument configurations executed by the mock engine
    executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
    executed_bindings = [call[0][1] for call in mock_cursor.execute.call_args_list if len(call[0]) > 1]
    
    # Verify Table Invariant Generation Assertion
    assert any("CREATE TABLE IF NOT EXISTS RAW_TRANSCRIPTS" in q for q in executed_queries), \
        "The script must verify target table existence before attempting ingestion operations."
        
    # Verify Parameter Invariant Insertion Assertions
    insert_queries = [q for q in executed_queries if "INSERT INTO RAW_TRANSCRIPTS" in q]
    assert len(insert_queries) == 2, "Exactly two SQL insert invocations should occur for two input rows."
    
    for query in insert_queries:
        assert "PARSE_JSON(%s)" in query, "The engine must pass payloads safely wrapped inside a database PARSE_JSON call."
        assert "%s" in query and "f" not in query, "Security Violation: Hard-coded formatting detected. Use standard parameter placeholders."
        
    # Ensure parameter payloads are passed safely within matching positional argument tuples
    assert len(executed_bindings) == 2
    parsed_payload = json.loads(executed_bindings[0][0])
    assert parsed_payload["video_id"] == "test_id_001"

