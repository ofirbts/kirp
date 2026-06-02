import dotenv from "dotenv";

dotenv.config();

// Use GEMINI_API_KEY as the primary key for Gemini; fall back to GOOGLE_API_KEY if needed.
const apiKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;

if (!apiKey) {
  console.error("Missing GEMINI_API_KEY / GOOGLE_API_KEY in .env");
  process.exit(1);
}

async function list() {
  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models?key=${encodeURIComponent(
      apiKey,
    )}`;
    const res = await fetch(url);
    if (!res.ok) {
      const text = await res.text();
      console.error("Error listing models:", res.status, res.statusText, text);
      return;
    }
    const data = await res.json();
    const models = data.models || [];
    console.log("Available Models:");
    if (models.length === 0) {
      console.log("(no models returned – check API key / project / region)");
      return;
    }
    models.forEach((m) => console.log(m.name));
  } catch (err) {
    console.error("Error listing models:", err.message || err);
  }
}

list();