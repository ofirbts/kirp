#!/bin/bash
echo -e "🚀=== KIRP SYSTEM AUDIT ===🚀"
echo -e "Date: $(date)"
echo

GREEN="\e[32m"; YELLOW="\e[33m"; RED="\e[31m"; BLUE="\e[36m"; RESET="\e[0m"

check_file() {
  local desc=$1
  local path=$2
  if [ -f "$path" ]; then
    echo -e "${GREEN}✔ $desc (${path})${RESET}"
  else
    echo -e "${RED}✖ $desc missing (${path})${RESET}"
  fi
}

section() {
  echo -e "\n${BLUE}=== $1 ===${RESET}"
}

# === Memory Intelligence ===
section "🧠 Memory Intelligence"
check_file "Decay module" "app/api/intelligence/decay.py"
check_file "Memory clustering" "app/services/memory_intelligence/cluster.py"
check_file "Summarization engine" "app/services/memory_intelligence/summarize.py"
check_file "Weekly summarization" "app/services/memory_intelligence/weekly.py"
check_file "Retriever" "app/rag/retriever.py"
check_file "Memory model" "app/models/memory.py"

# === Agent Reasoning ===
section "🤖 Agent Reasoning"
check_file "Main Agent logic" "app/agent/agent.py"
check_file "Agent tools" "app/agent/tools.py"
check_file "Agent API router" "app/api/agent.py"
check_file "Task extractor" "app/services/task_extractor.py"
check_file "Pipeline service" "app/services/pipeline.py"

# === Production Polish ===
section "🧪 Production Polish"
check_file "Query tests" "tools/test_query.py"
check_file "Task tests" "tools/test_tasks.py"
check_file "Full status check" "tools/check_kirp_full.sh"
check_file "Runbook" "app/Runbook.txt"
check_file "Docker Compose" "docker-compose.yml"

# === Additional Checks ===
section "🩺 Summary Readiness"
MI=$(ls app/api/intelligence/decay.py app/services/memory_intelligence/*.py 2>/dev/null | wc -l)
AG=$(ls app/agent/*.py app/api/agent.py 2>/dev/null | wc -l)
PP=$(ls tools/test_*.py 2>/dev/null | wc -l)

echo
if [ $MI -gt 3 ]; then echo -e "Memory Intelligence: ${GREEN}READY${RESET} ($MI modules)"; else echo -e "Memory Intelligence: ${YELLOW}PARTIAL${RESET} ($MI modules)"; fi
if [ $AG -gt 2 ]; then echo -e "Agent Reasoning: ${GREEN}READY${RESET} ($AG modules)"; else echo -e "Agent Reasoning: ${YELLOW}PARTIAL${RESET} ($AG modules)"; fi
if [ $PP -gt 1 ]; then echo -e "Production Polish: ${GREEN}READY${RESET} ($PP test scripts)"; else echo -e "Production Polish: ${RED}MISSING${RESET} ($PP test scripts)"; fi

echo -e "\n✅ Audit Complete. Look above for missing or partial components."
