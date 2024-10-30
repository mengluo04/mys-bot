import re
import json
import asyncio
import contextlib
from io import BytesIO
from typing import Any

from nonebot.log import logger
from nonebot.plugin import PluginMetadata
from nonebot import get_bot, require, on_command
from nonebot.adapters import Bot, Event, Message

require("nonebot_plugin_saa")
require("nonebot_plugin_orm")
require("nonebot_plugin_mys_api")
require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_saa import (
    Text,
    Image,
    Mention,
    MessageFactory,
    PlatformTarget,
    extract_target,
)

try:
    from mys_bot.nonebot_plugin_mys_api import MysApi
except ModuleNotFoundError:
    from nonebot_plugin_mys_api import MysApi  # type: ignore

from .model import UserBind
from .data_source import (
    del_user_bind,
    generate_qrcode,
    get_user_bind,
    set_user_bind,
)

__plugin_meta__ = PluginMetadata(
    name="UserBind",
    description="账号绑定",
    usage="mysqr"
)

qrbind_buffer: dict[str, Any] = {}

srdel = on_command(
    "srdel",
    aliases={
        "星铁解绑",
        "星铁取消绑定",
        "星铁解除绑定",
        "星铁取消账号绑定",
        "星铁解除账号绑定",
    },
    priority=2,
    block=True,
)
mysqr = on_command(
    "mysqr",
    aliases={"米游社扫码绑定"},
    priority=2,
    block=True,
)


@mysqr.handle()
async def _(bot: Bot, event: Event):
    user_id = str(event.get_user_id())
    if user_id in qrbind_buffer:
        msg_builder = MessageFactory([Text("你已经在绑定中了，请扫描上一次的二维码")])
        await msg_builder.finish(at_sender=not event.is_tome())
    mys_api = MysApi()
    login_data = await mys_api.create_login_qr(2)
    if login_data is None:
        msg_builder = MessageFactory(
            [
                Mention(user_id) if not event.is_tome() else "",
                Text("生成二维码失败，请稍后重试"),
            ]
        )
        await msg_builder.finish()
    qr_img: BytesIO = generate_qrcode(login_data["url"])
    qrbind_buffer[user_id] = login_data
    qrbind_buffer[user_id]["bot_id"] = bot.self_id
    qrbind_buffer[user_id]["qr_img"] = qr_img
    qrbind_buffer[user_id]["target"] = extract_target(event)
    qrbind_buffer[user_id]["tome"] = event.is_tome()
    msg_builder = MessageFactory(
        [
            Image(qr_img),
            Text("\n"),
            Mention(user_id) if not event.is_tome() else "",
            Text(
                "\n请在3分钟内使用米游社扫码并确认进行绑定。\n注意：1.扫码即代表你同意将cookie信息授权给Bot使用\n2.扫码时会提示登录游戏，但不会挤掉账号\n3.其他人请不要乱扫，否则会将你的账号绑到TA身上！"
            ),
        ]
    )
    await msg_builder.finish()


@scheduler.scheduled_job("cron", second="*/10", misfire_grace_time=10)
async def check_qrcode():
    with contextlib.suppress(RuntimeError):
        for user_id, data in qrbind_buffer.items():
            logger.debug(f"Check qr result of {user_id}")
            tome: bool = data["tome"]
            try:
                mys_api = MysApi()
                status_data = await mys_api.check_login_qr(data)
                if status_data is None:
                    logger.warning(f"Check of user_id {user_id} failed")
                    msg_builder = MessageFactory(
                        [
                            Mention(user_id) if not tome else "",
                            Text("绑定二维码已失效，请重新发送扫码绑定指令"),
                        ]
                    )
                    target: PlatformTarget = data["target"]
                    bot = get_bot(self_id=data["bot_id"])
                    await msg_builder.send_to(target=target, bot=bot)
                    qrbind_buffer.pop(user_id)
                    continue
                logger.debug(status_data)
                if status_data["retcode"] != 0:
                    logger.debug(f"QR code of user_id {user_id} expired")
                    qrbind_buffer.pop(user_id)
                    msg_builder = MessageFactory(
                        [
                            Mention(user_id) if not tome else "",
                            Text("绑定二维码已过期，请重新发送扫码绑定指令"),
                        ]
                    )
                    target = data["target"]
                    bot = get_bot(self_id=data["bot_id"])
                    await msg_builder.send_to(target=target, bot=bot)
                    qrbind_buffer.pop(user_id)
                    continue
                if status_data["data"]["stat"] != "Confirmed":
                    continue
                logger.debug(f"QR code of user_id {user_id} confirmed")
                game_token = json.loads(status_data["data"]["payload"]["raw"])
                cookie_data = await mys_api.get_cookie_by_game_token(
                    int(game_token["uid"]), game_token["token"]
                )
                stoken_data = await mys_api.get_stoken_by_game_token(
                    int(game_token["uid"]), game_token["token"]
                )
                if not cookie_data or not stoken_data:
                    logger.debug(f"Get cookie and stoken failed of user_id {user_id}")
                    msg_builder = MessageFactory(
                        [
                            Mention(user_id) if not tome else "",
                            Text("获取cookie失败，请稍后重试"),
                        ]
                    )
                    target: PlatformTarget = data["target"]
                    bot = get_bot(self_id=data["bot_id"])
                    await msg_builder.send_to(target=target, bot=bot)
                    qrbind_buffer.pop(user_id)
                    continue
                mys_id = stoken_data["data"]["user_info"]["aid"]
                mid = stoken_data["data"]["user_info"]["mid"]
                cookie_token = cookie_data["data"]["cookie_token"]
                stoken = stoken_data["data"]["token"]["token"]
                device_id = qrbind_buffer[user_id]["device"]
                device_id, device_fp = await mys_api.init_device(device_id)
                mys_api = MysApi(
                    cookie=f"account_id={mys_id};cookie_token={cookie_token}",
                    device_id=device_id,
                    device_fp=device_fp,
                )
                game_info = await mys_api.call_mihoyo_api(
                    api="game_record",
                    mys_id=mys_id,

                )
                logger.debug(f"Game info: {game_info}")
                if game_info is None:
                    msg_builder = MessageFactory(
                        [
                            Mention(user_id) if not tome else "",
                            Text("获取游戏信息失败，请稍后重试"),
                        ]
                    )
                    logger.debug(f"Get game record failed of user_id {user_id}")
                elif isinstance(game_info, int):
                    msg_builder = MessageFactory(
                        [
                            Mention(user_id) if not tome else "",
                            Text(f"绑定失败，请稍后重试（错误代码 {game_info}）"),
                        ]
                    )
                    logger.debug(f"Get game record failed of user_id {user_id}")
                elif not game_info["list"]:
                    msg_builder = MessageFactory(
                        [
                            Mention(user_id) if not tome else "",
                            Text("该账号尚未绑定任何游戏，请确认扫码的账号无误"),
                        ]
                    )
                    logger.debug(f"No game record of user_id {user_id}")
                    logger.debug(f"No hsr game record of user_id {user_id}")
                else:
                    games = []
                    for game in game_info["list"]:
                        games.append({
                            "uid": game["game_role_id"],
                            "nickname": game["nickname"],
                            "game_id": game["game_id"],
                            "game_name": game["game_name"],
                            "region": game["region"],
                        })
                    logger.debug(f"Found game record of user_id {user_id}: {games}")
                    msg_builder = MessageFactory(
                        [
                            Mention(user_id) if not tome else "",
                            Text("登陆成功:\n"),
                        ]
                    )

                    for info in games:
                        msg_builder += MessageFactory(
                            [Text(f"{info['game_name']} ：{info['nickname']} ({info['uid']})\n")]
                        )
                        user = UserBind(
                            bot_id=data["bot_id"],
                            user_id=str(user_id),
                            mys_id=mys_id,
                            uid=info["uid"],
                            game=info['game_id'],
                            region=info['region'],
                            device_id=device_id,
                            device_fp=device_fp,
                            cookie=f"account_id={mys_id};cookie_token={cookie_token}",
                            stoken=(
                                f"stuid={mys_id};stoken={stoken};mid={mid};"
                                if stoken
                                else None
                            ),
                        )
                        print(user)
                        await set_user_bind(user)
                # send message to origin target
                target: PlatformTarget = data["target"]
                bot = get_bot(self_id=data["bot_id"])
                await msg_builder.send_to(target=target, bot=bot)
                qrbind_buffer.pop(user_id)
                logger.debug(f"Check of user_id {user_id} success")
                if not qrbind_buffer:
                    break
            except Exception as e:
                logger.warning(f"QR process error: {e}")
                logger.exception(e)
            finally:
                await asyncio.sleep(1)
