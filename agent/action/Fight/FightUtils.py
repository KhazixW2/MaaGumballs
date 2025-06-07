from maa.context import Context
from loguru import logger
import time

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
                "TitlePanel_TitleCheck_New": {"expected": titleName},
                "TitlePanel_Series": {"expected": titleType},
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
            },
        )


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

    # 初始化背包
    context.run_task("Bag_ToLeftestPage")

    # 开始寻找
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
