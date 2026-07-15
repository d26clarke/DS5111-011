# DS 5111: Streamlining Data Science with Software and Automation Skills

Welcome to **DS 5111: Streamlining Data Science with Software and Automation Skills!**

This is a very "hands-on" course — in essence, a learning lab. Its purpose is to complement your Data Science skills by walking through putting a pipeline together in as close a way as you would in a real work setting. The emphasis is on removing as much of the "surprise" factor when entering a real work setting, as well as picking up skills that make you efficient.

---

## Course Philosophy

Rather than focusing on the internals of any single algorithm or model, this course focuses on the **entire process around it** — from collecting and cleaning data, to managing your work in version control, to deploying and collaborating as part of a team. The skills you gain here are transferable regardless of the programming language or environment you eventually work in.

---

## Topics Covered

### Command Line & Cloud Computing

For efficiency's sake, we take a close look at using the **command line**, which remains — after all these years — the backbone of how software is configured, accessed, and run remotely. To that end, you will set up and work on an **Ubuntu AWS instance** throughout the semester to get comfortable with using the cloud.

### Core Tools

| Tool | Purpose |
| :--- | :--- |
| **Git & GitHub** | Version control and collaborative code management |
| **GitHub Actions** | CI/CD automation and workflow management |
| **dbt (Data Build Tool)** | A widely used Python package for data transformation and manipulation |
| **Snowflake** | A cloud-based data lake/store tool, commonly paired with dbt |
| **Docker** | Creating and sharing reproducible environments |
| **Windsurf** | AI-assisted coding tool |

Both Git/GitHub and GitHub Actions are a major pain point for many developers but can become a real boost for productivity once mastered. You are virtually guaranteed to use one or both in any technical role today.

### Software Engineering Practices

The course touches on the following practices, with a primary focus on **efficiency** — the ideas and experience you gain from incorporating these into your workflow pay off by saving you time and energy:

- **Object-Oriented Design (OOD)**
- **Testing**
- **Design Patterns**

---

## Course Project: NFL Season Analysis Pipeline

You will build a data pipeline in as close to a real work setting as possible. The project analyzes **NFL season results to make predictions**, running the full gamut from data collection to reporting:

1. Collecting raw NFL season data
2. Cleaning and transforming the data
3. Inserting data into **dbt / Snowflake**
4. Generating result tables for a final report

### Team Collaboration

In the second half of the semester, you will be part of a **team** attending **Scrum meetings** (short 5–10 minute check-ins after class). You will manage all work in **git/github**, mirroring the workflow of a real development team.

---

## Getting Started

### Prerequisites

- Access to an AWS account (provided or personal)
- Git installed locally
- Python 3.x
- A GitHub account
- To Use SSH instead of HTTPS:  git remote set-url origin git@github.com:d26clarke/DS5111-011.git

### Environment Setup

Detailed setup instructions for the Ubuntu AWS instance, GitHub repository, and required tools will be provided in the course materials. All configuration will be performed via the command line to reinforce the skills covered in class.

---

Operational Runbook & Project Overview

This repository contains an automated text-processing pipeline designed to clean YouTube IDs, enrich text transcripts, and validate output schemas. 

The project uses a Makefile to standardize local development and a GitHub Actions workflow to enforce continuous integration (CI) quality gates. 

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

1. Environment Lifecycle

In a bash shell, 

execute "make env" to create an isolated python environment
- OR -  
execute "make update" to pull the latest libraries from requirements.txt into the active environment.

2. Code Quality & Testing

In a bash shell, 

execute "make lint" to run pylint to verify syntax and code style

execute "make test" to execute a python test

3. Execution Pipeline (Run Data Job)

In a bash shell, 

execute "make run"

4. CI/CD pipeline

This project enforces structural and functional validation via a automated GitHub Actions workflow (.github/workflows/ci.yml).

## Contact

For questions, please refer to the course syllabus or contact the instructor through the course management system.
