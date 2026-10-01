from pathlib import Path
import json
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import time
import hmac
import hashlib
import base64
import urllib.parse

from .logger import logger
from .simpleEncryption import decrypt
from .myRequests import get_request, post_request

config: dict = {}


# 读取配置文件
def read_config() -> bool:
    global config
    config_path = Path("./config/config.json")
    if not config_path.exists():
        logger.info("未配置外部通知，请检查配置文件！")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            message_types = config.get("ExternalNotificationEnabled")
            channels = message_types.split(",")
            logger.debug("配置文件读取成功！开始解密配置...")

            # 通道配置键映射表
            # str: 键名即是目标键名，默认值为空
            # tuple: (目标键, 来源键, 默认值)，来源键为 None 时等同于目标键
            CHANNEL_KEYS = {
                "SMTP": ["ExternalNotificationSmtpFrom", "ExternalNotificationSmtpTo",
                         "ExternalNotificationSmtpPassword", "ExternalNotificationSmtpServer",
                         "ExternalNotificationSmtpPort"],
                "DingTalk": ["ExternalNotificationDingTalkToken", "ExternalNotificationDingTalkSecret"],
                "Qmsg": ["ExternalNotificationQmsgServer", "ExternalNotificationQmsgKey",
                         "ExternalNotificationQmsgBot", "ExternalNotificationQmsgUser"],
                "pushplus_token": ["pushplus_token"],
                "Telegram": [("telegram_token", "ExternalNotificationTelegramBotToken", ""),
                             ("telegram_chat_id", "ExternalNotificationTelegramChatId", "")],
                "Lark": ["ExternalNotificationLarkWebhookUrl", "ExternalNotificationLarkID",
                         "ExternalNotificationLarkToken"],
                "WxPusher": ["ExternalNotificationWxPusherToken", "ExternalNotificationWxPusherUID"],
                "Discord": ["ExternalNotificationDiscordBotToken", "ExternalNotificationDiscordChannelId"],
                "DiscordWebhook": ["ExternalNotificationDiscordWebhookUrl", "ExternalNotificationDiscordWebhookName"],
                "ServerChan": ["ExternalNotificationServerChanKey"],
                "CustomWebhook": [("ExternalNotificationCustomWebhookUrl", None, ""),
                                  ("ExternalNotificationCustomWebhookContentType", None, "application/json"),
                                  ("ExternalNotificationCustomWebhookPayloadTemplate", None, '{"message": "{message}"}')],
                "OneBot": ["ExternalNotificationOneBotServer", "ExternalNotificationOneBotKey",
                           "ExternalNotificationOneBotUser"],
                "Email": ["ExternalNotificationEmailAccount", "ExternalNotificationEmailSecret"],
            }

            for channel in channels:
                for item in CHANNEL_KEYS.get(channel, []):
                    if isinstance(item, str):
                        target = source = item
                        default = ""
                    else:
                        target, source, default = item
                        if source is None:
                            source = target
                    if config.get(source, default) is None:
                        config[target] = ""
                    else:
                        config[target] = decrypt(config.get(source, default)).strip()
            logger.debug("配置文件解密成功！")
            return True
    except Exception:
        logger.exception("读取config配置失败，请检查配置文件！")
        return False


# 判断dict是否为空
def dictIsNoneOrEmpty(dp: dict) -> bool:
    return dp is None or len(dp) == 0 or dp == {} or bool(dp) is False or not dp


# 判断url是否合法
def is_valid_url(url: str) -> bool:
    """
    使用正则表达式验证URL是否有效
    Args:
        url (str): 需要验证的URL字符串
    Returns:
        bool: 如果URL有效返回True，否则返回False
    """
    # 定义URL的正则表达式模式
    url_pattern = re.compile(
        r"^https?://"  # http:// 或 https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # 域名
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP地址
        r"(?::\d+)?"  # 可选端口号
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )  # 路径部分

    return bool(url_pattern.match(url))


def is_valid_email(email: str) -> bool:
    """
    验证邮箱地址是否有效
    Args:
        email (str): 需要验证的邮箱地址
    Returns:
        bool: 如果邮箱有效返回True，否则返回False
    """
    # 定义邮箱的正则表达式模式
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    return bool(email_pattern.match(email))


# 通过smtp发送邮件
def send_email(dp: dict, title: str, text: str) -> bool:
    start = time.time()
    # 邮件配置
    send_email = dp.get("ExternalNotificationSmtpFrom")
    receiver_email = dp.get("ExternalNotificationSmtpTo")
    password = dp.get("ExternalNotificationSmtpPassword")
    smtp_server = dp.get("ExternalNotificationSmtpServer")
    smtp_port = dp.get("ExternalNotificationSmtpPort")

    if send_email and receiver_email and password and smtp_server and smtp_port:

        if not is_valid_email(send_email) or not is_valid_email(receiver_email):
            logger.info("邮件地址格式错误，请检查邮件配置文件！")
            return False

        # 创建邮件内容
        message = MIMEMultipart()
        message["From"] = send_email
        message["To"] = receiver_email
        message["Subject"] = "MaaGumballs:" + title

        # 添加邮件正文
        message.attach(MIMEText(text, "plain"))

        # 连接 SMTP 服务器并发送邮件
        try:
            # 使用 SMTP_SSL 建立安全连接
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            server.login(send_email, password)
            text = message.as_string()
            server.sendmail(send_email, receiver_email, text)
            server.quit()
            logger.info("邮件发送成功！")
            end = time.time()
            logger.debug(f"邮件发送耗时: {end - start}s")
            return True
        except Exception as e:
            logger.info(f"邮件发送失败: {e}")
            return False
    else:
        logger.info("邮件配置不完整，请检查邮件配置文件")
        return False


# 通过pushplus发送消息，暂时没用上
def send_byPushplus(dp: dict, title: str, text: str) -> bool:

    token = dp.get("pushplus_token")
    if token == None or token == "":
        logger.info("未配置pushplus_token")
        return False
    rootUrl = f"http://www.pushplus.plus/send?token={token}"
    title = "MaaGumballs:" + title
    request_url = rootUrl + "&title=" + title + "&content=" + text
    try:
        response = get_request(request_url)
        if response.get("status") == 200:
            if response.get("json")["code"] == 200:
                logger.info("消息推送成功")
                return True
            else:
                logger.info("消息推送失败")
                return False
        else:
            logger.error(f"消息推送失败，状态码：{response.get('status')}")
            return False
    except Exception as e:
        logger.info(f"pushplus发送失败：{e}")
        return False


# 通过Qmsg发送消息
def send_qmsg(dp: dict, title: str, text: str) -> bool:

    start = time.time()
    server = dp.get("ExternalNotificationQmsgServer")
    key = dp.get("ExternalNotificationQmsgKey")
    bot = dp.get("ExternalNotificationQmsgBot")
    user = dp.get("ExternalNotificationQmsgUser")

    if server:

        url = f"{ server }/jsend/{ key }"
        data = {"msg": text, "qq": user, "bot": bot}
        logger.debug(f"Qmsg_url：{url}")
        headers = {"Content-Type": "application/json"}
        try:
            if is_valid_url(url):
                response = post_request(url, data=data, headers=headers)
                if response.get("status") == 200:
                    if response.get("json")["code"] == 0:
                        logger.info("消息推送成功")
                        end = time.time()
                        logger.debug(f"消息发送耗时: {end - start}s")
                        return True
                    else:
                        logger.info(
                            "消息推送失败："
                            + response.get("json").get("reason", "未知错误")
                        )
                        return False
                else:
                    logger.error(f"消息推送失败，状态码：{ response.get('status') }")
                    return False
            else:
                logger.error("Qmsg URL 无效，请检查配置")
                return False
        except Exception as e:
            logger.error(f"Qmsg发送失败：{str(e)}")
            return False
    else:
        logger.info("Qmsg配置不完整，请检查配置文件")
        return False


def dingTalk_sign(timestamp: str, secret: str) -> str:
    """
    钉钉签名
    Args:
        timestamp(str): 时间戳
        secret(str): 密钥

    Returns:
        sign(str): 签名
    """
    secret_enc = secret.encode("utf-8")
    string_to_sign = "{}\n{}".format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode("utf-8")
    hmac_code = hmac.new(
        secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return sign


def send_dingTalk(dp: dict, title: str, text: str) -> bool:
    """
    发送钉钉消息
    Args:
        title(str): 标题
        text(str): 内容
    Returns:
        发送成功返回True，否则返回False
    """

    start = time.time()
    token = dp.get("ExternalNotificationDingTalkToken")
    secret = dp.get("ExternalNotificationDingTalkSecret")

    if not token:
        logger.error("钉钉配置不完整，请检查配置文件")
        return False
    else:
        url = f"https://oapi.dingtalk.com/robot/send?access_token={ token }"
        if secret:
            timestamp = str(round(time.time() * 1000))
            sign = dingTalk_sign(timestamp, secret)
            url = f"https://oapi.dingtalk.com/robot/send?access_token={ token }&timestamp={ timestamp }&sign={ sign }"

        headers = {"Content-Type": "application/json"}
        data = {"msgtype": "text", "text": {"content": text}}
        try:
            response = post_request(
                url, data=json.dumps(data).encode("utf-8"), headers=headers
            )
            if response.get("status") == 200:
                if response.get("json")["errmsg"] == "ok":
                    logger.info("消息推送成功")
                    end = time.time()
                    logger.debug(f"消息发送耗时: {end - start}s")
                    return True
                else:
                    logger.error(f"消息推送失败: { response.get('json')['errmsg'] }")
                    return False
            else:
                logger.error(f"消息推送失败，状态码：{ response.get('status') }")
                return False
        except Exception as e:
            logger.info(f"消息推送失败: { str(e) }")
            return False


def send_telegram(dp: dict, title, text: str) -> bool:
    """
    发送消息到 Telegram
    Args:
        title(str): 标题
        text(str): 内容
    Returns:
        发送成功返回True，否则返回False
    """
    start = time.time()
    bot_token = dp.get("telegram_token")
    chat_id = dp.get("telegram_chat_id")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        response = post_request(url, data={"chat_id": chat_id, "text": text})
        if response.get("status") == 200:
            logger.info("telegram消息推送成功")
            end = time.time()
            logger.debug(f"telegram消息发送耗时: {end - start}s")
            return True
        else:
            logger.error(f"消息推送失败，状态码：{response.get('status')}")
            return False
    except Exception as e:
        logger.error(f"发送 Telegram 消息失败: { str(e) }")
        return False


def lark_sign(timestamp: str, secret: str) -> str:
    """
    飞书签名
    Args:
        timestamp(str): 时间戳
        secret(str): 密钥

    Returns:
        sign(str): 签名
    """
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def send_lark(dp: dict, title: str, text: str) -> bool:
    """
    发送飞书(Lark)消息
    Args:
        dp(dict): 配置字典
        title(str): 标题
        text(str): 内容
    Returns:
        发送成功返回True，否则返回False
    """
    start = time.time()
    webhook_url = dp.get("ExternalNotificationLarkWebhookUrl")
    app_id = dp.get("ExternalNotificationLarkID")
    app_secret = dp.get("ExternalNotificationLarkToken")

    if not webhook_url and not app_id:
        logger.error("飞书配置不完整，请检查配置文件")
        return False

    headers = {"Content-Type": "application/json"}
    data = {"msg_type": "text", "content": {"text": text}}

    try:
        if webhook_url and is_valid_url(webhook_url):
            # 直接使用WebHook URL发送
            response = post_request(
                webhook_url, data=json.dumps(data).encode("utf-8"), headers=headers
            )
        elif app_id and app_secret:
            # 使用应用ID和签名发送
            timestamp = str(int(time.time()))
            sign = lark_sign(timestamp, app_secret)
            url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{app_id}?timestamp={timestamp}&sign={sign}"
            response = post_request(
                url, data=json.dumps(data).encode("utf-8"), headers=headers
            )
        else:
            logger.error("飞书配置不完整，请检查配置文件")
            return False

        if response.get("status") == 200:
            logger.info("飞书消息推送成功")
            end = time.time()
            logger.debug(f"飞书消息发送耗时: {end - start}s")
            return True
        else:
            logger.error(f"飞书消息推送失败，状态码：{response.get('status')}")
            return False
    except Exception as e:
        logger.error(f"发送飞书消息失败: {str(e)}")
        return False


def send_wxpusher(dp: dict, title: str, text: str) -> bool:
    """
    发送WxPusher(微信公众号)消息
    Args:
        dp(dict): 配置字典
        title(str): 标题
        text(str): 内容
    Returns:
        发送成功返回True，否则返回False
    """
    start = time.time()
    app_token = dp.get("ExternalNotificationWxPusherToken")
    uid = dp.get("ExternalNotificationWxPusherUID")

    if not uid:
        logger.error("WxPusher配置不完整，UID不能为空")
        return False

    headers = {"Content-Type": "application/json"}

    try:
        if app_token:
            # 普通推送：使用appToken和uid
            url = "https://wxpusher.zjiecode.com/api/send/message"
            payload = {
                "appToken": app_token,
                "content": text,
                "contentType": 1,
                "uids": [uid]
            }
            response = post_request(
                url, data=json.dumps(payload).encode("utf-8"), headers=headers
            )
        else:
            # 极简推送：uid作为SPT处理
            url = "https://wxpusher.zjiecode.com/api/send/message/simple-push"
            payload = {
                "content": text,
                "contentType": 1,
                "summary": text[:20] if len(text) > 20 else text,
                "spt": uid
            }
            response = post_request(
                url, data=json.dumps(payload).encode("utf-8"), headers=headers
            )

        if response.get("status") == 200:
            json_resp = response.get("json")
            if json_resp and json_resp.get("success", True):
                logger.info("WxPusher消息推送成功")
                end = time.time()
                logger.debug(f"WxPusher消息发送耗时: {end - start}s")
                return True

        logger.error(f"WxPusher消息推送失败，状态码：{response.get('status')}")
        return False
    except Exception as e:
        logger.error(f"发送WxPusher消息失败: {str(e)}")
        return False


def send_discord(dp: dict, title: str, text: str) -> bool:
    """
    发送Discord消息(通过Bot Token)
    Args:
        dp(dict): 配置字典
        title(str): 标题
        text(str): 内容
    Returns:
        发送成功返回True，否则返回False
    """
    start = time.time()
    bot_token = dp.get("ExternalNotificationDiscordBotToken")
    channel_id = dp.get("ExternalNotificationDiscordChannelId")

    if not bot_token or not channel_id:
        logger.error("Discord配置不完整，请检查配置文件")
        return False

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bot {bot_token}"
    }
    payload = {
        "content": text,
        "allowed_mentions": {"parse": ["users"]}
    }

    try:
        response = post_request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers
        )
        if response.get("status") == 200:
            logger.info("Discord消息推送成功")
            end = time.time()
            logger.debug(f"Discord消息发送耗时: {end - start}s")
            return True
        else:
            logger.error(f"Discord消息推送失败，状态码：{response.get('status')}")
            return False
    except Exception as e:
        logger.error(f"发送Discord消息失败: {str(e)}")
        return False


def send_discord_webhook(dp: dict, title: str, text: str) -> bool:
    """
    发送Discord Webhook消息
    Args:
        dp(dict): 配置字典
        title(str): 标题
        text(str): 内容
    Returns:
        发送成功返回True，否则返回False
    """
    start = time.time()
    webhook_url = dp.get("ExternalNotificationDiscordWebhookUrl")
    webhook_name = dp.get("ExternalNotificationDiscordWebhookName")

    if not webhook_url:
        logger.error("Discord Webhook配置不完整，URL不能为空")
        return False

    if not is_valid_url(webhook_url):
        logger.error("Discord Webhook URL无效，请检查配置")
        return False

    headers = {"Content-Type": "application/json"}
    payload = {
        "username": webhook_name if webhook_name else "Notifier",
        "content": text,
        "allowed_mentions": {"parse": ["users"]}
    }

    try:
        response = post_request(
            webhook_url, data=json.dumps(payload).encode("utf-8"), headers=headers
        )
        if response.get("status") == 200 or response.get("status") == 204:
            logger.info("Discord Webhook消息推送成功")
            end = time.time()
            logger.debug(f"Discord Webhook消息发送耗时: {end - start}s")
            return True
        else:
            logger.error(f"Discord Webhook消息推送失败，状态码：{response.get('status')}")
            return False
    except Exception as e:
        logger.error(f"发送Discord Webhook消息失败: {str(e)}")
        return False


def send_serverchan(dp: dict, title: str, text: str) -> bool:
    """
    发送ServerChan(Server酱)消息
    Args:
        dp(dict): 配置字典
        title(str): 标题
        text(str): 内容
    Returns:
        发送成功返回True，否则返回False
    """
    start = time.time()
    send_key = dp.get("ExternalNotificationServerChanKey")

    if not send_key:
        logger.error("ServerChan配置不完整，sendKey不能为空")
        return False

    try:
        # 判断 sendkey 是否以 "sctp" 开头并提取数字部分
        match = re.match(r"^sctp(\d+)t", send_key)
        if match:
            num = match.group(1)
            url = f"https://{num}.push.ft07.com/send/{send_key}.send"
        else:
            url = f"https://sctapi.ftqq.com/{send_key}.send"

        post_data = f"title={urllib.parse.quote('[MFA] Notification Service')}&desp={urllib.parse.quote(text)}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = post_request(
            url, data=post_data.encode("utf-8"), headers=headers
        )

        if response.get("status") == 200:
            logger.info("ServerChan消息推送成功")
            end = time.time()
            logger.debug(f"ServerChan消息发送耗时: {end - start}s")
            return True
        else:
            logger.error(f"ServerChan消息推送失败，状态码：{response.get('status')}")
            return False
    except Exception as e:
        logger.error(f"发送ServerChan消息失败: {str(e)}")
        return False


def send_custom_webhook(dp: dict, title: str, text: str) -> bool:
    """
    发送通用Webhook(CustomWebhook)消息
    Args:
        dp(dict): 配置字典
        title(str): 标题
        text(str): 内容
    Returns:
        发送成功返回True，否则返回False
    """
    start = time.time()
    webhook_url = dp.get("ExternalNotificationCustomWebhookUrl")
    content_type = dp.get("ExternalNotificationCustomWebhookContentType", "application/json")
    payload_template = dp.get("ExternalNotificationCustomWebhookPayloadTemplate", "")

    if not webhook_url:
        logger.error("通用Webhook URL不能为空")
        return False

    if not is_valid_url(webhook_url):
        logger.error("通用Webhook URL无效，请检查配置")
        return False

    try:
        # 处理payload模板，将{message}替换为实际消息
        if not payload_template:
            payload = json.dumps({"message": text})
        else:
            # 转义消息中的引号，再替换模板中的{message}
            escaped_text = text.replace('"', '\\"')
            payload = payload_template.replace("{message}", escaped_text)

        headers = {"Content-Type": content_type}
        response = post_request(
            webhook_url, data=payload.encode("utf-8"), headers=headers
        )

        if response.get("status") == 200:
            logger.info("通用Webhook消息推送成功")
            end = time.time()
            logger.debug(f"通用Webhook消息发送耗时: {end - start}s")
            return True
        else:
            logger.error(f"通用Webhook消息推送失败，状态码：{response.get('status')}")
            return False
    except Exception as e:
        logger.error(f"发送通用Webhook消息失败: {str(e)}")
        return False


def send_onebot(dp: dict, title: str, text: str) -> bool:
    """
    发送OneBot消息
    Args:
        dp(dict): 配置字典
        title(str): 标题
        text(str): 内容
    Returns:
        发送成功返回True，否则返回False
    """
    start = time.time()
    server_url = dp.get("ExternalNotificationOneBotServer")
    api_key = dp.get("ExternalNotificationOneBotKey")
    user_qq = dp.get("ExternalNotificationOneBotUser")

    if not server_url or not user_qq:
        logger.error("OneBot配置不完整，请检查配置文件")
        return False

    api_endpoint = f"{server_url}/send_msg"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "message": text,
        "user_id": user_qq
    }

    try:
        response = post_request(
            api_endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers
        )
        if response.get("status") == 200:
            json_resp = response.get("json")
            if json_resp and json_resp.get("status") == "ok":
                logger.info("OneBot消息推送成功")
                end = time.time()
                logger.debug(f"OneBot消息发送耗时: {end - start}s")
                return True

        logger.error(f"OneBot消息推送失败，状态码：{response.get('status')}")
        return False
    except Exception as e:
        logger.error(f"发送OneBot消息失败: {str(e)}")
        return False


def send_email_auto(dp: dict, title: str, text: str) -> bool:
    """
    通过自动检测SMTP配置发送邮件(对应C#的Email通道)
    根据邮箱域名自动选择SMTP服务器
    Args:
        dp(dict): 配置字典
        title(str): 标题
        text(str): 内容
    Returns:
        发送成功返回True，否则返回False
    """
    start = time.time()
    email = dp.get("ExternalNotificationEmailAccount")
    password = dp.get("ExternalNotificationEmailSecret")

    if not email or not password:
        logger.error("邮件配置不完整，请检查配置文件")
        return False

    if not is_valid_email(email):
        logger.error("邮箱地址格式错误，请检查邮件配置文件")
        return False

    # 根据邮箱域名自动选择SMTP配置
    domain = email.split("@")[1].lower().strip()
    smtp_configs = {
        "qq.com": ("smtp.qq.com", 465, True),
        "163.com": ("smtp.163.com", 994, True),
        "gmail.com": ("smtp.gmail.com", 465, True),
        "outlook.com": ("smtp-mail.outlook.com", 587, False),
        "hotmail.com": ("smtp-mail.outlook.com", 587, False),
        "126.com": ("smtp.126.com", 994, True),
        "yeah.net": ("smtp.yeah.net", 994, True),
        "sina.com": ("smtp.sina.com", 465, True),
        "sohu.com": ("smtp.sohu.com", 465, True),
        "aliyun.com": ("smtp.aliyun.com", 465, True),
    }

    smtp_config = smtp_configs.get(domain)
    if not smtp_config:
        logger.error(f"不支持的邮箱服务: {domain}")
        return False

    smtp_server, smtp_port, use_ssl = smtp_config

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()

        server.login(email, password)

        message = MIMEMultipart()
        message["From"] = email
        message["To"] = email
        message["Subject"] = "MaaGumballs:" + title
        message.attach(MIMEText(text, "plain"))

        server.sendmail(email, email, message.as_string())
        server.quit()

        logger.info("邮件发送成功！")
        end = time.time()
        logger.debug(f"邮件发送耗时: {end - start}s")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False


def send_message(title: str, text: str) -> bool:
    """
    发送消息的主函数
    Args:
        title(str): 消息标题
        text(str): 消息内容
    Returns:
        发送成功返回True，否则返回False
    """
    global config
    if dictIsNoneOrEmpty(config):
        logger.info("读取外部配置文件")
        read_config()
    if config.get("ExternalNotificationEnabled", False) is False:
        logger.info("未配置外部通知，请检查配置文件！")
        return False

    # 渠道分发映射表
    SEND_FUNCS = {
        "SMTP": send_email,
        "pushplus": send_byPushplus,
        "Qmsg": send_qmsg,
        "DingTalk": send_dingTalk,
        "Telegram": send_telegram,
        "Lark": send_lark,
        "WxPusher": send_wxpusher,
        "Discord": send_discord,
        "DiscordWebhook": send_discord_webhook,
        "ServerChan": send_serverchan,
        "CustomWebhook": send_custom_webhook,
        "OneBot": send_onebot,
        "Email": send_email_auto,
    }

    channels = config["ExternalNotificationEnabled"].split(",")
    for channel in channels:
        if not channel:
            logger.info("未配置消息发送，请检查配置文件！")
            return False
        send_func = SEND_FUNCS.get(channel)
        if not send_func:
            logger.info("未配置消息类型或暂不支持此消息类型！")
            return False
        send_func(config, title, text=text)
    return True
