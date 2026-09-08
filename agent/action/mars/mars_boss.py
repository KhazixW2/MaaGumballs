from typing import TYPE_CHECKING

from maa.context import Context
from action.fight import fightUtils
from action.fight.fightUtils import timing_decorator
from utils import logger

if TYPE_CHECKING:
    from action.fight.mars101 import Mars101

import time


# Boss 坐标
boss_x, boss_y = 360, 800
boss_slave_1_x, boss_slave_1_y = 100, 660
boss_slave_2_x, boss_slave_2_y = 640, 660


class MarsBossHandler:
    """马尔斯101 Boss处理器：负责Boss层战斗逻辑"""

    def __init__(self, mars: "Mars101") -> None:
        self.mars: "Mars101" = mars

    @timing_decorator
    def handle_boss_event(self, context: Context):
        """处理Boss层战斗流程"""
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_OpenedDoor", image).hit:
            return True

        context.run_task(
                    "WaitStableNode_ForOverride",
                    pipeline_override={
                        "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 200}}
                    },
                )
        image = context.tasker.controller.post_screencap().wait().get()
        # result=
        # logger.debug(f"下楼钥匙识别结果: {result},{result.status if result else 'No result'}")
        if context.run_recognition("下楼钥匙",image).hit:
            logger.info("检测到下楼钥匙，尝试点击")
            context.run_task("下楼钥匙")
            return True

        # 检查boss是否存在
        if context.run_recognition(
            "Fight_CheckBossStatus",
            context.tasker.controller.post_screencap().wait().get(),
        ).hit:
            logger.info(f"当前层数 {self.mars.layers} 已经击杀boss")
        if context.run_recognition("Fight_OpenedDoor", image).hit:
            return True
        fightUtils.cast_magic_special("生命颂歌", context)
        if self.mars.target_magicgumball_para == "波塞冬":
            fightUtils.cast_magic(
                "水", "冰锥术", context, (boss_slave_1_x, boss_slave_1_y)
            )
            context.tasker.controller.post_click(boss_slave_1_x, boss_slave_1_y).wait()
            fightUtils.cast_magic(
                "水", "冰锥术", context, (boss_slave_2_x, boss_slave_2_y)
            )
            context.tasker.controller.post_click(boss_slave_2_x, boss_slave_2_y).wait()
        else:
            fightUtils.cast_magic("光", "祝福术", context)
            context.tasker.controller.post_click(boss_slave_1_x, boss_slave_1_y).wait()
            time.sleep(2)
            context.tasker.controller.post_click(boss_slave_2_x, boss_slave_2_y).wait()
        fightUtils.cast_magic_special("生命颂歌", context)
        if self.mars.layers >= 120:
            fightUtils.cast_magic("土", "石肤术", context, (boss_x, boss_y))
        fightUtils.cast_magic_special("生命颂歌", context)
        if context.run_recognition("Fight_OpenedDoor", image).hit:
            return True
        actions = []
        if self.mars.target_magicgumball_para == "波塞冬":
            if self.mars.layers < 110:
                actions = [
                    lambda: fightUtils.cast_magic(
                        "水", "冰锥术", context, (boss_x, boss_y)
                    ),
                    lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                ]
            elif self.mars.layers >= 110 and self.mars.layers <= 150:
                actions = [
                    lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                    lambda: fightUtils.cast_magic(
                        "水", "冰锥术", context, (boss_x, boss_y)
                    ),
                    lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                    lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                ]
        else:
            if self.mars.layers <= 80:
                actions = [
                    lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                    lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                    lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                ]
            elif self.mars.layers >= 90 and self.mars.layers <= 150:
                actions = [
                    lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                    lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                    lambda: fightUtils.cast_magic("水", "冰锥术", context),
                    lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                    lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                ]
        index = 0
        for _ in range(10):
            # 执行当前动作
            if not actions[index]():
                logger.info("没有冰锥了，尝试直接点击boss")
                for _ in range(5):
                    context.tasker.controller.post_click(boss_x, boss_y).wait()
                    context.run_task(
                        "WaitStableNode_ForOverride",
                        pipeline_override={
                            "WaitStableNode_ForOverride": {
                                "pre_wait_freezes": {"time": 100}
                            }
                        },
                    )

            context.run_task(
                "WaitStableNode_ForOverride",
                pipeline_override={
                    "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 300}}
                },
            )

            # 检查boss是否存在
            if context.run_recognition(
                "Fight_CheckBossStatus",
                context.tasker.controller.post_screencap().wait().get(),
            ).hit:
                logger.info(f"当前层数 {self.mars.layers} 已经击杀boss")
                break

            index = (index + 1) % len(actions)
            fightUtils.handle_dragon_event("马尔斯", context)
            if context.run_recognition(
                "Fight_FindRespawn",
                context.tasker.controller.post_screencap().wait().get(),
            ).hit:
                logger.info("检测到死亡， 尝试小SL")
                fightUtils.Saveyourlife(context)
                return False

        # 捡东西
        context.run_task(
            "WaitStableNode_ForOverride",
            pipeline_override={
                "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 100}}
            },
        )
        context.run_task("Mars_Inter_Confirm_Fail")#防止卡在柱子界面

        return True
