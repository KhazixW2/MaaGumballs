from maa.context import Context
from utils import logger, send_message
from plyer import notification

import math
import re
import time
from functools import wraps

# 神龙许愿ROI [77,465,570,553]
# 神龙许愿list = ["我要获得钻石", "我要神奇的果实", "我要更多的伙伴", "我要获得巨龙之力", "我要学习龙语魔法", "我要变得更强", "我要变得富有", "我要最凶残的装备", "我要更多的伙伴", "我要大量的矿石", "我要你的收藏品", "我要您的碎片"]

MagicType: dict = {
    "火": "Fight_ClickFireMagicPage",
    "水": "Fight_ClickWaterMagicPage",
    "土": "Fight_ClickEarthMagicPage",
    "气": "Fight_ClickQiMagicPage",
    "光": "Fight_ClickLightMagicPage",
    "暗": "Fight_ClickDarkMagicPage",
}


EquipmentType: dict = {
    "腰带": [56, 262, 138, 120],
    "手套": [67, 150, 122, 117],
    "盔甲": [186, 143, 117, 123],
    "头盔": [301, 138, 123, 129],
    "副手": [415, 143, 120, 122],
    "项链": [536, 150, 124, 119],
    "戒指": [529, 266, 127, 117],
    "披风": [522, 380, 138, 116],
    "鞋子": [536, 491, 122, 123],
    "宝物": [411, 477, 131, 141],
}


def send_alert(title, message):
    try:
        notification.notify(
            title=title, message=message, app_name="MaaGumballs", timeout=10
        )
    except Exception as e:
        logger.error(f"通知发送失败：{str(e)}")


def extract_num(input_string):
    """
    从字符串中识别并返回数字
    """
    match = re.search(r"(\d+)", input_string)
    if match:
        return int(match.group(1))
    else:
        return 0


def extract_num_layer(input_string):
    """
    从字符串中识别并返回有“层”这个文字的前缀数字
    """
    match = re.search(r"(\d+)层", input_string)
    if match:
        return int(match.group(1))
    else:
        return 0


def cast_magic(Type: str, MagicName: str, context: Context, TargetPos: tuple = (0, 0)):
    """施放指定类型的魔法

    Args:
        Type: 魔法的类型，如 '火', '土', '气' 等
        MagicName: 具体的魔法名称，如 '祝福术', '石肤术' 等
        TargetPos: 目标位置，如 (x, y)
        context: 游戏上下文对象，包含当前状态信息

    Returns:
        执行结果，成功返回 True, 失败返回 False

    Example:
        >>> cast_magic("火", "火球术", context)
        True
    """

    # run
    context.run_task(
        "Fight_Magic_Elemental",
        pipeline_override={"Fight_Magic_Elemental": {"next": [MagicType[Type]]}},
    )

    image = context.tasker.controller.post_screencap().wait().get()
    if context.run_recognition(
        "Fight_Magic_Cast",
        image,
        pipeline_override={"Fight_Magic_Cast": {"expected": MagicName}},
    ):
        # 自身释放的魔法
        if TargetPos == (0, 0):
            context.run_task(
                "Fight_Magic_Cast",
                pipeline_override={
                    "Fight_Magic_Cast": {
                        "expected": MagicName,
                        "next": "Fight_ClickMagic",
                    }
                },
            )
            logger.info(f"施放魔法:{MagicName}")
        # 指定位置释放的魔法
        else:
            rect_x, rect_y = TargetPos[0] - 50, TargetPos[1] - 50
            context.run_task(
                "Fight_Magic_Cast",
                pipeline_override={
                    "Fight_Magic_Cast": {"expected": MagicName},
                    "Fight_ClickMagic": {"target": [rect_x, rect_y, 100, 100]},
                },
            )
            logger.info(f"施放魔法:{MagicName}在{TargetPos}")
    else:
        logger.info(f"没有找到对应的魔法:{MagicName}")
        context.run_task("BackText")
        return False

    return True


def check_magic(Type: str, MagicName: str, context: Context):
    """施放指定类型的魔法

    Args:
        Type: 魔法的类型，如 '火', '土', '气' 等
        MagicName: 具体的魔法名称，如 '祝福术', '石肤术' 等
        context: 游戏上下文对象，包含当前状态信息

    Returns:
        执行结果，存在返回 True, 失败返回 False

    Example:
        >>> cast_magic("火", "火球术", context)
        True
    """

    # run
    context.run_task(
        "Fight_Magic_Elemental",
        pipeline_override={"Fight_Magic_Elemental": {"next": [MagicType[Type]]}},
    )

    image = context.tasker.controller.post_screencap().wait().get()
    if context.run_recognition(
        "Fight_Magic_Cast",
        image,
        pipeline_override={"Fight_Magic_Cast": {"expected": MagicName}},
    ):
        logger.info(f"找到了魔法:{MagicName}")
        context.run_task("BackText")
    else:
        logger.info(f"没有找到对应的魔法:{MagicName}")
        context.run_task("BackText")
        return False
    return True


def cast_magic_special(MagicName: str, context: Context):
    """施放特殊类型的魔法

    Args:
        MagicName: 具体的魔法名称，如 '天眼', '大闹天宫' 等
        context: 游戏上下文对象，包含当前状态信息

    Returns:
        执行结果，成功返回 True, 失败返回 False

    Example:
        >>> cast_magic_special("天眼", context)
        True
    """

    # run
    magic_special_type = [(632, 328), (632, 430), (632, 539)]
    context.run_task("Fight_Magic_Special")
    # 多尝试几页，来适配更多类型特殊魔法
    count = 0
    while count < 3:
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition(
            "Fight_Magic_Special_Cast",
            image,
            pipeline_override={"Fight_Magic_Special_Cast": {"expected": MagicName}},
        ):
            context.run_task(
                "Fight_Magic_Special_Cast",
                pipeline_override={"Fight_Magic_Special_Cast": {"expected": MagicName}},
            )
            logger.info(f"施放魔法:{MagicName}")
            return True
        else:
            x, y = magic_special_type[count]
            context.tasker.controller.post_click(x, y).wait()
            time.sleep(1)
        count += 1
    logger.info(f"没有找到对应的魔法:{MagicName}")
    context.run_task("BackText")
    return False


def check_magic_special(MagicName: str, context: Context):
    """确认特殊类型的魔法是否存在

    Args:
        MagicName: 具体的魔法名称，如 '天眼', '大闹天宫' 等
        context: 游戏上下文对象，包含当前状态信息

    Returns:
        执行结果，成功返回 True, 失败返回 False

    Example:
        >>> cast_magic_special("天眼", context)
        True
    """

    # run
    magic_special_type = [(632, 328), (632, 430), (632, 539)]
    context.run_task("Fight_Magic_Special")
    # 多尝试几页，来适配更多类型特殊魔法
    count = 0
    while count < 3:
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition(
            "Fight_Magic_Special_Cast",
            image,
            pipeline_override={"Fight_Magic_Special_Cast": {"expected": MagicName}},
        ):
            logger.info(f"找到了魔法:{MagicName}")
            context.run_task("BackText")
            return True
        else:
            x, y = magic_special_type[count]
            context.tasker.controller.post_click(x, y).wait()
            time.sleep(1)
        count += 1
    logger.info(f"没有找到对应的魔法:{MagicName}")
    context.run_task("BackText")
    return False


def title_learn(
    titleType: str,
    titleLevel: int,
    titleName: str,
    expectedLevel: int,
    context: Context,
):

    # 对应几级称号的坐标
    titileRect: list = [
        [0, 0, 0, 0],
        [53, 843, 138, 152],
        [185, 854, 119, 136],
        [296, 847, 127, 140],
        [418, 842, 123, 147],
        [530, 847, 133, 147],
    ]

    for i in range(0, expectedLevel):
        logger.info(f"学习第{i+1}级{titleName}")
        context.run_task(
            "TitlePanel_Learnable",
            pipeline_override={
                "TitlePanel_Learnable_Click": {
                    "target": titileRect[titleLevel],
                },
                "TitlePanel_TitleCheck_New": {
                    "expected": titleName,
                    "roi": [79, 252, 563, 242],
                    "target_offset": [0, -75, 0, 0],
                },
                "TitlePanel_Series": {"expected": titleType},
                "TitlePanel_Panel": {"expected": titleType},
                "TitlePanel_CurrentPanel": {"expected": titleType},
            },
        )

    context.run_task("TitlePanel_ReturnPanel")
    return True


def title_check(titleType: str, context: Context):
    """检查是否存在目标称号系列"""
    isSuccess = False
    context.run_task("Fight_ReturnMainWindow")
    context.run_task("TitlePanel_Open")
    time.sleep(1)
    checkcount = 0
    while checkcount < 3:
        if context.run_recognition(
            "TitlePanel_CurrentPanel_Check",
            context.tasker.controller.post_screencap().wait().get(),
            pipeline_override={
                "TitlePanel_CurrentPanel_Check": {
                    "recognition": "OCR",
                    "roi": [40, 986, 435, 108],
                    "expected": titleType,
                    "timeout": 2000,
                }
            },
        ):
            isSuccess = True
            break

        else:
            context.tasker.controller.post_click(433, 1037).wait()
            checkcount += 1
            time.sleep(0.5)
        context.run_task("Fight_ReturnMainWindow")
    return isSuccess


def title_learn_branch(
    titleType: str,
    titleLevel: int,
    titleName: str,
    expectedLevel: int,
    context: Context,
):

    # 对应几级称号的坐标
    titileRect: list = [
        [0, 0, 0, 0],
        [53, 843, 138, 152],
        [185, 854, 119, 136],
        [296, 847, 127, 140],
        [418, 842, 123, 147],
        [530, 847, 133, 147],
    ]

    for i in range(0, expectedLevel):
        logger.info(f"学习{titleType}系 {i+1}级{titleName}")
        context.run_task(
            "TitlePanel_Learnable",
            pipeline_override={
                "TitlePanel_Learnable_Click": {
                    "target": titileRect[titleLevel],
                },
                "TitlePanel_TitleCheck_New": {
                    "expected": titleName,
                    "roi": [54, 463, 623, 550],
                    "target_offset": [0, 0, 0, 0],
                },
                "TitlePanel_Series": {"expected": titleType},
                "TitlePanel_Panel": {"expected": titleType},
                "TitlePanel_CurrentPanel": {"expected": titleType},
            },
        )
        time.sleep(0.3)
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("ConfirmButton_500ms", image):
            context.run_task("ConfirmButton_500ms")

    context.run_task("TitlePanel_ReturnPanel")
    return True


def checkEquipment(
    equipmentType: str, equipmentLevel: int, equipmentName: str, context: Context
):
    """检查是否装备指定的装备"""

    # init
    global EquipmentType
    EquipmentPath = f"equipments/{equipmentLevel}level/{equipmentName}.png"

    # 检查是否装备上目标装备
    image = context.tasker.controller.post_screencap().wait().get()
    ItemRecoDetail = context.run_recognition(
        "Bag_CheckItem",
        image,
        pipeline_override={
            "Bag_CheckItem": {
                "template": EquipmentPath,
                "roi": EquipmentType[equipmentType],
            },
        },
    )

    # 输出目标装备是否装备上
    if ItemRecoDetail:
        logger.info(f"已装备: {equipmentName}")
    else:
        logger.info(f"未装备: {equipmentName}")

    return ItemRecoDetail


def findEquipment(
    equipmentLevel: int, equipmentName: str, isEquip: bool, context: Context
):
    """检查是否存在目标装备"""

    global EquipmentType
    equipment_path = f"equipments/{equipmentLevel}level/{equipmentName}.png"

    # 初始化背包
    while BagRecoDetail := context.run_recognition(
        "Bag_ToPrevPage", context.tasker.controller.post_screencap().wait().get()
    ):
        box = BagRecoDetail.best_result.box
        center_x, center_y = box[0] + box[2] // 2, box[1] + box[3] // 2
        context.tasker.controller.post_click(center_x, center_y).wait()
        time.sleep(0.5)

    # 开始寻找背包
    while True:
        image = context.tasker.controller.post_screencap().wait().get()
        ItemRecoDetail = context.run_recognition(
            "Bag_FindItem",
            image,
            pipeline_override={
                "Bag_FindItem": {
                    "template": equipment_path,
                },
            },
        )

        # 输出目标装备是否存在
        if ItemRecoDetail:
            logger.info(f"已找到: {equipmentName}")
            if isEquip:
                center_x, center_y = (
                    ItemRecoDetail.box[0] + ItemRecoDetail.box[2] // 2,
                    ItemRecoDetail.box[1] + ItemRecoDetail.box[3] // 2,
                )
                context.tasker.controller.post_click(center_x, center_y).wait()
                time.sleep(1)
                context.run_task("Bag_LoadItem")
            break
        elif context.run_recognition("Bag_ToNextPage", image):
            context.run_task("Bag_ToNextPage")
        else:
            logger.info(f"背包未找到: {equipmentName}")
            return False

    return True


def disassembleEquipment(
    equipmentLevel: int, equipmentNameList: list[str], context: Context
):
    """分解所有目标装备"""

    # 初始化背包
    while BagRecoDetail := context.run_recognition(
        "Bag_ToPrevPage", context.tasker.controller.post_screencap().wait().get()
    ):
        box = BagRecoDetail.best_result.box
        center_x, center_y = box[0] + box[2] // 2, box[1] + box[3] // 2
        context.tasker.controller.post_click(center_x, center_y).wait()
        time.sleep(0.5)

    # 开始寻找背包
    for equipmentName in equipmentNameList:
        equipment_path = f"equipments/{equipmentLevel}level/{equipmentName}.png"
        image = context.tasker.controller.post_screencap().wait().get()
        ItemRecoDetail = context.run_recognition(
            "Bag_FindItem",
            image,
            pipeline_override={
                "Bag_FindItem": {
                    "template": equipment_path,
                },
            },
        )

        # 输出目标装备是否存在
        if ItemRecoDetail:
            logger.info(f"已找到: {equipmentName}")
            center_x, center_y = (
                ItemRecoDetail.box[0] + ItemRecoDetail.box[2] // 2,
                ItemRecoDetail.box[1] + ItemRecoDetail.box[3] // 2,
            )
            context.tasker.controller.post_click(center_x, center_y).wait()
            time.sleep(1)
            context.run_task("Bag_DisassembleItem")
            # 点击分解按钮之后有两种情况，如果只有一件装备那么只需要点击确定，如果超过一件装备那么需要点击分解x次
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition("ConfirmButton_500ms", image):
                context.run_task("ConfirmButton_500ms")
            elif context.run_recognition("Bag_DisassembleAllItem", image):
                context.run_task("Bag_DisassembleAllItem")
            time.sleep(1)
            context.run_task("ConfirmButton_500ms")

            logger.info(f"{equipmentName}已分解")
            time.sleep(1)
        elif context.run_recognition("Bag_ToNextPage", image):
            context.run_task("Bag_ToNextPage")
        else:
            logger.info(f"背包未找到: {equipmentName}")
    return True


def findItem(
    equipmentName: str,
    isUse: bool,
    context: Context,
    dst_x: int = 0,
    dst_y: int = 0,
    threshold: float = 0.9,
):
    """检查是否存在目标装备"""

    global EquipmentType
    equipment_path = f"items/{equipmentName}.png"

    # 初始化背包
    while BagRecoDetail := context.run_recognition(
        "Bag_ToPrevPage", context.tasker.controller.post_screencap().wait().get()
    ):
        box = BagRecoDetail.best_result.box
        center_x, center_y = box[0] + box[2] // 2, box[1] + box[3] // 2
        context.tasker.controller.post_click(center_x, center_y).wait()
        time.sleep(0.5)

    # 开始寻找
    while True:
        # 检测目标物品
        image = context.tasker.controller.post_screencap().wait().get()
        ItemRecoDetail = context.run_recognition(
            "Bag_FindItem",
            image,
            pipeline_override={
                "Bag_FindItem": {
                    "template": equipment_path,
                    "threshold": threshold,
                },
            },
        )

        # 输出目标装备是否存在
        if ItemRecoDetail:
            logger.info(f"已找到: {equipmentName}")
            if isUse:
                center_x, center_y = (
                    ItemRecoDetail.box[0] + ItemRecoDetail.box[2] // 2,
                    ItemRecoDetail.box[1] + ItemRecoDetail.box[3] // 2,
                )
                context.tasker.controller.post_click(center_x, center_y).wait()
                time.sleep(1)

                image = context.tasker.controller.post_screencap().wait().get()
                if context.run_recognition("Bag_LoadItem", image):
                    context.run_task("Bag_LoadItem")
                # 使用所有
                else:
                    context.run_task("Bag_LoadAllItem")

                if (dst_x != 0) or (dst_y != 0):
                    logger.info(f"使用物品 {equipmentName}, at {dst_x},{dst_y}")
                    context.tasker.controller.post_click(dst_x, dst_y).wait()
            break
        elif context.run_recognition("Bag_ToNextPage", image):
            context.run_task("Bag_ToNextPage")
        else:
            logger.info(f"背包未找到: {equipmentName}")
            return False

    return True


def pair_by_distance(detections, max_distance=200):
    """
    根据距离进行智能配对，返回字典格式
    """
    if not detections:
        return {}

    status = {}
    used_indices = set()

    for i, det1 in enumerate(detections):
        if i in used_indices:
            continue

        # 计算det1的中心点
        x1, y1, w1, h1 = det1.box
        center1_x = x1 + w1 / 2
        center1_y = y1 + h1 / 2

        best_match = None
        best_distance = float("inf")
        best_index = -1

        # 寻找最近的未配对框
        for j, det2 in enumerate(detections):
            if j <= i or j in used_indices:
                continue

            x2, y2, w2, h2 = det2.box
            center2_x = x2 + w2 / 2
            center2_y = y2 + h2 / 2

            # 计算距离
            distance = math.sqrt(
                (center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2
            )

            # 同行判断
            y_diff = abs(center1_y - center2_y)
            if y_diff < 30 and distance < best_distance and distance <= max_distance:
                best_distance = distance
                best_match = det2
                best_index = j

        # 记录配对结果（移到循环外面）
        if best_match:
            if det1.text in ["生命值", "魔法值"]:
                values = best_match.text.split("/")
                if len(values) == 2:
                    current_value = values[0]
                    max_value = values[1]
                    status[f"当前{det1.text}"] = current_value
                    status[f"最大{det1.text}"] = max_value
                else:
                    status[f"{det1.text}"] = best_match.text
            else:
                status[f"{det1.text}"] = best_match.text
            used_indices.add(i)
            used_indices.add(best_index)
        else:
            status[f"{det1.text}"] = "空"
            used_indices.add(i)

    return status


def checkBuffStatus(buffName: str, context: Context):
    BuffPath = f"fight/buff/{buffName}.png"
    context.run_task("Fight_ReturnMainWindow")
    image = context.tasker.controller.post_screencap().wait().get()
    if context.run_recognition(
        "Fight_CheckStatus",
        image,
        pipeline_override={
            "Fight_CheckStatus": {
                "template": BuffPath,
            }
        },
    ):
        logger.info(f"已发现: {buffName} buff")
        return True
    logger.info(f"未发现: {buffName} buff")
    return False


def checkGumballsStatusV2(context: Context):
    """检查当前战斗中的Gumball角色状态信息

    Args:
        context (Context): 任务上下文对象，提供控制器和任务执行能力

    Returns:
        dict: 包含角色状态的字典，格式为{属性名: 属性值}

    Example:
        {
            "攻击": "58",
            "生命值": "915/915",
            "魔法值": "225/225"
        }
    """
    status = {
        "攻击": "50",
        "魔力": "50",
        "闪避": "10%",
        "当前生命值": "100",
        "最大生命值": "100",
        "当前魔法值": "100",
        "最大魔法值": "100",
        "降低敌人攻击": "8",
    }

    # 打开状态面包
    context.run_task("Fight_ReturnMainWindow")
    context.run_task("Fight_OpenStatusPanel")

    # 检查状态
    image = context.tasker.controller.post_screencap().wait().get()
    if reco_detail := context.run_recognition("Fight_CheckStatusText", image):
        nodes = reco_detail.all_results
        status = pair_by_distance(nodes, max_distance=200)
    else:
        logger.warning("状态识别失败，保持默认值")

    # 输出状态字典
    # logger.info(status)

    context.run_task("Fight_ReturnMainWindow")
    return status


def dragonwish(targetWish: str, context: Context):
    wishlist = []
    min_index = 999
    min_index_wish = ""
    min_index_wish_pos = None
    if targetWish == "工资":
        wishlist = [
            "我要获得钻石",
            "我要变得富有",
            "我要大量的矿石",
            "我需要您的碎片",
            "我想获得巨龙之力",
            "我想学习龙语魔法",
            "我要最凶残的装备",
            "我要你的收藏品",
            "我要变得更强",
            "我要更多的伙伴",
            "我要神奇的果实",
        ]
    elif targetWish == "马尔斯":
        wishlist = [
            "我要获得钻石",
            "我要变得富有",
            "我想获得巨龙之力",
            "我需要您的碎片",
            "我要更多的伙伴",
            "我要最凶残的装备",
            "我要你的收藏品",
            "我要大量的矿石",
            "我想学习龙语魔法",
            "我要变得更强",
            "我要神奇的果实",
        ]
    elif targetWish == "测试":
        wishlist = [
            "我要变得富有",
            "我要大量的矿石",
            "我要变得更强",
            "我要最凶残的装备",
            "我需要您的碎片",
            "我要更多的伙伴",
            "我要神奇的果实",
            "我要你的收藏品",
            "我要获得钻石",
            "我想学习龙语魔法",
            "我想获得巨龙之力",
        ]
    else:
        logger.error("请输入[工资, 马尔斯, 测试]中的一个")
    # 神龙许愿list = ["我要获得钻石", "我要神奇的果实", "我想获得巨龙之力", "我要学习龙语魔法", "我要变得更强","我要最凶残的装备", "我要变得富有", "我要大量的矿石", "我要你的收藏品", "我要您的碎片", "我要更多的伙伴"]

    # # 等待8秒，确保界面加载完毕，可以考虑移除
    time.sleep(8)
    textdetail = context.run_task("Fight_FindText")
    if textdetail.nodes:
        for result in textdetail.nodes[0].recognition.filterd_results:
            if result.text.endswith("！"):
                result.text = result.text[:-1]
            cuurent_wish_index = wishlist.index(result.text)
            logger.info(f"当前许愿: {result.text}")
            if cuurent_wish_index < min_index:
                min_index = cuurent_wish_index
                min_index_wish = result.text
                min_index_wish_pos = result.box
        if min_index_wish_pos:
            center_x, center_y = (
                min_index_wish_pos[0] + min_index_wish_pos[2] // 2,
                min_index_wish_pos[1] + min_index_wish_pos[3] // 2,
            )
            time.sleep(1)
            context.tasker.controller.post_click(center_x, center_y).wait()
        time.sleep(3)

        logger.info(f"已点击愿望: {min_index_wish}")
        status = True
        while status:
            image = context.tasker.controller.post_screencap().wait().get()
            TextRecoDetail = context.run_recognition(
                "TextReco",
                image,
                pipeline_override={
                    "TextReco": {
                        "recognition": "OCR",
                        "expected": ["神龙", "冈布奥"],
                        "roi": [21, 217, 682, 762],
                        "action": "DoNothing",
                    },
                },
            )
            status = TextRecoDetail
            if TextRecoDetail:
                center_x, center_y = (
                    TextRecoDetail.box[0] + TextRecoDetail.box[2] // 2,
                    TextRecoDetail.box[1] + TextRecoDetail.box[3] // 2 + 10,
                )
                context.tasker.controller.post_click(center_x, center_y).wait()
                time.sleep(1)
        # 已点击愿望，等待界面加载
        if min_index_wish in [
            "我要你的收藏品",
            "我想学习龙语魔法",
            "我想获得巨龙之力",
            "我要最凶残的装备",
            "我需要您的碎片",
        ]:
            pass

        elif min_index_wish in ["我要变得富有"]:
            # 等待地图加载
            time.sleep(10)
            cast_magic("火", "末日审判", context)
            for _ in range(3):
                if not cast_magic("暗", "死亡波纹", context):
                    if not cast_magic("土", "地刺术", context, (350, 400)):
                        cast_magic("火", "流星雨", context, (350, 400))
                        if targetWish == "工资":
                            logger.info("那只能使用天眼了")
                            cast_magic_special("天眼", context)

                        else:
                            logger.info("没有死波没有地刺,流星雨不会也没有吧！")

            # 除变强以外的夹层的出口一定在右下角
            context.run_task("Fight_ReturnMainWindow")
            time.sleep(2)
            context.tasker.controller.post_click(646, 939).wait()
            time.sleep(2)
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition("ConfirmButton_500ms", image):
                context.run_task("ConfirmButton_500ms")
            # 等待拾取结束
        elif min_index_wish in ["我要更多的伙伴"]:
            context.run_task("Fight_ReturnMainWindow")
            time.sleep(2)
            context.tasker.controller.post_click(646, 939).wait()
            time.sleep(2)
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition("ConfirmButton_500ms", image):
                context.run_task("ConfirmButton_500ms")
            pass
            # todo 清理当前层的逻辑
        elif min_index_wish in ["我要获得钻石"]:
            # 等待地图加载
            time.sleep(10)

            for _ in range(110):
                time.sleep(0.1)
                context.tasker.controller.post_click(356, 407).wait()
                context.tasker.controller.post_click(214, 681).wait()
                context.tasker.controller.post_click(493, 684).wait()

            # 除变强以外的夹层的出口一定在右下角
            # 等待拾取结束
            context.run_task("Fight_ReturnMainWindow")
            time.sleep(2)
            context.tasker.controller.post_click(646, 939).wait()
            time.sleep(2)
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition("ConfirmButton_500ms", image):
                context.run_task("ConfirmButton_500ms")

        elif min_index_wish in ["我要大量的矿石"]:
            # 等待地图加载
            time.sleep(10)
            for _ in range(13):
                time.sleep(0.5)
                context.tasker.controller.post_click(365, 535).wait()
                context.tasker.controller.post_click(219, 813).wait()
                context.tasker.controller.post_click(505, 805).wait()

            # 除变强以外的夹层的出口一定在右下角
            # 等待拾取结束
            context.run_task("Fight_ReturnMainWindow")
            time.sleep(2)
            context.tasker.controller.post_click(646, 939).wait()
            time.sleep(2)
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition("ConfirmButton_500ms", image):
                context.run_task("ConfirmButton_500ms")

        elif min_index_wish in ["我要变得更强", "我要神奇的果实"]:
            # TODO: 调用boss层

            if targetWish == "神锻":
                pass
            pass
    else:
        # 没有出现目标，不进行后续处理
        logger.info(f"没有检测到（我要，我想，我需)的字样, 检查一下")
        pass
    return min_index_wish


def Auto_CallDog(context: Context):
    # 叫狗初始化
    OpenDetail = context.run_task("Bag_Open")
    if OpenDetail.nodes:
        if not checkEquipment("腰带", 2, "电弧束带", context):
            findEquipment(2, "电弧束带", True, context)
        if not checkEquipment("宝物", 4, "毁灭者石板", context):
            findEquipment(4, "毁灭者石板", True, context)
        context.run_task("Fight_ReturnMainWindow")
        logger.info(f"叫狗装备检查完成")

    # 打开背包
    OpenDetail = context.run_task("Bag_Open")
    if OpenDetail.nodes:
        findItem("狼人药剂", True, context)
        context.run_task("Bag_Open")
        findItem("狼人药剂", True, context)
        context.run_task("Bag_Open")
        findItem("狼人药剂", True, context)

        # 拖回合
        for i in range(1, 76):
            OpenNatureSwitch(i % 2, context)
        cast_magic("气", "静电场", context)

        if cast_magic("火", "毁灭之刃", context):
            pass
        elif cast_magic("土", "地震术", context):
            cast_magic("气", "静电场", context)
            cast_magic_special("天眼", context)

        if not checkBuffStatus("毁灭之刃", context):
            # sl恢复现场, 叫狗失败
            logger.error(f"召唤狗子失败,可能是没触发毁灭,请到下一层叫狗.现在先保存状态")
            context.run_task("LogoutGame")
            context.run_task("ReturnMaze")
            return False

        # 召唤狗子
        OpenDetail = context.run_task("Bag_Open")
        findItem("东方剪纸", True, context)

        # 关闭自然之力
        logger.info("关闭自然之力")
        tmp_ctx = context.clone()
        tmp_ctx.run_task(
            "JJC_OpenForceOfNature",
            pipeline_override={"JJC_OpenForceOfNature_Switch": {"expected": "关闭"}},
        )
        time.sleep(1)
        logger.info("狗子召唤成功！！！")
    return True


def PushOne(context: Context):
    context.run_task("Fight_ReturnMainWindow")
    if not cast_magic("水", "治疗术", context):
        if not cast_magic("水", "寒冰护盾", context):
            if not cast_magic("暗", "死亡波纹", context):
                if cast_magic("暗", "吸能术", context):
                    return True
                else:
                    logger.info("没有治疗术、寒冰护盾、吸能术，死亡波纹, 无法推序！")
                    return False
    return True


def PushOne_defense(context: Context):
    """
    防御性的拖回合
    """
    if not cast_magic("水", "寒冰护盾", context):
        if not cast_magic("水", "治疗术", context):
            if not cast_magic("光", "神恩术", context):
                if not cast_magic("光", "祝福术", context):
                    pass
                else:
                    logger.info("怎么什么都没有，只能释放闪电火球了")
                    if not cast_magic("气", "闪电术", context):
                        cast_magic("火", "火球术", context)

    return True


def OpenNatureSwitch(isDefense: bool, context: Context):
    tempStr: str = "自然守护" if isDefense else "自然之力"
    context.run_task(
        "JJC_OpenForceOfNature",
        pipeline_override={
            "JJC_OpenForceOfNature_Switch": {
                "expected": [f"开启{tempStr}"],
            },
            "JJC_OpenForceOfNature_Fail": {
                "expected": [f"关闭{tempStr}"],
            },
        },
    )


def autoOpenPicup(context: Context):
    # 测试中
    context.tasker.controller.post_touch_down(68, 661)
    time.sleep(5)
    context.run_task("Fight_OpenedDoor")
    context.tasker.controller.post_touch_up()


def Saveyourlife(context: Context):
    checkcount = 0
    while checkcount < 3:
        TextRecoDetail = context.run_recognition(
            "Fight_FindRespawn",
            context.tasker.controller.post_screencap().wait().get(),
            pipeline_override={
                "Fight_FindRespawn": {
                    "roi": [66, 563, 583, 446],
                    "expected": "复活",
                }
            },
        )
        checkcount += 1
        time.sleep(0.5)
        if TextRecoDetail:
            break

    if TextRecoDetail:
        logger.info("夭寿啦！！！检测到冈布奥倒下啦！")
        # 小SL, 保住狗命
        context.run_task("LogoutGame")
        context.run_task("ReturnMaze")
    else:
        logger.info("没有检测到冈布奥倒下！可能没死吧！！继续战斗！！")
    return True


def handle_dragon_event(map_str: str, context: Context):
    # 检测神龙
    img = context.tasker.controller.post_screencap().wait().get()
    if context.run_recognition("Fight_FindDragon", img):
        logger.info("是神龙,俺,俺们有救了！！！")
        dragonwish(map_str, context)
        logger.info("神龙带肥家lo~")
        send_message(f"MaaGB", "是神龙,俺,俺们有救了！！！")


def handle_currentlayer_event(context: Context):
    context.run_task("Fight_ReturnMainWindow")
    tempLayers = -1
    while tempLayers <= 0 and (
        RunResult := context.run_recognition(
            "Fight_CheckLayer",
            context.tasker.controller.post_screencap().wait().get(),
        )
    ):
        tempLayers = extract_num_layer(RunResult.best_result.text)
        if context.tasker.stopping:
            logger.info("检测到停止任务, 开始退出agent")
            return -1
    return tempLayers


def handle_downstair_event(context: Context):
    temp_layer = handle_currentlayer_event(context)
    recoDetail = context.run_task("Fight_OpenedDoor")
    if not recoDetail.nodes and context.run_recognition(
        "FindKeyHole", context.tasker.controller.post_screencap().wait().get()
    ):
        logger.warning("检查到神秘的洞穴捏，请冒险者大人检查！！")
        send_alert("洞穴警告", "发现神秘洞穴，请及时处理！")

        send_message(f"MaaGB", "发现神秘洞穴，请及时处理")

        while not context.run_recognition(
            "Fight_OpenedDoor",
            context.tasker.controller.post_screencap().wait().get(),
        ):
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return False
            time.sleep(3)

        logger.info("冒险者大人已找到钥匙捏，继续探索")
        context.run_task("Fight_OpenedDoor")
    # 确认层数更换再返回
    for _ in range(5):
        current_layer = handle_currentlayer_event(context)
        if temp_layer != current_layer and current_layer != -1:
            return True
        time.sleep(1)
    logger.info("由于未知原因, 层数未改变，可能在夹层中")
    return True


def handle_skillShop_event(
    context: Context, target_skill=["火球术", "闪电术", "死亡波纹"]
):
    # 打开技能商店
    if context.run_recognition(
        "Fight_SkillShop", context.tasker.controller.post_screencap().wait().get()
    ):
        logger.info("触发技能商店")

        context.run_task("Fight_SkillShop")
        # 拼凑技能路径
        template_path = ["items/scroll/%s.png" % skill for skill in target_skill]
        # 技能商店开始购物
        if recoDetail := context.run_recognition(
            "SkillShop_Reco",
            context.tasker.controller.post_screencap().wait().get(),
            pipeline_override={
                "SkillShop_Reco": {
                    "recognition": "TemplateMatch",
                    "template": template_path,
                    "roi": [65, 334, 610, 686],
                    "threshold": 0.8,
                }
            },
        ):
            logger.info(f"找到商品{len(recoDetail.filterd_results)}个, 开始购物")
            for result in recoDetail.filterd_results:
                if result.score < 0.8:
                    continue
                box = result.box
                context.tasker.controller.post_click(
                    box[0] + box[2] // 2, box[1] + box[3] // 2
                )
                time.sleep(0.5)
                context.run_task("ConfirmButton_500ms")
        context.run_task("Fight_ReturnMainWindow")


# 存储函数执行时间的全局变量
function_time_records = {}


def timing_decorator(func):
    """装饰器：记录函数执行时间并累积总时长"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start_time

        # 更新函数执行时间记录
        if func_name in function_time_records:
            function_time_records[func_name]["count"] += 1
            function_time_records[func_name]["total_time"] += duration
        else:
            function_time_records[func_name] = {"count": 1, "total_time": duration}

        return result

    return wrapper


# 获取统计信息的函数
def get_time_statistics():
    """返回所有函数的执行时间统计信息，返回后清空统计信息"""
    global function_time_records
    result = function_time_records
    function_time_records = {}
    return result
