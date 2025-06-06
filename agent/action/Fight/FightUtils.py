from maa.context import Context
from loguru import logger

MagicType: dict = {
    "火": "Fight_ClickFireMagicPage",
    "水": "Fight_ClickWaterMagicPage",
    "土": "Fight_ClickEarthMagicPage",
    "气": "Fight_ClickQiMagicPage",
    "光": "Fight_ClickLightMagicPage",
    "暗": "Fight_ClickDarkMagicPage",
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
    RunDetail = context.run_task(
        "Fight_Magic_Elemental",
        pipeline_override={
            "Fight_Magic_Cast": {"expected": MagicName},
            "Fight_Magic_Elemental": {
                "interrupt": [
                    MagicType[Type],
                    "Fight_SkillPack_Type",
                    "Fight_SkillPack_Open",
                ],
            },
        },
    )

    if not RunDetail:
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
    RunDetail = context.run_task(
        "Fight_Magic_Special",
        pipeline_override={"Fight_Magic_Special_Cast": {"expected": MagicName}},
    )

    if not RunDetail:
        return False

    return True


def title_learn(
    titleType: str,
    titleLevel: int,
    titleName: str,
    expectedLevel: int,
    context: Context,
):
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
