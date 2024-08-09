import asyncio
import json
from contextlib import suppress
from functools import wraps

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from loguru import logger
from pydantic_core import ValidationError


def message_process_error(func):
    async def process_error(e, *args, **kwargs):
        message: Message = args[0]
        bot = message.bot
        if isinstance(e, ValidationError):
            err_data = json.loads(e.json())
            e = f'Поле "{err_data[0]["loc"][0]}": {err_data[0]["msg"]}'
        message_answer = await message.answer(
            f"{e if e else 'Error'}",
        )
        await asyncio.sleep(3)
        with suppress(TelegramBadRequest):
            for m_id in range(
                message_answer.message_id - 1, message_answer.message_id + 1
            ):
                await bot.delete_message(message.from_user.id, m_id)

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(e)
            await process_error(e, *args, **kwargs)

    return wrapper
