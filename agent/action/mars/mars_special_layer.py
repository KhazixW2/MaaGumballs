from typing import TYPE_CHECKING

from maa.context import Context
from action.fight import fightUtils
from action.fight.fightUtils import timing_decorator
from utils import logger, send_message

if TYPE_CHECKING:
    from action.fight.mars101 import Mars101

import time

# 特殊层怪物坐标
special_layer_monster_1_x, special_layer_monster_1_y = 90, 650
special_layer_monster_2_x, special_layer_monster_2_y = 363, 650


class MarsSpecialLayerManager:
    """马尔斯101特殊层管理器：负责进入/离开休息室及休息室事件处理"""

    def __init__(self, mars: "Mars101") -> None:
        self.mars: "Mars101" = mars

    def gotoSpecialLayer(self, context: Context, entrance_detected: bool = False):
        """进入休息室（特殊层）"""
        context.run_task("Fight_ReturnMainWindow")
        used_cached_entrance = entrance_detected
        if not entrance_detected:
            time.sleep(1)
            entrance_detected = context.run_recognition(
                "Mars_GotoSpecialLayer",
                context.tasker.controller.post_screencap().wait().get(),
            ).hit
        else:
            logger.debug(
                "special_layer cached entrance hit, skip fresh entrance recognition"
            )
        if entrance_detected:

            context.run_task("Mars_GotoSpecialLayer")
            entered_special_layer = False
            for _ in range(10):
                if context.run_recognition(
                    "Mars_GotoSpecialLayer_Confirm",
                    context.tasker.controller.post_screencap().wait().get(),
                ).hit:
                    context.run_task("Mars_GotoSpecialLayer_Confirm")
                    entered_special_layer = True
                    break
                if context.run_recognition(
                    "Mars_Inter_Confirm_Fail",
                    context.tasker.controller.post_screencap().wait().get(),
                ).hit:
                    context.run_task("Mars_Inter_Confirm_Fail")
                    logger.info("进入休息室失败, 需要重新清理当前层")
                    return False
                time.sleep(1)

            if used_cached_entrance and not entered_special_layer:
                if not context.run_recognition(
                    "Mars_LeaveSpecialLayer",
                    context.tasker.controller.post_screencap().wait().get(),
                ).hit:
                    logger.debug(
                        "cached special entrance did not enter, retry fresh recognition"
                    )
                    return self.gotoSpecialLayer(context, False)

            while not context.run_recognition(
                "Mars_LeaveSpecialLayer",
                context.tasker.controller.post_screencap().wait().get(),
            ).hit:
                time.sleep(1)
            logger.info("进入休息室")
            return True
        return True

    def leaveSpecialLayer(self, context: Context):
        """离开休息室（特殊层）"""
        context.run_task("Fight_ReturnMainWindow")
        count = 0
        for _ in range(10):
            if context.run_recognition(
                "Mars_LeaveSpecialLayer",
                context.tasker.controller.post_screencap().wait().get(),
            ).hit:
                context.run_task("Mars_LeaveSpecialLayer")
                break
        while not context.run_recognition(
            "Mars_GotoSpecialLayer",
            context.tasker.controller.post_screencap().wait().get(),
        ).hit:
            time.sleep(1)
            if count < 10:
                context.run_task("Mars_LeaveSpecialLayer")
                count += 1
            else:
                send_message("MaaGB", "自动离开休息室失败10次，请冒险者大大手动离开!")
                break
        logger.info("离开休息室")
        return True

    @timing_decorator
    def handle_SpecialLayer_event(self, context: Context, image):
        """处理休息室（特殊层）事件：吃面包、施法等"""
        # 波塞冬不放柱子，用冰锥打裸男
        if (30 <= self.mars.layers + 1 <= 150) and ((self.mars.layers + 1) % 10 == 0):
            entrance_detected = False
            for _ in range(5):
                entrance_detected = context.run_recognition(
                    "Mars_GotoSpecialLayer", image
                ).hit
                if not entrance_detected:
                    logger.debug("当前截图中休息室可能被遮挡, 再次截图尝试")
                    context.run_task(
                        "WaitStableNode_ForOverride",
                        pipeline_override={
                            "WaitStableNode_ForOverride": {
                                "pre_wait_freezes": {"time": 300}
                            }
                        },
                    )
                    image = context.tasker.controller.post_screencap().wait().get()
                else:
                    break
            logger.info("触发Mars休息室事件")
            if not self.gotoSpecialLayer(context, entrance_detected):
                return False
            if self.mars.isUseMagicAssist:
                fightUtils.cast_magic("土", "石肤术", context)
            if self.mars.layers < 100:
                context.run_task("Mars_Shower")
            context.run_task("Mars_EatBread")
            if self.mars.target_magicgumball_para == "波塞冬":
                if self.mars.layers <= 89:
                    if fightUtils.cast_magic(
                        "暗",
                        "死亡波纹",
                        context,
                    ):
                        times = 2
                        for _ in range(times):
                            if not fightUtils.cast_magic(
                                "水",
                                "冰锥术",
                                context,
                                (special_layer_monster_1_x, special_layer_monster_1_y),
                            ):
                                break
                        for _ in range(times):
                            if not fightUtils.cast_magic(
                                "水",
                                "冰锥术",
                                context,
                                (special_layer_monster_2_x, special_layer_monster_2_y),
                            ):
                                break
            context.run_task("Fight_ReturnMainWindow")
            self.leaveSpecialLayer(context)
            # 检查一下状态
            self.mars.Check_DefaultStatus(context)

            return True
        return True
