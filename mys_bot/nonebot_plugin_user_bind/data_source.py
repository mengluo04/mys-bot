from io import BytesIO

import qrcode
from sqlalchemy import select, update
from nonebot_plugin_orm import get_session

from .model import UserBind


async def set_user_bind(user: UserBind) -> None:
    print(user)
    select_user = await get_user_bind(user.bot_id, user.user_id, user.game)
    update_flag = False
    for old_user in select_user:
        if user.user_id != "0":
            # not public user
            if user.uid != old_user.uid:
                # delete origin user
                async with get_session() as session:
                    await session.delete(old_user)
                    await session.commit()
            else:
                # update user
                statement = (
                    update(UserBind)
                    .where(UserBind.bot_id == user.bot_id)
                    .where(UserBind.user_id == user.user_id)
                    .where(UserBind.uid == user.uid)
                    .where(UserBind.game == user.game)
                    .values(mys_id=user.mys_id)
                    .values(device_id=user.device_id)
                    .values(device_fp=user.device_fp)
                    .values(cookie=user.cookie)
                    .values(stoken=user.stoken)
                )
                async with get_session() as session:
                    await session.execute(statement)
                    await session.commit()
                update_flag = True
        else:
            # public user
            if user.cookie == old_user.cookie:
                statement = (
                    update(UserBind)
                    .where(UserBind.bot_id == user.bot_id)
                    .where(UserBind.user_id == user.user_id)
                    .where(UserBind.uid == user.uid)
                    .where(UserBind.game == user.game)
                    .values(mys_id=user.mys_id)
                    .values(device_id=user.device_id)
                    .values(device_fp=user.device_fp)
                    .values(cookie=user.cookie)
                    .values(stoken=user.stoken)
                )
                async with get_session() as session:
                    await session.execute(statement)
                    await session.commit()
                update_flag = True
    if not update_flag:
        async with get_session() as session:
            session.add(user)
            await session.commit()


async def del_user_bind(bot_id: str, user_id: str, uid: str, game: str) -> None:
    select_user = await get_user_bind(bot_id, user_id, game)
    select_uid = [user.uid for user in select_user]
    if uid in select_uid:
        user = select_user[select_uid.index(uid)]
        async with get_session() as session:
            await session.delete(user)
            await session.commit()


async def get_user_bind(bot_id: str, user_id: str, game: str) -> list[UserBind]:
    statement = (
        select(UserBind)
        .where(UserBind.bot_id == bot_id)
        .where(UserBind.user_id == user_id)
        .where(UserBind.game == game)
    )
    async with get_session() as session:
        records = (await session.scalars(statement)).all()
    return list(records)


def generate_qrcode(url: str) -> BytesIO:
    qr = qrcode.QRCode(  # type: ignore
        version=1, error_correction=qrcode.ERROR_CORRECT_L, box_size=10, border=4
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio)
    return bio
