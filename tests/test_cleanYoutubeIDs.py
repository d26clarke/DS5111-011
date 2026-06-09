import sys
import io
import pytest
from python.cleanYoutubeIDs.py import main

def test_script_execution(monkeypatch, capsys):
    # 1. Simulate the standard input data
    # We use io.StringIO to make a string act like a readable stream/file
    fake_input = io.StringIO("kcFsuxaJ1es\nasd123\n")
    monkeypatch.setattr(sys, "stdin", fake_input)

    # 2. Run the script's main logic
    main()

    # 3. Capture the printed output
    captured = capsys.readouterr()
    
    # 4. Assert that the data was modified correctly
    assert captured.out == "kcFsuxaJ1es\n"
