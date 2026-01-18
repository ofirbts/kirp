#!/bin/bash

OUTPUT_FILE="/mnt/c/Users/User1/Desktop/kirp_full_dump.txt"

rm -f "$OUTPUT_FILE"

find . \
  -type f \
  \( -name "*.py" -o -name "*.md" -o -name "*.txt" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.toml" -o -name "Dockerfile" -o -name "docker-compose.yml" \) \
  ! -path "./mongo_data/*" \
  ! -path "./data/vector_store/*" \
  ! -path "*/__pycache__/*" \
  ! -path "*/assets/*" \
  | sort \
  | while IFS= read -r file; do
      echo "==============================" >> "$OUTPUT_FILE"
      echo "FILE: $file" >> "$OUTPUT_FILE"
      echo "==============================" >> "$OUTPUT_FILE"
      cat "$file" >> "$OUTPUT_FILE"
      printf "\n\n" >> "$OUTPUT_FILE"
    done

echo "הקובץ נוצר בהצלחה: $OUTPUT_FILE"

