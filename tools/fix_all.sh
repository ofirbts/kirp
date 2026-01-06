#!/bin/bash
cd ~/projects/kirp

echo "🔧 Fixing Tasks ObjectId..."
cat > app/storage/tasks.py << 'EOF'
# תיקון ObjectId + מגבלה
async def fetch_open_tasks():
    cursor = tasks_collection.find({"status": "open"})
    tasks = []
    async for doc in cursor:
        task = doc.copy()
        if '_id' in task:
            task['id'] = str(task.pop('_id'))
        tasks.append(task)
    return tasks[:10]
EOF

echo "🔧 Restarting backend..."
pkill -f uvicorn
sleep 2
uvicorn app.main:app --reload &

echo "⏳ Testing in 3s..."
sleep 3
./tools/check_kirp_full.sh
