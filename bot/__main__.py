import asyncio

from bot.handlers.handler import form_router
from bot.loguru_logger import configure_logging
from bot.settings import bot, dp, settings


async def main():
    configure_logging(logging_level=settings.log_level_number)
    dp.include_router(form_router)
    await asyncio.sleep(0.5)
    await bot.delete_my_commands(request_timeout=1)
    await bot.set_my_commands(
        commands=settings.bot_commands
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
