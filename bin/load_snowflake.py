# File location: bin/load_snowflake.py
import sys
import os
import json
import logging
import snowflake.connector
from dotenv import load_dotenv

logging.basicConfig(
    filename='bin/pipeline/logs/pipeline_audit.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    load_dotenv("../.env")
    logging.info("Pipeline Step 3 (Snowflake Loader Node) initialized.")

    # DONE 1 (DONE) Environment Handshake & Connection 
    sf_user      = os.getenv('SF_USER')
    sf_password  = os.getenv('SF_PASSWORD')
    sf_schema    = os.getenv('SF_SCHEMA')
    sf_account   = os.getenv('SF_ACCOUNT')
    sf_warehouse = os.getenv('SF_WAREHOUSE')
    sf_database  = os.getenv('SF_DATABASE')
    sf_role      = os.getenv('SF_ROLE')

    if not sf_user or not sf_password:
        logging.critical("Missing critical Snowflake runtime credential bindings. Ingestion aborted.")
        sys.exit(1)

    print(f"Initializing connection to Snowflake account '{sf_account}' as user '{sf_user}'...")

    try:
        conn   = snowflake.connector.connect(
            account=sf_account, user=sf_user, password=sf_password,
            role=sf_role, warehouse=sf_warehouse,
            database=sf_database, schema=sf_schema
        )
        cursor = conn.cursor()
        cursor.execute(
            "SELECT CURRENT_VERSION(), CURRENT_USER(), CURRENT_ROLE(), "
            "CURRENT_DATABASE(), CURRENT_SCHEMA();"
        )
        version, user, role, db, schema = cursor.fetchone()
        print("\n [SUCCESS] Secure Handshake Completed...")
        print(f" - Snowflake Version:        {version}")
        print(f" - Authenticated User:       {user}")
        print(f" - Active Session Role:      {role}")
        print(f" - Target Database Context:  {db}.{schema}")
    except snowflake.connector.errors.ProgrammingError as e:
        logging.critical(f" [CREDENTIALS ERROR] Snowflake rejected connection parameters: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logging.critical(f"Snowflake Authorization Context Handshake Failed: {str(e)}")
        sys.exit(1)

    # DONE 2 DDL: Guarantee landing table exists 
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_pipeline_ingest (
                record_id    NUMBER AUTOINCREMENT PRIMARY KEY,
                raw_payload  VARIANT,
                ingested_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
            )
        """)
        logging.info("Target table 'raw_pipeline_ingest' verified / created successfully.")
        print(" [DDL] Target landing table structure validated.")
    except Exception as e:
        logging.error(f"Failed to execute target structural validation DDL: {str(e)}")
        cursor.close()
        conn.close()
        sys.exit(1)

    # DONE 3 Streaming insertion loop 
    for line in sys.stdin:
        cleaned_line = line.strip()
        if not cleaned_line:
            continue
        try:
            json_data = json.loads(cleaned_line)
            cursor.execute(
                "INSERT INTO raw_pipeline_ingest (raw_payload) SELECT PARSE_JSON(%s)",
                (json.dumps(json_data),)
            )
            logging.info(
                f"Loaded entry token item target: "
                f"[{json_data.get('video_id', 'UNKNOWN')}] safely to warehouse."
            )
        except Exception as e:
            logging.error(f"Skipping corrupt pipeline payload stream element: {str(e)}")

    # DONE 4 Resource reclamation 
    try:
        cursor.close()
        logging.info("Snowflake cursor closed.")
    except Exception as e:
        logging.warning(f"Cursor close warning: {str(e)}")

    try:
        conn.close()
        logging.info("Snowflake connection closed.")
    except Exception as e:
        logging.warning(f"Connection close warning: {str(e)}")

    logging.info("Pipeline Step 3 finished execution cycles cleanly.")

if __name__ == '__main__':
    main()

