import asyncio
import json
import random
from hashlib import sha256
from hmac import new
from urllib.parse import quote, unquote

import aiohttp
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from bot.config import settings
from bot.exceptions import InvalidSession
from bot.utils import logger
from pyrogram import Client
from pyrogram.errors import (
    AuthKeyUnregistered,
    FloodWait,
    Unauthorized,
    UserDeactivated,
)
from pyrogram.raw.functions.messages import RequestWebView

from .agents import generate_random_user_agent
from .headers import headers

tg_client
session_name


async def get_tg_web_data(self, proxy: str | None) -> str:
    try:
        with_tg = True

        if not self.tg_client.is_connected:
            with_tg = False
            try:
                await self.tg_client.connect()
                await self.tg_client.send_message(
                    "pixelversexyzbot", "/start 178648151"
                )
            except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                raise InvalidSession(self.session_name)

        while True:
            try:
                peer = await self.tg_client.resolve_peer("pixelversexyzbot")
                break
            except FloodWait as fl:
                fls = fl.value

                logger.warning(f"{self.session_name} | FloodWait {fl}")
                logger.info(f"{self.session_name} | Sleep {fls}s")

                await asyncio.sleep(fls + 3)

        web_view = await self.tg_client.invoke(
            RequestWebView(
                peer=peer,
                bot=peer,
                platform="android",
                from_bot_menu=False,
                url="https://sexyzbot.pxlvrs.io/",
            )
        )

        auth_url = web_view.url
        tg_web_data = unquote(
            string=unquote(
                string=auth_url.split("tgWebAppData=", maxsplit=1)[1].split(
                    "&tgWebAppVersion", maxsplit=1
                )[0]
            )
        )

        if with_tg is False:
            await self.tg_client.disconnect()

        return tg_web_data

    except InvalidSession as error:
        raise error

    except Exception as error:
        logger.error(
            f"{self.session_name} | Unknown error during Authorization: {error}"
        )
        await asyncio.sleep(delay=3)


async def run_tasks(tg_clients: list[Client]):
    tasks = [
        asyncio.create_task(
            run_tapper(
                tg_client=tg_client
            )
        )
        for tg_client in tg_clients
    ]

    await asyncio.gather(*tasks)


async def get_tg_clients() -> list[Client]:
    global tg_clients

    session_names = get_session_names()

    if not session_names:
        raise FileNotFoundError("Not found session files")

    if not settings.API_ID or not settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    tg_clients = [
        Client(
            name=session_name,
            api_id=settings.API_ID,
            api_hash=settings.API_HASH,
            workdir="sessions/",
            plugins=dict(root="bot/plugins"),
        )
        for session_name in session_names
    ]

    return tg_clients


def get_session_names() -> list[str]:
    session_names = glob.glob("sessions/*.session")
    session_names = [
        os.path.splitext(os.path.basename(file))[0] for file in session_names
    ]

    return session_names
