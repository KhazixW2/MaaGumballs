from maa.context import Context
from utils import logger

import math
import re
import time
import cv2
import numpy as np


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


# 从字符串中识别并返回数字
def extract_num(input_string):
    match = re.search(r"(\d+)", input_string)
    if match:
        return int(match.group(1))
    else:
        return 0


# 从字符串中识别并返回有“层”这个文字的前缀数字
def extract_num_layer(input_string):
    match = re.search(r"(\d+)层", input_string)
    if match:
        return int(match.group(1))
    else:
        return 0


# 初始化地板的 ROI 列表
def calRoiList():
    start_x, start_y = 15, 222
    width, height = 138, 126
    cols, rows = 5, 6

    roi_list = []

    for r in range(rows):
        for c in range(cols):
            x = start_x + c * width
            y = start_y + r * height
            roi = [x, y, width, height]
            roi_list.append(roi)
    return roi_list


# 假设存在一个辅助函数用于判断两个 ROI 区域是否重叠或者大部分重叠
# 这里需要根据实际的 ROI 数据结构实现具体逻辑
def is_roi_in_or_mostly_in(roi1, roi2):
    # 简单示例：假设 ROI 是 (x, y, width, height) 元组
    # 计算两个 ROI 的交集面积
    x1 = max(roi1[0], roi2[0])
    y1 = max(roi1[1], roi2[1])
    x2 = min(roi1[0] + roi1[2], roi2[0] + roi2[2])
    y2 = min(roi1[1] + roi1[3], roi2[1] + roi2[3])
    if x2 > x1 and y2 > y1:
        intersection_area = (x2 - x1) * (y2 - y1)
        roi1_area = roi1[2] * roi1[3]
        # 判断交集面积是否超过 roi1 面积的一半
        return intersection_area / roi1_area >= 0.5
    return False


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
    context.run_task("Fight_Magic_Special")
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
    else:
        logger.info(f"没有找到对应的魔法:{MagicName}")
        context.run_task("BackText")
        return False
    return True


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
                "TitlePanel_Learnable_Next": {
                    "roi": titileRect[titleLevel],
                },
                "TitlePanel_Learnable_Fnish": {
                    "roi": titileRect[titleLevel],
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
                "TitlePanel_Learnable_Next": {
                    "roi": titileRect[titleLevel],
                },
                "TitlePanel_Learnable_Fnish": {
                    "roi": titileRect[titleLevel],
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


def findItem(
    equipmentName: str, isUse: bool, context: Context, dst_x: int = 0, dst_y: int = 0
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
        logger.info(f"已发现: {buffName}")
        return True
    logger.info(f"未发现: {buffName}")
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
    logger.info(status)

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
    elif targetWish == "神锻":
        wishlist = [
            "我想获得巨龙之力",
            "我想学习龙语魔法",
            "我要变得更强",
            "我要神奇的果实",
            "我要获得钻石",
            "我要最凶残的装备",
            "我要你的收藏品",
            "我要变得富有",
            "我需要您的碎片",
            "我要更多的伙伴",
            "我要大量的矿石",
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
        logger.error("请输入[工资, 神锻, 测试]中的一个")
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
            time.sleep(2)

        logger.info(f"已点击愿望: {min_index_wish}")
        status = True
        while status:
            image = context.tasker.controller.post_screencap().wait().get()
            TextRecoDetail = context.run_recognition(
                "Fight_FindText",
                image,
                pipeline_override={
                    "Fight_FindText": {
                        "expected": "神龙冈布奥",
                    }
                },
            )
            status = TextRecoDetail
            if TextRecoDetail:
                center_x, center_y = (
                    TextRecoDetail.box[0] + TextRecoDetail.box[2] // 2,
                    TextRecoDetail.box[1] + TextRecoDetail.box[3] // 2,
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
            context.run_task("JJC_OpenForceOfNature")
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


def rgb_pixel_count(
    image,
    lower,
    upper,
    count,
    context: Context,
    method="opencv",
) -> int:
    """
    RGB颜色空间像素计数
    :param image: BGR格式图像（需转换）
    :param roi: 检测区域 [x,y,w,h]
    :param lower: RGB下限 [R,G,B] (0-255)
    :param upper: RGB上限 [R,G,B]
    :return: 匹配像素数量
    """

    # RGB转BGR
    lower = [lower[2], lower[1], lower[0]]
    upper = [upper[2], upper[1], upper[0]]

    if method == "opencv":
        # 创建三维掩膜
        lower_bound = np.array(lower, dtype=np.uint8)
        upper_bound = np.array(upper, dtype=np.uint8)
        mask = cv2.inRange(image, lower_bound, upper_bound)

        # 统计有效像素数量
        valid_pixel_count = cv2.countNonZero(mask)
        return valid_pixel_count if valid_pixel_count > count else 0

    elif recoDetail := context.run_recognition(
        "GridCheckTemplate",
        image,
        pipeline_override={
            "GridCheckTemplate": {
                "recognition": "ColorMatch",
                "method": 4,
                "lower": lower,
                "upper": upper,
                "count": count,
            }
        },
    ):
        if recoDetail:
            valid_pixel_count = recoDetail.best_result.count
            return valid_pixel_count if valid_pixel_count > count else 0
        return 0
    else:
        return 0


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
