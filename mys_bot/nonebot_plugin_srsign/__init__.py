from nonebot.log import logger
from nonebot import require, on_command
from nonebot.adapters import Bot, Event
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_saa")
require("nonebot_plugin_mys_api")
require("nonebot_plugin_user_bind")

from nonebot_plugin_saa import Text, MessageFactory

from mys_bot.nonebot_plugin_mys_api import MysApi
from mys_bot.nonebot_plugin_user_bind import get_user_bind
from mys_bot.nonebot_plugin_user_bind.cookie import (
    set_user_fp,
    get_user_cookie_with_fp,
)

__plugin_meta__ = PluginMetadata(
    name="StarRailSign",
    description="崩坏：星穹铁道米游社签到",
    usage="srsign"
)

error_code_msg = {
    10001: "绑定cookie失效，请重新绑定",
    -10001: "请求出错，请尝试重新使用`srqr`绑定",
    -5003: "今日已签到",
    -100: "请重新使用`srqr`绑定账号",
}

srsign = on_command(
    "srsign", aliases={"星铁签到", "星铁每日签到"}, priority=2, block=True
)


@srsign.handle()
async def _(bot: Bot, event: Event):
    user_id = event.get_user_id()
    user_list = await get_user_bind(bot.self_id, user_id, '6')
    if not user_list:
        err = "未绑定星铁账号，请使用[mysqr]或[扫码登录]进行绑定"
        msg_builder = MessageFactory([Text(err)])
        await msg_builder.send(at_sender=not event.is_tome())
        await srsign.finish()
    msg: list[str] = []
    for user in user_list:
        uid = user.uid
        cookie, device_id, device_fp = await get_user_cookie_with_fp(
            bot.self_id, event.get_user_id(), uid, '6'
        )
        if not cookie:
            msg.append(
                f"UID{uid}: 未绑定cookie，请使用`srck [cookie]`绑定或`srqr`扫码绑定"
            )
            continue
        logger.info(f"开始为SRUID『{uid}』签到")
        mys_api = MysApi(cookie, device_id, device_fp)
        if not device_id or not device_fp:
            device_id, device_fp = await mys_api.init_device()
        sign = await mys_api.call_mihoyo_api("sr_sign", role_uid=uid, region=user.region)
        if not sign:
            msg.append(
                f"UID{uid}: 疑似cookie失效，请重新使用`srck [cookie]`绑定或`srqr`扫码绑定"
            )
            msg_builder = MessageFactory([Text(str(msg))])
            await msg_builder.send(at_sender=not event.is_tome())
            await srsign.finish()
        if isinstance(sign, int):
            if sign in error_code_msg:
                msg.append(f"UID{uid}: {error_code_msg[sign]}")
            else:
                msg.append(f"UID{uid}: 签到失败（错误代码 {sign}）")
            continue
        is_risk = sign.get("is_risk")
        if is_risk is True:
            msg.append(f"UID{uid}: 签到遇验证码，请手动签到")
        else:
            msg.append(f"UID{uid}: 签到成功")
            if new_fp := sign.get("new_fp"):
                await set_user_fp(
                    bot.self_id, event.get_user_id(), uid, device_id, new_fp
                )
    msg_builder = MessageFactory([Text("\n" + "\n".join(msg))])
    await msg_builder.finish(at_sender=not event.is_tome())
