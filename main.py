import asyncio
import logging

from maxapi import Bot, Dispatcher

from config import MAX_BOT_TOKEN
from database import init_db          # ← добавить
from handlers import start, faq, operator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    init_db()                          # ← добавить (создаст tickets.db при первом запуске)

    bot = Bot(token=MAX_BOT_TOKEN)
    dp = Dispatcher()

    dp.include_routers(start.router, operator.router, faq.router)

    logger.info("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")