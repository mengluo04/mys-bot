from nonebot.log import logger
from nonebot import require, on_command
from nonebot.adapters import Bot, Event
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_saa")
require("mys_api")
require("user_bind")

from nonebot_plugin_saa import Text, MessageFactory

from mys_bot.mys_api import MysApi
from mys_bot.user_bind import get_user_bind
from mys_bot.user_bind.cookie import (
    set_user_fp,
    get_user_cookie_with_fp,
)

__plugin_meta__ = PluginMetadata(
    name="ZzzSign",
    description="绝区零米游社签到",
    usage="zzzsign"
)

error_code_msg = {
    10001: "绑定cookie失效，请重新绑定",
    -10001: "请求出错，请尝试重新使用`zzzqr`绑定",
    -5003: "今日已签到",
    -100: "请重新使用`zzzqr`绑定账号",
}

zzzsign = on_command(
    "zzzsign", aliases={"绝区零签到", "绝区零每日签到"}, priority=2, block=True
)


@zzzsign.handle()
async def _(bot: Bot, event: Event):
    user_id = event.get_user_id()
    user_list = await get_user_bind(bot.self_id, user_id, '8')
    if not user_list:
        err = "未绑定zzzUID，请使用`zzzck [cookie]`绑定或`zzzqr`扫码绑定"
        msg_builder = MessageFactory([Text(err)])
        await msg_builder.send(at_sender=not event.is_tome())
        await zzzsign.finish()
    msg: list[str] = []
    for user in user_list:
        uid = user.uid
        cookie, device_id, device_fp = await get_user_cookie_with_fp(
            bot.self_id, event.get_user_id(), uid, '8'
        )
        if not cookie:
            msg.append(
                f"UID{uid}: 未绑定cookie，请使用`zzzck [cookie]`绑定或`zzzqr`扫码绑定"
            )
            continue
        logger.info(f"开始为zzzUID『{uid}』签到")
        mys_api = MysApi(cookie, device_id, device_fp)
        if not device_id or not device_fp:
            device_id, device_fp = await mys_api.init_device()
        sign = await mys_api.call_mihoyo_api("zzz_sign", role_uid=uid, region=user.region, extra_headers={
            "x-rpc-signgame": "zzz",
            "Origin": "https://act.mihoyo.com",
            "Referer": "https://act.mihoyo.com/",
            "Host": "act-nap-api.mihoyo.com"
        })
        if not sign:
            msg.append(
                f"UID{uid}: 疑似cookie失效，请重新使用`zzzck [cookie]`绑定或`zzzqr`扫码绑定"
            )
            msg_builder = MessageFactory([Text(str(msg))])
            await msg_builder.send(at_sender=not event.is_tome())
            await zzzsign.finish()
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
