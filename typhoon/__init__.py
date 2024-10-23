from nonebot import on_command, require
from nonebot.adapters import Message, Event, Bot
from nonebot.params import CommandArg
from nonebot import logger
from datetime import datetime
from nonebot_plugin_session import extract_session, SessionIdType
from .typhoon import realtime_summary, plot_typhoon

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

matcher = on_alconna(
    Alconna(
        "台风", Option("-t|--typhoon", Args["typhoon", str], help_text="显示特定台风")
    ),
    use_cmd_start=True,
    priority=5,
    block=True,
)


@matcher.handle()
async def handle(evt: Event, typhoon: Query[str] = AlconnaQuery("typhoon", None)):
    if typhoon.result is not None:
        msg = Image(raw=await plot_typhoon(typhoon.result))
    else:
        msg = Image(raw=await realtime_summary())
    print(msg)
    await matcher.send(msg)
