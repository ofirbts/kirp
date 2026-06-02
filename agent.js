import { GoogleGenerativeAI } from "@google/generative-ai";
import dotenv from "dotenv";
import fs from "fs/promises";
import axios from "axios";

dotenv.config();

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
if (!GEMINI_API_KEY) {
  console.error(
    "Missing GEMINI_API_KEY / GOOGLE_API_KEY in .env. Please set a valid Gemini API key.",
  );
  process.exit(1);
}

const genAI = new GoogleGenerativeAI(GEMINI_API_KEY);

/** פונקציית חיפוש אמיתי עם Tavily */
async function performWebSearch(query) {
  try {
    if (!process.env.TAVILY_API_KEY) {
      return "Error: TAVILY_API_KEY missing. Add to .env.";
    }
    const response = await axios.post("https://api.tavily.com/search", {
      api_key: process.env.TAVILY_API_KEY,
      query,
      search_depth: "smart",
      max_results: 3
    });
    return JSON.stringify(response.data.results, null, 2);
  } catch (error) {
    return `Search error: ${error.message}`;
  }
}

/** משיכת תוכן מאתר */
async function fetchUrlContent(url) {
  try {
    const response = await axios.get(url, { timeout: 5000 });
    const cleanText = response.data.toString().replace(/<[^>]*>/g, ' ').slice(0, 3000);
    return cleanText;
  } catch (error) {
    return `Fetch error: ${error.message}`;
  }
}

async function runAgent(query) {
  console.log(`[Gemini Agent]: מחקר על "${query}"...`);

  // הגדרת הכלים (function declarations)
  const tools = [
    {
      functionDeclarations: [
        {
          name: "web_search",
          description: "חיפוש מידע עדכני ברשת לקבלת הקשר רחב.",
          parameters: {
            type: "object",
            properties: { query: { type: "string", description: "השאילתא לחיפוש" } },
            required: ["query"]
          }
        },
        {
          name: "fetch",
          description: "משיכת תוכן מלא מדף ספציפי אם רלוונטי מאוד.",
          parameters: {
            type: "object",
            properties: { url: { type: "string", description: "כתובת URL" } },
            required: ["url"]
          }
        }
      ]
    }
  ];

  let chatHistory = [{ role: "user", parts: [{ text: query }] }];

  try {
    // לולאה לטיפול בכלים עד תשובה סופית
    const modelName = process.env.GEMINI_MODEL || "gemini-2.0-flash";
    console.log(`[Gemini Agent]: משתמש במודל ${modelName}`);
    while (true) {
      const model = genAI.getGenerativeModel({ 
        model: modelName, 
        tools 
      });

      const result = await model.generateContent({
        contents: chatHistory,
        generationConfig: { maxOutputTokens: 2000 }
      });

      const response = await result.response;
      const parts = response.candidates[0].content.parts;

      // בדיקה אם יש function calls
      const functionCalls = parts.filter(part => part.functionCall);
      if (functionCalls.length === 0) {
        // תשובה סופית
        const finalText = response.text();
        const fileContent = `# תוצאות מחקר: ${query}\n\n${finalText}\n\n*נוצר על ידי Gemini*`;
        await fs.writeFile("research_results.md", fileContent);
        console.log("\n[הצלחה]: שמרתי ב-research_results.md");
        console.log("\n=== תשובה סופית ===\n", finalText);
        break;
      }

      // ביצוע הכלים
      for (const fc of functionCalls) {
        const { name, args } = fc.functionCall;
        console.log(`[כלי]: מבצע ${name}(${JSON.stringify(args)})...`);
        let toolResult;

        if (name === "web_search") {
          toolResult = await performWebSearch(args.query);
        } else if (name === "fetch") {
          toolResult = await fetchUrlContent(args.url);
        }

        // הוספת function call ותוצאה להיסטוריה
        chatHistory.push({
          role: "model",
          parts: [{ functionCall: fc.functionCall }]
        });
        chatHistory.push({
          role: "user",
          parts: [{
            functionResponse: {
              name,
              response: { result: toolResult }
            }
          }]
        });
      }
    }
  } catch (error) {
    const msg = error?.message || String(error);
    if (msg.includes("API key not valid") || msg.includes("API_KEY_INVALID")) {
      console.error(
        "\n[שגיאה]: מפתח Gemini אינו תקף או לא שייך לפרויקט הנכון. בדוק את GEMINI_API_KEY / GOOGLE_API_KEY והפעלת ה-API בפרויקט.",
      );
    } else if (msg.includes("429") || msg.toLowerCase().includes("quota")) {
      console.error(
        "\n[שגיאה]: חריגה ממכסת Gemini (quota). בדוק את מגבלות השימוש ב-https://ai.google.dev/gemini-api/docs/rate-limits או עדכן תכנית חיוב.",
      );
    } else if (msg.includes("404") && msg.includes("models/")) {
      console.error(
        "\n[שגיאה]: המודל שבחרת אינו זמין ל-API הזה. הרץ `node list_models.js` ובחר שם מודל קיים ל-GEMINI_MODEL ב-.env.",
      );
    } else {
      console.error("\n[שגיאה לא צפויה]:", msg);
    }
  }
}

// הרצה: אם יש ארגומנט בשורת הפקודה נשתמש בו כשאילתה, אחרת ברירת מחדל
const userQueryFromCli = process.argv.slice(2).join(" ");
const defaultQuery = "What happened in the latest SpaceX launch?";
runAgent(userQueryFromCli || defaultQuery);
