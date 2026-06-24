#!/usr/bin/env python3
import sys
import json

def validate_payload(line_num, payload):
    """
    Validates a single line of JSON data against the target API contract.
    Returns True if valid, False otherwise.
    """
    required_fields = ["video_id", "cleaned_text"]
    optional_fields = ["tech_terms", "book_names"]
    
    # 1. Enforce top-level dictionary data structure
    if not isinstance(payload, dict):
        print(f"❌ [Row {line_num}] Schema Failure: Record is not a valid JSON Object.")
        return False

    # 2. Enforce Required Keys Presence
    for field in required_fields:
        if field not in payload:
            print(f"❌ [Row {line_num}] Schema Failure: Missing mandatory key '{field}'.")
            return False

    # 3. Enforce Required Value Data Types
    if not isinstance(payload["video_id"], str) or not payload["video_id"].strip():
        print(f"❌ [Row {line_num}] Type Failure: 'video_id' must be a non-empty STRING.")
        return False
        
    if not isinstance(payload["cleaned_text"], str):
        print(f"❌ [Row {line_num}] Type Failure: 'cleaned_text' must be a STRING.")
        return False

    # 4. Enforce Optional Key Structure and Type Safety
    for field in optional_fields:
        if field in payload:
            if not isinstance(payload[field], list):
                print(f"❌ [Row {line_num}] Type Failure: '{field}' must be an ARRAY (Python list).")
                return False
            
            # Ensure every element inside the array is a string primitive
            if not all(isinstance(item, str) for item in payload[field]):
                print(f"❌ [Row {line_num}] Type Failure: All elements inside '{field}' must be STRINGS.")
                return False
                
    return True

def main():
    print("🚀 Starting pipeline data contract validation...")
    total_records = 0
    failed_records = 0

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
            
        total_records += 1
        try:
            data = json.loads(line)
            if not validate_payload(total_records, data):
                failed_records += 1
        except json.JSONDecodeError:
            print(f"❌ [Row {total_records}] Syntax Failure: Line is not valid JSON Lines format.")
            failed_records += 1

    print("\n--- Validation Summary ---")
    if total_records == 0:
        print("⚠️ Warning: No records were processed via stdin.")
        sys.exit(1)
    elif failed_records > 0:
        print(f"🔴 Failure: {failed_records}/{total_records} records violated the schema contract.")
        sys.exit(1)
    else:
        print(f"🟢 Success: All {total_records} records successfully match the required data contract!")
        sys.exit(0)

if __name__ == '__main__':
    main()
