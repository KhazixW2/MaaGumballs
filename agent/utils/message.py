from pathlib import Path
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

from .logger import logger
from .simpleEncryption import decrypt

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
            return True
    except Exception:
        logger.exception("读取config配置失败，请检查配置文件！")
        return False


# 判断dict是否为空
def dictIsNoneOrEmpty(dp: dict) -> bool:
    return dp is None or len(dp) == 0 or dp == {} or bool(dp) is False or not dp


# 通过smtp发送邮件
def send_email(dp: dict, title: str, text: str) -> bool:
    # 邮件配置
    send_email = dp.get("ExternalNotificationSmtpFrom")
    receiver_email = dp.get("ExternalNotificationSmtpTo")
    password = dp.get("ExternalNotificationSmtpPassword")
    smtp_server = dp.get("ExternalNotificationSmtpServer")
    smtp_port = dp.get("ExternalNotificationSmtpPort")

    if send_email and receiver_email and password and smtp_server and smtp_port:
        # 解密邮件配置
        send_email = decrypt(send_email)
        receiver_email = decrypt(receiver_email)
        password = decrypt(password)
        smtp_server = decrypt(smtp_server)
        smtp_port = decrypt(smtp_port)

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
        response = requests.get(request_url)
        if response.status_code == 200:
            if response.json()["code"] == 200:
                logger.info("消息推送成功")
                return True
            else:
                logger.info("消息推送失败")
                return False
        else:
            logger.error("消息推送失败")
            return False
    except Exception as e:
        logger.info(f"pushplus发送失败：{e}")
        return False


# 通过Qmsg发送消息
def send_qmsg(dp: dict, title: str, text: str) -> bool:
    server = dp.get("ExternalNotificationQmsgServer")
    key = dp.get("ExternalNotificationQmsgKey")
    bot = dp.get("ExternalNotificationQmsgBot")
    user = dp.get("ExternalNotificationQmsgUser")

    if server and key and bot and user:
        server = decrypt(server)
        key = decrypt(key)
        bot = decrypt(bot)
        user = decrypt(user)

        url = f"https://qmsg.zendee.cn/send/{key}"
        data = {"msg": text, "qq": user, "bot": bot}
        response = requests.post(url, data=data)
        if response.status_code == 200:
            if response.json()["code"] == 0:
                logger.info("消息推送成功")
                return True
            else:
                logger.info(
                    "消息推送失败：" + response.json().get("reason", "未知错误")
                )
                return False
        else:
            logger.error("消息推送失败")
            return False
    else:
        logger.info("Qmsg配置不完整，请检查配置文件")


def send_message(title: str, text: str) -> bool:
    """
    # 发送消息的主函数
    # title: 消息标题
    # text: 消息内容
    """
    global config
    if dictIsNoneOrEmpty(config):
        logger.info("读取外部配置文件")
        read_config()
    if config.get("ExternalNotificationEnabled", False) is False:
        logger.info("未配置外部通知，请检查配置文件！")
        return False

    message_types = config.get("ExternalNotificationEnabled")
    list = message_types.split(",")
    for message_type in list:
        if message_type:
            if message_type == "SMTP":
                send_email(config, title, text=text)
            elif message_type == "pushplus":
                send_byPushplus(config, title, text=text)
            elif message_type == "Qmsg":
                send_qmsg(config, title, text=text)
            else:
                logger.info("未配置消息类型或暂不支持此消息类型！")
                return False
        else:
            logger.info("未配置消息发送，请检查配置文件！")
            return False
    return True
