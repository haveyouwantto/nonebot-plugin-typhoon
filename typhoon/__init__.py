from nonebot import on_command, require
from nonebot.adapters import Message, Event, Bot
from nonebot.params import CommandArg
from nonebot import logger
from datetime import datetime
from nonebot_plugin_session import extract_session, SessionIdType
from .typhoon import realtime_summary

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import (
    AlcMatches,
    Alconna,
    AlconnaQuery,
    Args,
    Image,
    Option,
    Query,
    Text,
    UniMessage,
    on_alconna,
)

import aiohttp
import io

matcher = on_alconna("台风",
    use_cmd_start=True,
    priority=5,
    block=True)

@matcher.handle()
async def handle(evt: Event):
    msg= Image(raw=await realtime_summary())
    print(msg)
    await matcher.send(msg)