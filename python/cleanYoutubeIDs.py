"""
clean_ids.py — YouTube ID validator
====================================
Reads one ID candidate per line from stdin.
Writes valid YouTube IDs to stdout (one per line).
Logs invalid IDs to pipeline_audit.log via the logging module.

Usage
-----
  # Pipe a file:
  cat youtube_ids | python3 clean_ids.py

  # Interactive (wait for keyboard input, Ctrl-C to exit):
  python3 clean_ids.py

Valid YouTube ID definition
---------------------------
  - Exactly 11 characters
  - Characters drawn from: A-Z  a-z  0-9  -  _
"""

# Including type hints in Python is a best practice!

import logging
import re
import sys

# Setup Logging
# All invalid-ID events go to pipeline_audit.log only (not to stderr/stdout per task requirement)
logging.basicConfig(
    filename = "pipeline_audit.log",
    filemode = "a",                          # append across multiple executions
    level    = logging.WARNING,
    format   = "%(asctime)s  %(levelname)s  %(message)s",
    datefmt  = "%Y-%m-%dT%H:%M:%S",
)
# The magic of using double under name resolves to the name of this current module.  In this case, __main__
# Doing this helps with Trouobleshooting and traceability
logger = logging.getLogger(__name__)

# Validation pattern
_VALID_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')


def is_valid_youtube_id(candidate: str) -> bool:

    # Return True if *candidate* is a well-formed YouTube video ID

    return bool(_VALID_ID.match(candidate))


def process_stream(stream) -> None:
    """
    Read lines from *stream*, validate each trimmed token, and:
      - print valid IDs to stdout
      - log invalid IDs to pipeline_audit.log
    """
    for raw_line in stream:
        candidate = raw_line.rstrip("\n").strip()

        # Skip blank lines silently
        if not candidate:
            continue

        if is_valid_youtube_id(candidate):
            # Write Valid IDs to stdout
            print(f"Valid Candidate ID: {candidate}")
        else:
            # Capture warnings to log file
            logger.warning("Invalid YouTube ID: %r", candidate)


def main() -> None:
    try:
        process_stream(sys.stdin)
    except KeyboardInterrupt:
        # Ctrl-C in interactive mode — exit cleanly, no traceback
        sys.stderr.write("\n")          # move past the ^C on the terminal line
        sys.exit(0)


if __name__ == "__main__":
    main()
