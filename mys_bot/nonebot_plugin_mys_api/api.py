import json
import time
import uuid
import random
import string
import hashlib
from copy import deepcopy
from typing import Any, Union, Literal, Optional

from nonebot import get_driver
from nonebot.log import logger
from nonebot.drivers import Driver, Request, HTTPClientMixin

from .config import plugin_config

RECOGNIZE_SERVER = {
    "1": "prod_gf_cn",
    "2": "cn_gf01",
    "5": "cn_qd01",
    # '6': 'os_usa',
    # '7': 'os_euro',
    # '8': 'os_asia',
    # '9': 'os_cht',
}

OLD_URL = "https://api-takumi.mihoyo.com"
NEW_URL = "https://api-takumi-record.mihoyo.com"
HK4_SDK_URL = "https://hk4e-sdk.mihoyo.com"
TAKUMI_HOST = "https://api-takumi.mihoyo.com"
PASSPORT_HOST = "https://passport-api.mihoyo.com"
PUBLIC_DATA_HOST = "https://public-data-api.mihoyo.com"
NEW_BBS_URL = "https://bbs-api.miyoushe.com"
WEBSTATIC_URL = "https://webstatic.mihoyo.com"
APP_URL = "https://app.mihoyo.com/"

# 米游社
GAME_RECORD_API = f"{NEW_URL}/game_record/card/wapi/getGameRecordCard"  # 游戏记录
GET_FP_API = f"{PUBLIC_DATA_HOST}/device-fp/api/getFp"  # device_fp

# AuthKey
GET_TOKENS_BY_LT_API = (
    f"{OLD_URL}/auth/api/getMultiTokenByLoginTicket"  # 通过login_ticket获取tokens
)
GET_COOKIE_BY_STOKEN_API = (
    f"{OLD_URL}/auth/api/getCookieAccountInfoBySToken"  # 通过stoken获取cookie
)
CREATE_QRCODE_API = f"{HK4_SDK_URL}/hk4e_cn/combo/panda/qrcode/fetch"  # 创建登录qrcode
CHECK_QRCODE_API = (
    f"{HK4_SDK_URL}/hk4e_cn/combo/panda/qrcode/query"  # 检查qrcode扫描状态
)
GET_COOKIE_BY_GAME_TOKEN_API = f"{TAKUMI_HOST}/auth/api/getCookieAccountInfoByGameToken"  # 通过game_token获取cookie
GET_STOKEN_BY_GAME_TOKEN_API = f"{PASSPORT_HOST}/account/ma-cn-session/app/getTokenByGameToken"  # 通过game_token获取stoken

# 崩坏：星穹铁道
STAR_RAIL_APP = f"{NEW_URL}/game_record/app"
STAR_RAIL_INDEX_API = f"{STAR_RAIL_APP}/hkrpg/api/index"  # 崩坏：星穹铁道角色橱窗信息
STAR_RAIL_AVATAR_INFO_API = (
    f"{STAR_RAIL_APP}/hkrpg/api/avatar/info"  # 崩坏：星穹铁道角色详细信息
)
STAR_RAIL_WIDGET_API = f"{STAR_RAIL_APP}/hkrpg/aapi/widget"  # 崩坏：星穹铁道桌面组件
STAR_RAIL_NOTE_API = f"{STAR_RAIL_APP}/hkrpg/api/note"  # 崩坏：星穹铁道实时便笺
STAR_RAIL_MONTH_INFO_API = (
    f"{OLD_URL}/event/srledger/month_info"  # 崩坏：星穹铁道开拓月历
)
SIGN_API = f"{OLD_URL}/event/luna/sign"
ZZZ_SIGN_URL = "https://act-nap-api.mihoyo.com/event/luna/zzz/sign"
# Unknown function API
BBS_VERIFICATION_API = (
    f"{NEW_BBS_URL}/game_record/app/card/wapi/createVerification?is_high=false"
)
SR_VERIFICATION_API = f"{STAR_RAIL_APP}/card/wapi/createVerification?is_high=false"
SR_VERIFY_API = f"{STAR_RAIL_APP}/card/wapi/verifyVerification"

APP_VERSION = "2.70.1"
TOOL_VERSION = "v2.1.2"
USER_AGENT = (
        "Mozilla/5.0 (Linux; Android 12; IN2025 Build/V417IR; wv) "
        + "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
        + f"Chrome/83.0.4103.120 Mobile Safari/537.36 miHoYoBBS/{APP_VERSION}"
)


def md5(text: str) -> str:
    """
    md5
    """
    md5_ = hashlib.md5()
    md5_.update(text.encode())
    return md5_.hexdigest()


def random_hex(length: int) -> str:
    """
    生成指定长度的随机16进制字符串
    """
    result = hex(random.randint(0, 16 ** length)).replace("0x", "").upper()
    if len(result) < length:
        result = "0" * (length - len(result)) + result
    return result


def random_text(length: int) -> str:
    """
    生成指定长度的随机字符串
    """
    return "".join(random.sample(string.ascii_lowercase + string.digits, length))


class MysApi:
    driver: HTTPClientMixin
    cookie: Optional[str]
    device_id: Optional[str]
    device_fp: Optional[str]

    def __init__(
            self,
            cookie: Optional[str] = None,
            device_id: Optional[str] = None,
            device_fp: Optional[str] = None,
    ) -> None:
        driver: Driver = get_driver()
        if not isinstance(driver, HTTPClientMixin):
            raise RuntimeError(
                f"当前驱动配置 {driver} 无法进行 HTTP 请求，请在 DRIVER 配置项末尾添加 +~httpx"
            )
        self.driver = driver
        self.cookie = cookie
        self.device_id = device_id
        self.device_fp = device_fp

    async def init_device(self, device_id: Optional[str] = None) -> tuple[str, str]:
        self.device_id = device_id if device_id is not None else str(uuid.uuid4())
        self.device_fp = await self.get_fp(self.device_id)
        return self.device_id, self.device_fp

    async def generate_headers(
            self,
            q: Optional[str] = None,
            b: Optional[dict[str, Any]] = None,
            p: Optional[str] = None,
            r: Optional[str] = None,
            is_ds2: bool = False,
    ) -> dict[str, str]:
        """
        生成米游社headers
            :param q: 查询
            :param b: 请求体
            :param p: x-rpc-page
            :return: headers
        """
        if is_ds2:
            ds = self.get_ds(q, b, is_ds2=True)
        else:
            ds = self.get_ds(q, b)
        result = {
            "DS": ds,
            "cookie": self.cookie,
            "Origin": (WEBSTATIC_URL if not is_ds2 else "https://app.mihoyo.com/"),
            "Referer": (
                r if r else (WEBSTATIC_URL if not is_ds2 else "https://app.mihoyo.com/")
            ),
            "User-Agent": USER_AGENT,
            "x-rpc-page": p if p else "",
            "x-rpc-platform": "5",
            "x-rpc-client_type": "5" if not is_ds2 else "2",
            "x-rpc-device_name": "OnePlus%20IN2025",
            "x-rpc-device_model": "14Pro",
            "x-rpc-device_id": self.device_id,
            "x-rpc-device_fp": self.device_fp,
            "x-rpc-sys_version": "12",
            "x-rpc-tool_verison": TOOL_VERSION,
            "x-rpc-app_version": APP_VERSION,
        }
        return result

    def get_ds(
            self,
            query: Optional[str] = None,
            body: Optional[dict[str, Any]] = None,
            is_ds2: bool = False,
    ) -> str:
        """
        生成米游社headers的ds_token

        :param query: 查询
        :param body: 请求体
        :param ds2: 是否使用ds2
        :return: ds_token
        """
        q = query if query else ""
        b = json.dumps(body) if body else ""
        if is_ds2:
            salt = "t0qEgfub6cvueAPgR5m9aQWWVciEer7v"  # 6X
        else:
            salt = "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs"  # 4X
        t = str(int(time.time()))
        r = str(random.randint(100000, 200000))
        s = f"salt={salt}&t={t}&r={r}&b={b}&q={q}"
        c = md5(s)
        return f"{t},{r},{c}"

    async def get_fp(self, device_id: str):
        headers = {
            "User-Agent": USER_AGENT,
            "x-rpc-client_type": "5",
            "x-rpc-app_version": APP_VERSION,
            "Referer": WEBSTATIC_URL,
            "Origin": WEBSTATIC_URL,
        }
        request = Request(
            "POST",
            GET_FP_API,
            params={
                "device_id": device_id,
                "seed_id": random_hex(16).lower(),
                "seed_time": str(round(time.time() * 1000)),
                "platform": "5",
                "device_fp": random_hex(13).lower(),
                "app_name": "account_cn",
                "ext_fields": f"{{\"userAgent\":\"{headers['User-Agent']}\",\"browserScreenSize\":329280,\"maxTouchPoints\":5,\"isTouchSupported\":true,\"browserLanguage\":\"zh-CN\",\"browserPlat\":\"Linux i686\",\"browserTimeZone\":\"Asia/Shanghai\",\"webGlRender\":\"Adreno (TM) 640\",\"webGlVendor\":\"Qualcomm\",\"numOfPlugins\":0,\"listOfPlugins\":\"unknown\",\"screenRatio\":3.75,\"deviceMemory\":\"4\",\"hardwareConcurrency\":\"4\",\"cpuClass\":\"unknown\",\"ifNotTrack\":\"unknown\",\"ifAdBlock\":0,\"hasLiedResolution\":1,\"hasLiedOs\":0,\"hasLiedBrowser\":0}}",
            },
            timeout=10,
        )
        response = await self.driver.request(request)
        try:
            data = json.loads(response.content or "{}")
            return str(data["data"]["device_fp"])
        except (json.JSONDecodeError, KeyError):
            logger.warning("Failed to get device fp, use random")
            logger.warning(f"Response: {response.status_code} {response.content}")
            return random_hex(13).lower()

    async def _pass(
            self, gt: str, challenge: str, headers: dict[str, str]
    ) -> tuple[Optional[str], Optional[str]]:
        # For test only
        if plugin_config.magic_api:
            url = f"{plugin_config.magic_api}&gt={gt}&challenge={challenge}"
            request = Request(
                "GET",
                url,
                headers=headers,
                timeout=10,
            )
            response = await self.driver.request(request)
            try:
                data = json.loads(response.content or "{}")
                logger.debug(f"Pass data: {data}")
                validate = data["data"]["validate"]
                challenge = data["data"]["challenge"]
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Pass API failed: {e}")
                validate = None
        else:
            validate = None
        return validate, challenge

    async def _validate(self, headers: dict[str, str], challenge: str, validate: str):
        data = {
            "geetest_challenge": challenge,
            "geetest_validate": validate,
            "geetest_seccode": f"{validate}|jordan",
        }
        headers["DS"] = self.get_ds("", data)
        request = Request(
            "POST",
            SR_VERIFY_API,
            headers=headers,
            json=data,
            timeout=10,
        )
        response = await self.driver.request(request)
        logger.debug(f"Validate info: {response.content}")

    async def _upass(self, headers: dict[str, str], is_bbs: bool = False) -> str:
        logger.info("Start upass")
        raw_data = await self.get_upass_link(headers, is_bbs)
        if raw_data is None:
            logger.warning("Get upass link failed")
            return ""
        try:
            gt = raw_data["data"]["gt"]
            challenge = raw_data["data"]["challenge"]
            validate, challenge = await self._pass(gt, challenge, headers)
            if validate and challenge:
                await self._validate(headers, challenge, validate)
                logger.info(f"Challenge upass: {challenge}")
                return challenge
            logger.warning("Get upass validate failed")
            return ""
        except (json.JSONDecodeError, KeyError):
            logger.warning("Process upass failed")
            return ""

    async def get_upass_link(
            self, headers: dict[str, str], is_bbs: bool = False
    ) -> Optional[dict]:
        headers["DS"] = self.get_ds("is_high=false")
        request = Request(
            "GET",
            BBS_VERIFICATION_API if is_bbs else SR_VERIFICATION_API,
            headers=headers,
            timeout=10,
        )
        response = await self.driver.request(request)
        try:
            data = json.loads(response.content or "{}")
            return data
        except (json.JSONDecodeError, KeyError):
            return None

    async def get_stoken_by_login_ticket(self, login_ticket: str, mys_id: str):
        request = Request(
            "GET",
            GET_TOKENS_BY_LT_API,
            headers={
                "User-Agent": USER_AGENT,
                "x-rpc-client_type": "5",
                "x-rpc-app_version": APP_VERSION,
                "Referer": WEBSTATIC_URL,
                "Origin": WEBSTATIC_URL,
            },
            params={
                "login_ticket": login_ticket,
                "token_types": "3",
                "uid": mys_id,
            },
            timeout=10,
        )
        response = await self.driver.request(request)
        try:
            data = json.loads(response.content or "{}")
            return data["data"]["list"][0]["token"]
        except (json.JSONDecodeError, KeyError):
            return None

    async def get_cookie_token_by_stoken(self, stoken: str, mys_id: str):
        request = Request(
            "GET",
            GET_COOKIE_BY_STOKEN_API,
            headers={
                "User-Agent": USER_AGENT,
                "x-rpc-client_type": "5",
                "x-rpc-app_version": APP_VERSION,
                "Referer": WEBSTATIC_URL,
                "Origin": WEBSTATIC_URL,
                "Cookie": f"stuid={mys_id};stoken={stoken}",
            },
            params={"uid": mys_id, "stoken": stoken},
            timeout=10,
        )
        response = await self.driver.request(request)
        try:
            data = json.loads(response.content or "{}")
            return data["data"]["cookie_token"]
        except (json.JSONDecodeError, KeyError):
            logger.warning("Failed to get cookie token by stoken")
            logger.warning(f"Response: {response.status_code} {response.content}")
            return None

    async def get_cookie_by_game_token(self, uid: int, game_token: str):
        request = Request(
            "GET",
            GET_COOKIE_BY_GAME_TOKEN_API,
            params={"game_token": game_token, "account_id": uid},
            timeout=10,
        )
        response = await self.driver.request(request)
        try:
            return json.loads(response.content or "{}")
        except json.JSONDecodeError:
            logger.warning("Failed to get cookie by game token")
            logger.warning(f"Response: {response.status_code} {response.content}")
            return None

    async def get_stoken_by_game_token(self, uid: int, game_token: str):
        params = {"account_id": uid, "game_token": game_token}
        headers = {
            "DS": self.get_ds(body=params),
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-rpc-aigis": "",
            "x-rpc-app_id": "bll8iq97cem8",
            "x-rpc-game_biz": "bbs_cn",
            "x-rpc-sys_version": "12",
            "x-rpc-device_name": "OnePlus%20IN2025",
            "x-rpc-device_model": "14Pro",
        }
        request = Request(
            "POST",
            GET_STOKEN_BY_GAME_TOKEN_API,
            headers=headers,
            params=params,
            timeout=10,
        )
        response = await self.driver.request(request)
        try:
            return json.loads(response.content or "{}")
        except json.JSONDecodeError:
            logger.warning("Failed to get stoken by game stoken")
            logger.warning(f"Response: {response.status_code} {response.content}")
            return None

    async def create_login_qr(self, app_id: int):
        """
        创建登录二维码
        app_id:
            1-崩坏3, 2-未定事件簿, 4-原神, 5-平台应用, 7-崩坏学园2,
            8-星穹铁道, 9-云游戏, 10-3NNN, 11-PJSH, 12-绝区零, 13-HYG
        """
        device = str(uuid.uuid4())
        params = {"app_id": str(app_id), "device": device}
        request = Request(
            "GET",
            CREATE_QRCODE_API,
            params=params,
            timeout=10,
        )
        response = await self.driver.request(request)
        try:
            data = json.loads(response.content or "{}")
            url = data["data"]["url"]
            ticket = url.split("ticket=")[1]
            ret_data = {
                "app_id": app_id,
                "ticket": ticket,
                "device": device,
                "url": url,
            }
            return ret_data
        except (json.JSONDecodeError, KeyError):
            return None

    async def check_login_qr(self, login_data: dict[str, Any]):
        try:
            assert "app_id" in login_data
            assert "ticket" in login_data
            assert "device" in login_data
        except AssertionError as e:
            logger.warning(f"Check QR error: {e}")
            return None
        request = Request(
            "GET",
            CHECK_QRCODE_API,
            params={
                "app_id": login_data["app_id"],
                "ticket": login_data["ticket"],
                "device": login_data["device"],
            },
            timeout=10,
        )
        response = await self.driver.request(request)
        try:
            return json.loads(response.content or "{}")
        except json.JSONDecodeError as e:
            logger.warning(f"Check QR error: {e}")
            return None

    async def get_game_basic_info(
            self, role_uid: str, mys_id: str, game_id: str = "6"
    ) -> Union[dict, int, None]:
        game_record = await self.call_mihoyo_api(
            api="game_record", role_uid=role_uid, mys_id=mys_id
        )
        if not isinstance(game_record, dict):
            return game_record
        game_record_list = game_record.get("list", [])
        for game in game_record_list:
            if (
                    str(game.get("game_id", "")) == game_id
                    and game.get("game_role_id", "") == role_uid
            ):
                return game
        logger.warning(f"Game record not found for {role_uid=} in {game_record_list}")
        return None

    async def request(
            self,
            method: Literal["GET", "POST"],
            url: str,
            headers: dict[str, str],
            params: Optional[dict[str, Any]] = None,
            body: Optional[dict[str, Any]] = None,
    ):
        if method == "POST":
            request = Request(
                "POST",
                url,
                headers=headers,
                json=body,
                timeout=10,
            )
        else:
            request = Request(
                "GET",
                url,
                headers=headers,
                params=params,
                timeout=10,
            )
        response = await self.driver.request(request)
        try:
            data = json.loads(response.content or "{}")
        except json.JSONDecodeError:
            logger.warning("API call failed")
            logger.warning(f"Response: {response.status_code} {response.content}")
            data = None
        return data

    async def call_mihoyo_api(
            self,
            api: Literal[
                "game_record",
                "sr_widget",
                "bh3_sign",
                "gs_sign",
                "sr_sign",
                "zzz_sign",
            ],
            region: str = "",
            role_uid: str = "0",
            extra_headers: Optional[dict[str, Any]] = None,
            **kwargs,
    ) -> Union[dict, int, None]:
        # cookie check
        if not self.cookie:
            return None
        # request params
        # fill params by api, or keep empty to use default params
        # default params: uid, server_id, role_id
        params: Optional[dict[str, Any]] = None
        params_str: Optional[str] = None
        body: Optional[dict[str, Any]] = None
        page: str = ""
        headers: dict[str, str] = {}
        refer: str = ""
        # flags
        is_ds2 = False
        is_post = False
        # fill headers and params by api
        if api == "game_record":
            # extra params: mys_id
            mys_id = kwargs.get("mys_id", None)
            if not mys_id:
                raise ValueError("mys_id is required for game_record api")
            url = GAME_RECORD_API  # 游戏记录
            params = {"uid": mys_id}
            params_str = f"uid={mys_id}"
        elif api == "sr_widget":
            url = STAR_RAIL_WIDGET_API
            params = {}
            params_str = ""
            is_ds2 = True
            page = f"{TOOL_VERSION}_#/rpg"
        elif api == "bh3_sign":
            url = SIGN_API
            body = {
                "act_id": "e202306201626331",
                "region": region,
                "uid": role_uid,
                "lang": "zh-cn",
            }
            is_post = True
            is_ds2 = True
        elif api == "gs_sign":
            url = SIGN_API
            body = {
                "act_id": "e202311201442471",
                "region": region,
                "uid": role_uid,
                "lang": "zh-cn",
            }
            is_post = True
            is_ds2 = True
            refer = WEBSTATIC_URL
        elif api == "sr_sign":
            url = SIGN_API
            body = {
                "act_id": "e202304121516551",
                "region": region,
                "uid": role_uid,
                "lang": "zh-cn",
            }
            is_post = True
            is_ds2 = True
            refer = WEBSTATIC_URL
        elif api == "zzz_sign":
            url = ZZZ_SIGN_URL
            body = {
                "act_id": "e202406242138391",
                "region": region,
                "uid": role_uid,
                "lang": "zh-cn",
            }
            is_post = True
            is_ds2 = True
            refer = WEBSTATIC_URL
        else:  # api not found
            return None
        logger.debug(f"Mys API call: {api}")
        logger.debug(f"URL: {url}")
        if url is not None:  # send request
            if not is_post:
                # get server_id by role_uid
                server_id = RECOGNIZE_SERVER.get(role_uid[0])
                # fill deault params
                if params_str is None:
                    params_str = (
                        "&".join([f"{k}={v}" for k, v in params.items()])
                        if params
                        else ""
                    )
                    params_fixed = f"role_id={role_uid}&server={server_id}"
                    params_str = (
                        f"{params_str}&{params_fixed}" if params_str else params_fixed
                    )
                if params is None:
                    params = {"role_id": role_uid, "server": server_id}
            # generate headers
            if not headers:
                headers = await self.generate_headers(
                    q=params_str,
                    b=body,
                    p=page,
                    r=refer,
                    is_ds2=is_ds2,
                )
                if extra_headers:
                    headers.update(extra_headers)
            data = await self.request(
                "POST" if is_post else "GET",
                url=url,
                headers=headers,
                params=params,
                body=body,
            )
        else:  # url is None
            return None
        # debug log
        # parse data
        times_try = 0
        new_id = None
        new_fp = None
        while data is not None:
            retcode = None
            try:
                retcode = int(data["retcode"])
                risk_code = data["data"].get("risk_code") if data.get("data") else None
                if risk_code and plugin_config.magic_api is not None:
                    logger.warning(f"Mys API {api} risk 5001: {data}")
                    logger.debug(f"with headers: {headers}")
                    times_try += 1
                    gt = data["data"].get("gt")
                    challenge = data["data"].get("challenge")
                    validate, challenge = await self._pass(gt, challenge, headers)
                    if validate is None or challenge is None:
                        break
                    await self._validate(headers, challenge, validate)
                    logger.info(f"Challenge upass: {challenge}")
                    headers["x-rpc-challenge_game"] = "6"
                    headers["x-rpc-challenge"] = challenge
                    data = await self.request(
                        "POST" if is_post else "GET",
                        url=url,
                        headers=headers,
                        params=params,
                        body=body,
                    )
                elif (
                        retcode in {1034, 5003, 10035, 10041}
                        and plugin_config.magic_api is not None
                ):
                    logger.warning(f"Mys API {api} code {retcode}: {data}")
                    logger.debug(f"with headers: {headers}")
                    times_try += 1
                    new_id, new_fp = await self.init_device()
                    headers["x-rpc-device_fp"] = new_fp
                    headers["x-rpc-challenge_game"] = "6"
                    headers["x-rpc-page"] = f"{TOOL_VERSION}_#/rpg"
                    challenge = await self._upass(deepcopy(headers))
                    headers["x-rpc-challenge"] = challenge
                    data = await self.request(
                        "POST" if is_post else "GET",
                        url=url,
                        headers=headers,
                        params=params,
                        body=body,
                    )
                elif retcode != 0:
                    logger.warning(f"Mys API {api} failed: {data}")
                    logger.debug(f"with headers: {headers}")
                    logger.debug(f"with params: {params}")
                    data = retcode
                    break
                else:
                    logger.debug(f"Mys API {api} response: {data}")
                    data = dict(data["data"])
                    if new_fp:
                        data["new_fp"] = new_fp
                    if new_id:
                        data["new_id"] = new_id
                    break
            except (json.JSONDecodeError, KeyError):
                data = None
                break
            if times_try > 1:
                logger.warning(f"All try failed of API {api}")
                if retcode is not None:
                    data = retcode
                break
        if data is None:
            logger.warning(f"Mys API {api} error")
        return data
