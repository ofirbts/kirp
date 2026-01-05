import asyncio
import logging
from datetime import datetime, timedelta

from app.services.memory_intelligence.strength import decay_memory_strength
from app.services.memory_intelligence.weekly import generate_weekly_summary
from app.storage.memory import fetch_recent_memories
from app.services.task_extractor import extract_task


async def agent_loop():
    logging.info("🤖 Agent loop started")

    last_weekly_run: datetime | None = None

    while True:
        try:
            now = datetime.utcnow()

            # 1️⃣ Decay – כל 30 דקות
            await decay_memory_strength()

            # 2️⃣ Weekly summary – פעם בשבוע באמת
            if (
                last_weekly_run is None
                or now - last_weekly_run > timedelta(days=7)
            ):
                try:
                    await generate_weekly_summary(days=7)
                    last_weekly_run = now
                    logging.info("📊 Weekly summary generated")
                except Exception as e:
                    logging.warning(f"Weekly summary skipped: {e}")

            # 3️⃣ Task extraction – רק על חדשים
            memories = await fetch_recent_memories(limit=20)
            for mem in memories:
                await extract_task(mem)

        except Exception as e:
            logging.exception(f"🤖 Agent error: {e}")

        # ⏱️ sleep מרכזי
        await asyncio.sleep(1800)  # 30 דקות
