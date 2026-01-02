from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "kirp")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

settings = Settings()
