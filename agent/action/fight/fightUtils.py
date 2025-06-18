from maa.context import Context
from utils import logger
from typing import Literal

import re
import time

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


# 从字符串中识别并返回第一个数字
def extract_numbers(input_string):
    numbers = re.findall(r"\d+", input_string)
    if numbers:
        return int(numbers[0])
    else:
        return None


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


def cast_magic(Type: str, MagicName: str, context: Context):
    """施放指定类型的魔法

    Args:
        Type: 魔法的类型，如 '火', '土', '气' 等
        MagicName: 具体的魔法名称，如 '祝福术', '石肤术' 等
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
        pipeline_override={
            "Fight_Magic_Elemental": {
                "next": [MagicType[Type]],
                "interrupt": [
                    "Fight_SkillPack_Type",
                    "Fight_SkillPack_Open",
                ],
            },
        },
    )

    image = context.tasker.controller.post_screencap().wait().get()
    if context.run_recognition(
        "Fight_Magic_Cast",
        image,
        pipeline_override={"Fight_Magic_Cast": {"expected": MagicName}},
    ):
        context.run_task(
            "Fight_Magic_Cast",
            pipeline_override={"Fight_Magic_Cast": {"expected": MagicName}},
        )
        logger.info(f"施放魔法:{MagicName}")
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
                "TitlePanel_CurrentPanel": {"expected": titleType},
            },
        )


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
                    "roi": [54, 463, 623, 550],
                    "target_offset": [0, 0, 0, 0],
                },
                "TitlePanel_Series": {"expected": titleType},
                "TitlePanel_CurrentPanel": {"expected": titleType},
            },
        )
        context.run_task("BackText")
        context.run_task("BackText")


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
    context.run_task("Bag_ToLeftestPage")

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
        elif context.run_recognition(
            "Bag_ToNextPage",
            context.tasker.controller.post_screencap().wait().get(),
        ):
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

    # 开始寻找
    while True:
        # 初始化背包
        context.run_task("Bag_ToLeftestPage")

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
                context.run_task("Bag_LoadItem")

                if (dst_x != 0) or (dst_y != 0):
                    logger.info(f"使用物品 {equipmentName}, at {dst_x},{dst_y}")
                    context.tasker.controller.post_click(dst_x, dst_y).wait()
            break
        elif context.run_recognition(
            "Bag_ToNextPage",
            context.tasker.controller.post_screencap().wait().get(),
        ):
            context.run_task("Bag_ToNextPage")
        else:
            logger.info(f"背包未找到: {equipmentName}")
            return False

    return True


def dragonwish(targetWish: Literal["工资", "神锻", "测试"], context: Context):
    if targetWish == "工资":
        wishlist = [
            "我要获得钻石",
            "我要变得富有",
            "我想获得巨龙之力",
            "我想学习龙语魔法",
            "我要最凶残的装备",
            "我要你的收藏品",
            "我要您的碎片",
            "我要大量的矿石",
            "我要更多的伙伴",
            "我要变得更强",
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
            "我要您的碎片",
            "我要更多的伙伴",
            "我要大量的矿石",
        ]
    elif targetWish == "测试":
        wishlist = [
            "我要变得更强",
            "我要变得富有",
            "我要最凶残的装备",
            "我要您的碎片",
            "我要更多的伙伴",
            "我要神奇的果实",
            "我要你的收藏品",
            "我要获得钻石",
            "我想学习龙语魔法",
            "我要大量的矿石",
            "我想获得巨龙之力",
        ]
    else:
        logger.error("请输入[工资, 神锻, 测试]中的一个")
    # 神龙许愿list = ["我要获得钻石", "我要神奇的果实", "我想获得巨龙之力", "我要学习龙语魔法", "我要变得更强","我要最凶残的装备", "我要变得富有", "我要大量的矿石", "我要你的收藏品", "我要您的碎片", "我要更多的伙伴"]

    # 等待5秒，确保界面加载完毕，可以考虑移除
    time.sleep(5)
    Itemdetail = context.run_task("Fight_FindItem")

    if Itemdetail.nodes:
        # 集齐七个龙珠并进入到许愿界面
        textdetail = context.run_task("Fight_FindText")
        min_index = 999
        min_index_wish = None
        min_index_wish_pos = None
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
                "我要您的碎片",
            ]:
                pass

            elif min_index_wish in ["我要更多的伙伴", "我要变得富有"]:
                # 等待地图加载
                time.sleep(10)
                for _ in range(3):
                    cast_magic("暗", "死亡波纹", context)
                # 拾取全部
                context.run_task(
                    "Fight_LongPress",
                    pipeline_override={
                        "Fight_LongPress": {
                            "target": [286, 465, 140, 129],
                        }
                    },
                )
                context.run_task("Fight_FindMidlevelExit")

            elif min_index_wish in ["我要获得钻石"]:
                # 等待地图加载
                time.sleep(10)

                for _ in range(110):
                    time.sleep(0.1)
                    context.tasker.controller.post_click(356, 407).wait()
                    context.tasker.controller.post_click(214, 681).wait()
                    context.tasker.controller.post_click(493, 684).wait()

                context.run_task("Fight_FindMidlevelExit")
            elif min_index_wish in ["我要大量的矿石"]:
                # 等待地图加载
                time.sleep(10)
                for _ in range(2):
                    for _ in range(12):
                        time.sleep(0.1)
                        context.tasker.controller.post_click(365, 535).wait()
                        context.tasker.controller.post_click(219, 813).wait()
                        context.tasker.controller.post_click(505, 805).wait()
                    time.sleep(1)
                    # 拾取全部
                    context.run_task(
                        "Fight_LongPress",
                        pipeline_override={
                            "Fight_LongPress": {
                                "target": [33, 595, 103, 108],
                            }
                        },
                    )
                context.run_task("Fight_FindMidlevelExit")
            elif min_index_wish in ["我要变得更强", "我要神奇的果实"]:
                # TODO: 调用boss层

                if targetWish == "神锻":
                    pass
                pass
        else:
            # 没有出现目标，不进行后续处理
            pass
    return min_index_wish
