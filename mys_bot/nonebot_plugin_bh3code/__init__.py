from nonebot.adapters import Event
from nonebot.plugin import PluginMetadata
from nonebot import logger, require, on_command

from .data_source import get_code_msg

require("nonebot_plugin_saa")

from nonebot_plugin_saa import Text, MessageFactory

__plugin_meta__ = PluginMetadata(
    name="HongKaiCode",
    description="崩坏3前瞻直播兑换码",
    usage="""查询兑换码: bh3code"""
)

srcode = on_command("bh3code", aliases={"崩坏3兑换码"})


@srcode.handle()
async def _(event: Event):
    try:
        codes = await get_code_msg()
    except Exception as e:
        logger.opt(exception=e).error("获取前瞻兑换码失败")
        codes = "获取前瞻兑换码失败"
    msg_builder = MessageFactory([Text(str(codes))])
    await msg_builder.finish(at_sender=not event.is_tome())
