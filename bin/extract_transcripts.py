'''
DS5111 LAB04 and LAB05
Derrick Clarke (thq3hn)

'''
import sys
import os
import json
import logging
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

# Conditionally load variables from local environment configuration file if present
load_dotenv("../.env")

# Direct logging statements to a shared audit log asset
logging.basicConfig(
    filename='/home/ubuntu/DS5111-011/bin/pipeline/logs/pipeline_audit.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    logging.info("Pipeline Step 2A (Raw Extraction) started.")
    
    # Ingest routing keys from the local shell environment
    proxy_user = os.getenv("WEBSHARE_USER")
    proxy_pass = os.getenv("WEBSHARE_PASSWORD")
    
    if proxy_user and proxy_pass:
        logging.info("Proxy credentials detected. Routing traffic via Webshare Residential network.")
        # Runtime Configuration Management: Instantiating proxy configuration
        config = WebshareProxyConfig(username=proxy_user, password=proxy_pass)
        ytt_api = YouTubeTranscriptApi(proxy_config=config)
    else:
        logging.warning("No proxy credentials found. Running with direct raw local IP routing.")
        ytt_api = YouTubeTranscriptApi()

    # Process streaming IDs line-by-line from stdin
    for line in sys.stdin:
        video_id = line.strip()
        if not video_id:
            continue
            
        logging.info(f"Processing transcript extraction for video: {video_id}")

        try:
            # Unpack the incoming stream JSON record
            payload = json.loads(line)
            video_id = payload.get("video_id")
            raw_text = payload.get("raw_text")

            if not video_id or not raw_text:
                logging.warning(f"Malformed stream entry skipped. Missing keys in payload: {line}")
                continue
        
        #try:
            # Execute instance lookup method
        #    fetched_transcript = ytt_api.fetch(video_id)
        #    transcript_list = fetched_transcript.to_raw_data()
            
            # Stream Architecture Optimization: Structure the data as an explicit, 
            # single-line payload optimized for Snowflake VARIANT performance.
        #    payload = {
        #        "video_id": video_id,
        #        "transcript": transcript_list
        #    }
            
            # Write out line-by-line to standard out utilizing JSONL architecture
            #sys.stdout.write(json.dumps(payload) + "\n")
            #sys.stdout.flush()
            
        except Exception as e:
            logging.error(f"Failed to fetch YouTube transcript for {video_id}: {str(e)}")
            continue

    logging.info("Pipeline Step 2A finished.")

if __name__ == '__main__':
    main()

