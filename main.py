import asyncio
import logging
import os
import sys
from typing import Set

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

from service import parse_service

load_dotenv()


TOKEN = os.getenv('BOT_TOKEN')
PARSE_INTERVAL = int(os.getenv('PARSE_INTERVAL'))
MAX_MESSAGE_LENGTH = 4000


SUBSCRIBERS: Set[int] = set()
shutdown_event = asyncio.Event()

logger = logging.getLogger(__name__)

dp = Dispatcher()


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    if len(text) <= max_length:
        return [text]

    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break

        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = max_length

        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()

    return parts


async def send_message_safe(bot: Bot, chat_id: int, text: str) -> bool:
    try:
        messages = split_message(text)
        for msg in messages:
            await bot.send_message(chat_id, msg)
            await asyncio.sleep(0.05)
        return True
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        if "chat not found" in str(e).lower() or "bot was blocked" in str(e).lower():
            SUBSCRIBERS.discard(chat_id)
            logger.info(f"Removed inactive subscriber: {chat_id}")
        return False


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    SUBSCRIBERS.add(message.chat.id)
    logger.info(f"New subscriber: {message.chat.id} ({message.from_user.full_name})")
    await message.answer(
        f"👋 Привет, {html.bold(message.from_user.full_name)}!\n\n"
        f"Вы подписаны на обновления.\n"
        f"Интервал обновления: {PARSE_INTERVAL} сек."
    )


@dp.message(Command("stop"))
async def command_stop_handler(message: Message) -> None:
    SUBSCRIBERS.discard(message.chat.id)
    logger.info(f"Unsubscribed: {message.chat.id}")
    await message.answer("❌ Вы отписаны от обновлений.")



async def periodic_parse(bot: Bot) -> None:
    logger.info("Periodic parse task started")

    while not shutdown_event.is_set():
        try:
            if SUBSCRIBERS:
                logger.debug(f"Parsing for {len(SUBSCRIBERS)} subscribers...")
                data = await parse_service.parse_xml()

                if data:
                    for chat_id in list(SUBSCRIBERS):
                        for item in data:
                            await send_message_safe(bot, chat_id, item)
                else:
                    logger.debug("No data matching criteria")
            else:
                logger.debug("No subscribers, skipping parse")

        except Exception as e:
            logger.error(f"Error in periodic_parse: {e}", exc_info=True)

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=PARSE_INTERVAL)
            break
        except asyncio.TimeoutError:
            pass


async def on_shutdown(bot: Bot) -> None:
    logger.info("Shutting down...")
    shutdown_event.set()
    await bot.session.close()


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    parse_task = asyncio.create_task(periodic_parse(bot))

    try:
        logger.info("Bot started")
        await dp.start_polling(bot)
    finally:
        await on_shutdown(bot)
        parse_task.cancel()
        try:
            await parse_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
