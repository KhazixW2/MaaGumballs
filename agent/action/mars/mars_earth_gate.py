from typing import TYPE_CHECKING

from maa.context import Context
from action.fight import fightUtils
from utils import logger

if TYPE_CHECKING:
    from action.fight.mars101 import Mars101

import time


class MarsEarthGateManager:
    """马尔斯101大地之门管理器：负责大地之门施放与等待"""

    def __init__(self, mars: "Mars101") -> None:
        self.mars: "Mars101" = mars

    def handle_EarthGate_event(self, context: Context):
        """
        大地成功返回True,否则返回False
        """
        if (
            ((self.mars.layers > 60) and (self.mars.layers % 10 == 9))
            # 在61~63层时释放大地，或者x9(>60)层时释放大地
            or (self.mars.layers == 66)
        ) and self.mars.useEarthGate < self.mars.target_earthgate_para:
            # 识别是否门关着
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition("Fight_ClosedDoor", image).hit:
                logger.info("当前层无法释放大地，跳过")
                return False
            context.run_task("Fight_ReturnMainWindow")
            if fightUtils.check_magic("土", "大地之门", context):
                fightUtils.cast_magic("气", "静电场", context)
                if self.mars.isUseMagicAssist:
                    # 关闭魔法助手, 节省卷轴
                    fightUtils.cast_magic_special("魔法助手", context)
                    self.mars.isUseMagicAssist = False
                if fightUtils.cast_magic("土", "大地之门", context):
                    templayer = self.mars.layers
                    for _ in range(10):
                        logger.info(f"等待大地之门特效结束")
                        self.mars.Check_CurrentLayers(context)
                        if self.mars.layers != templayer and self.mars.layers != -1:
                            logger.info(f"大地之门特效结束, 当前层数为{self.mars.layers}")
                            self.mars.note_earth_gate_used()
                            return True
                        time.sleep(1)
        return False
