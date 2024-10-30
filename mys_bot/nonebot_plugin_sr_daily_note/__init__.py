from datetime import datetime, timedelta

from nonebot.log import logger
from nonebot import require, on_command
from nonebot.adapters import Bot, Event
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_saa")
require("nonebot_plugin_mys_api")
require("nonebot_plugin_user_bind")

from nonebot_plugin_saa import Text, Image, MessageFactory

from mys_bot.nonebot_plugin_mys_api import MysApi
from mys_bot.nonebot_plugin_user_bind import get_user_bind
from mys_bot.nonebot_plugin_user_bind.cookie import (
    set_user_fp,
    get_user_stoken,
    get_user_cookie_with_fp,
)

__plugin_meta__ = PluginMetadata(
    name="StarRailNote",
    description="崩坏：星穹铁道开拓信息查询",
    usage="""srnote""",

)

error_code_msg = {
    1034: "查询遇验证码",
    10001: "绑定cookie失效，请重新绑定",
    -10001: "请求出错，请稍后重试",
}

srnote = on_command(
    "srnote",
    aliases={
        "星铁体力",
    },
    priority=2,
    block=True,
)


@srnote.handle()
async def get_note(bot: Bot, event: Event):
    user_list = await get_user_bind(bot.self_id, event.get_user_id(), '6')
    if not user_list:
        msg = "未绑定SRUID，请使用`星铁扫码绑定`或`srqr`命令扫码绑定"
        msg_builder = MessageFactory([Text(str(msg))])
        await msg_builder.finish(at_sender=not event.is_tome())
    sr_uid = user_list[0].uid
    mys_id = user_list[0].mys_id
    cookie, device_id, device_fp = await get_user_cookie_with_fp(
        bot.self_id, event.get_user_id(), sr_uid, '6'
    )
    stoken = await get_user_stoken(bot.self_id, event.get_user_id(), sr_uid, '6')
    if not mys_id or not cookie or not stoken:
        msg = "未绑定cookie，请使用`星铁扫码绑定`或`srqr`命令扫码绑定，或使用`星铁ck`或`srck`命令绑定"
        msg_builder = MessageFactory([Text(str(msg))])
        await msg_builder.finish(at_sender=not event.is_tome())
    logger.info(f"正在查询SRUID『{sr_uid}』便笺")
    cookie_with_token = f"{cookie};{stoken}"
    mys_api = MysApi(cookie_with_token, device_id, device_fp)
    if not device_id or not device_fp:
        device_id, device_fp = await mys_api.init_device()
    sr_note = await mys_api.call_mihoyo_api(api="sr_widget", role_uid=sr_uid)
    if isinstance(sr_note, int):
        if sr_note in error_code_msg:
            msg = error_code_msg[sr_note]
        else:
            msg = f"查询失败，请稍后重试（错误代码 {sr_note}）"
        msg_builder = MessageFactory([Text(str(msg))])
        await msg_builder.finish(at_sender=not event.is_tome())
    if new_fp := sr_note.get("new_fp"):
        await set_user_fp(bot.self_id, event.get_user_id(), sr_uid, device_id, new_fp)
    # 1. 开拓力
    stamina = f"{sr_note['current_stamina']}/ {sr_note['max_stamina']}"

    # 2. 预计回满
    current_time = datetime.now()
    recover_time = current_time + timedelta(seconds=sr_note['stamina_recover_time'])

    # 3. 派遣
    completed_expeditions = sum(1 for expedition in sr_note['expeditions'] if expedition['remaining_time'] == 0)
    total_expeditions = sr_note['total_expedition_num']
    expeditions = f"{completed_expeditions}/ {total_expeditions}"

    # 4. 每日实训
    train_score = f"{sr_note['current_train_score']}/{sr_note['max_train_score']}"

    # 5. 模拟宇宙积分
    rogue_score = f"{sr_note['current_rogue_score']}/{sr_note['max_rogue_score']}"

    # 6. 后备开拓力
    reserve_stamina = sr_note['current_reserve_stamina']

    # 7. 额外额外拟合值
    rogue_tourn_weekly = f"{sr_note['rogue_tourn_weekly_cur']}/{sr_note['rogue_tourn_weekly_max']}"

    result_string = (
        f"开拓力: {stamina}\n"
        f"预计回满: {recover_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"派遣: {expeditions}\n"
        f"每日实训: {train_score}\n"
        f"模拟宇宙积分: {rogue_score}\n"
        f"后备开拓力: {reserve_stamina}\n"
        f"额外额外拟合值: {rogue_tourn_weekly}"
    )

    msg_builder = MessageFactory([Text(result_string)])
    await msg_builder.finish()
