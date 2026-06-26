default:
	@cat makefile

env:
	python3 -m venv env; . env/bin/activate; pip install --upgrade pip

update:  env
	. env/bin/activate; pip install -r requirements.txt

lint:  env
	. env/bin/activate; pylint python/cleanYoutubeIDs.py
test_enrich:
	@. env/bin/activate && cat mock_transcripts.jsonl | python -u python/enrich_transcripts.py | python python/validate_schema.py
