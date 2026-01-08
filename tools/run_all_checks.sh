#!/bin/bash

TOOLS_DIR="tools"
LOG_FILE="test_run.log"
JSON_FILE="test_results.json"

echo "" > "$LOG_FILE"
echo "" > "$JSON_FILE"

severity_for() {
    case "$1" in
        *memory*|*chaos*|*load*) echo "HIGH" ;;
        *policy*|*explain*) echo "MEDIUM" ;;
        *) echo "LOW" ;;
    esac
}

run_check() {
    FILE="$1"
    START=$(date +%s.%N)
    SEV=$(severity_for "$FILE")

    if [[ "$FILE" == *.py ]]; then
        python3 "$FILE" >> "$LOG_FILE" 2>&1
    else
        bash "$FILE" >> "$LOG_FILE" 2>&1
    fi

    STATUS=$([[ $? -eq 0 ]] && echo "PASS" || echo "FAIL")
    END=$(date +%s.%N)
    DUR=$(echo "$END - $START" | bc)

    echo "$FILE|$STATUS|$SEV|$DUR" >> "$JSON_FILE"

    if [[ "$STATUS" == "PASS" ]]; then
        echo -e "\033[0;32m[PASS]\033[0m $FILE (Severity: $SEV, ${DUR}s)"
    else
        echo -e "\033[0;31m[FAIL]\033[0m $FILE (Severity: $SEV, ${DUR}s)"
    fi
}

echo "=== Running checks ==="

for f in tools/check_*.py tools/check_*.sh; do
    [[ -f "$f" ]] && run_check "$f"
done

echo "=== Checking for junk files ==="
JUNK=$(find tools -type f -name "*.pyc" -o -name "*~" -o -name "*.swp")
if [[ "$JUNK" != "" ]]; then
    echo -e "\033[1;33m[WARN]\033[0m Junk files found:"
    echo "$JUNK"
    echo "junk_check|WARN|MEDIUM|0" >> "$JSON_FILE"
else
    echo -e "\033[0;32m[PASS]\033[0m No junk files."
    echo "junk_check|PASS|LOW|0" >> "$JSON_FILE"
fi

echo ""
echo "=== Summary ==="

PASS=$(grep "|PASS|" "$JSON_FILE" | wc -l)
FAIL=$(grep "|FAIL|" "$JSON_FILE" | wc -l)
WARN=$(grep "|WARN|" "$JSON_FILE" | wc -l)
TOTAL=$((PASS + FAIL + WARN))

echo "Total checks: $TOTAL"
echo -e "\033[0;32mPassed: $PASS\033[0m"
echo -e "\033[0;31mFailed: $FAIL\033[0m"
echo -e "\033[1;33mWarnings: $WARN\033[0m"

POINTS=$(echo "$PASS*1 + $WARN*0.6" | bc)
HEALTH=$(echo "($POINTS / $TOTAL) * 100" | bc -l | xargs printf "%.0f")

echo ""
echo "=== System Health ==="
echo "Health: $HEALTH/100"

BAR_LEN=30
FILLED=$(echo "$HEALTH * $BAR_LEN / 100" | bc)
EMPTY=$(echo "$BAR_LEN - $FILLED" | bc)

printf "\033[0;32m%0.s█" $(seq 1 $FILLED)
printf "\033[0;31m%0.s░" $(seq 1 $EMPTY)
printf "\033[0m\n"

echo ""
echo "=== AI Summary ==="
if [[ $FAIL -gt 0 ]]; then
    echo "- יש כשלי מערכת שדורשים טיפול מיידי."
fi
if [[ $WARN -gt 0 ]]; then
    echo "- יש אזהרות שכדאי לבדוק."
fi
if [[ $FAIL -eq 0 && $WARN -eq 0 ]]; then
    echo "- המערכת יציבה ובריאה."
fi
echo "- אחוז הבריאות הכולל של המערכת הוא $HEALTH מתוך 100."
