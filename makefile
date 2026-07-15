ENV = env
PYTHON = $(VENV)/bin/python3
PIP = $(ENV)/bin/pip

default:
	@cat makefile

env:
	$(PYTHON) -m venv env; . env/bin/activate; $(PIP) install --upgrade pip

test:
	$(PYTHON) -m pytest tests/

lint:
	$(PYTHON) -m pylint bin/ lib/ tests/


update:  env
	. env/bin/activate; $(PIP) install -r requirements.txt

lint:  env
	. env/bin/activate; pylint bin/cleanYoutubeIDs.py
run:
	@. env/bin/activate && cat mock_transcripts.jsonl | $(PYTHON) -u bin/enrich_transcripts.py | $(PYTHON) bin/validate_schema.py

test:
	@. env/bin/activate && pytest -v tests/test_enrich_transcripts.py

.PHONY: load
load:
	@echo "Initiating Cloud Data Warehouse Synchronizer Node..."
	#cat data/enriched_transcripts.jsonl | ${PYTHON} bin/load_snowflake.py
	cat data/transcripts_raw.jsonl | python bin/load_snowflake.py

