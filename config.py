import os
from dotenv import load_dotenv

load_dotenv()

MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")
OPERATOR_CHAT_ID = int(os.getenv("OPERATOR_CHAT_ID", "0"))
OPERATOR_WORK_HOURS = os.getenv("OPERATOR_WORK_HOURS", "будние дни с 9:00 до 18:00")

if not MAX_BOT_TOKEN:
    raise ValueError("Не задан MAX_BOT_TOKEN в файле .env")