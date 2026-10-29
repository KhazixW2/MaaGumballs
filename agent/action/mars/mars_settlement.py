from typing import TYPE_CHECKING

from maa.context import Context
from action.fight import fightUtils
from utils import logger

if TYPE_CHECKING:
    from action.fight.mars101 import Mars101

import time


class MarsSettlementManager:
    """马尔斯101结算管理器：负责出图前结算流程"""

    def __init__(self, mars: "Mars101") -> None:
        self.mars: "Mars101" = mars

    def handle_before_leave_maze_event(self, context: Context):
        logger.info("触发Mars结算事件")
        context.run_task("Fight_ReturnMainWindow")
        if self.mars.manual_leave_para != "清怪暂离":
            # 名导心得相关
            if self.mars.director_para:
                fightUtils.openBagAndUseItem(
                    "名导心得", False, context, isReturnMainWindow=False
                )
                context.run_task(
                    "Clickitem",
                    pipeline_override={
                        "Clickitem": {
                            "recognition": "TemplateMatch",
                            "action": "Click",
                            "template": "items/名导心得.png",
                            "timeout": 3000,
                            "post_delay": 500,
                        },
                    },
                )
                context.run_task(
                    "Mars_Director_ATK_for_Override",
                    pipeline_override={
                        "Mars_Director_ATK_for_Override": {
                            "template": "fight/Mars/Mars_Director2.png"
                        }
                    },
                )
                for _ in range(5):
                    context.run_task("Mars_Director_ATK_Confirm")
                context.run_task("BackText")
                context.run_task(
                    "Mars_Director_ATK_for_Override",
                    pipeline_override={
                        "Mars_Director_ATK_for_Override": {
                            "template": "fight/Mars/Mars_Director4.png"
                        }
                    },
                )
                for _ in range(6):
                    context.run_task("Mars_Director_ATK_Confirm")
                context.run_task("Fight_ReturnMainWindow")
            # 压血相关
            # 先关闭魔法助手
            # 使用剑术卷轴逻辑
            UseSwordMagic=1
            for _ in range(6):
                OpenDetail = context.run_task("Bag_Open")
                if OpenDetail:
                    time.sleep(1)
                    if UseSwordMagic==1:
                        if fightUtils.findItem(
                            "剑术卷轴1", True, context, threshold=0.6
                        ):
                            continue
                        else:
                            UseSwordMagic=2
                    elif UseSwordMagic==2:
                        if fightUtils.findItem(
                            "剑术卷轴2", True, context, threshold=0.6
                        ):
                            continue
                        else:
                            UseSwordMagic=3
                    elif UseSwordMagic==3:
                        if fightUtils.findItem(
                            "剑术卷轴3", True, context, threshold=0.6
                        ):
                            continue
                        else:
                            UseSwordMagic=4
                    elif UseSwordMagic==4:
                        if fightUtils.findItem(
                            "剑术卷轴4", True, context, threshold=0.6
                        ):
                            continue
                        else:
                            break
            context.run_task("Fight_ReturnMainWindow")
            
            # 出图前使用掉所有极光屏障，需要确认当前角色是否为波塞冬
            if self.mars and self.mars.target_magicgumball_para == "波塞冬":
                for _ in range(10):
                    if not fightUtils.cast_magic("水","极光屏障",context):
                        break
            if self.mars.isUseMagicAssist:
                fightUtils.cast_magic_special("魔法助手", context)
                self.mars.isUseMagicAssist = False

            for _ in range(3):
                fightUtils.cast_magic_special("生命颂歌", context)

            self.mars.gotoSpecialLayer(context)
            fightUtils.openBagAndUseItem("电能试剂", True, context)

            self.mars.leaveSpecialLayer(context)
            context.run_task("Fight_ReturnMainWindow")
            for _ in range(3):
                fightUtils.cast_magic_special("生命颂歌", context)
            self.mars.gotoSpecialLayer(context)
            fightUtils.openBagAndUseItem("能量电池", True, context)

            self.mars.leaveSpecialLayer(context)
            context.run_task("Fight_ReturnMainWindow")
            for _ in range(3):
                fightUtils.cast_magic_special("生命颂歌", context)
            context.run_task("Screenshot")
            logger.info("截图保存检查柱子")
            fightUtils.title_learn("魔法", 3, "咒术师", 1, context)
            if fightUtils.title_check("巨龙", context):
                fightUtils.title_learn("巨龙", 1, "亚龙血统", 3, context)
                fightUtils.title_learn("巨龙", 2, "初级龙族血统", 3, context)
                if self.mars.layers > 100:
                    fightUtils.title_learn("巨龙", 3, "中级龙族血统", 3, context)
                    fightUtils.title_learn("巨龙", 4, "高级龙族血统", 3, context)

                if self.mars.useEarthGate > 0:
                    fightUtils.title_learn("巨龙", 5, "邪龙血统", 1, context)
                    fightUtils.title_learn_branch("巨龙", 5, "攻击强化", 3, context)
                    fightUtils.title_learn_branch(
                        "巨龙", 5, "攻击强化", 3, context, repeatable=True
                    )
                    fightUtils.title_learn_branch("巨龙", 5, "生命强化", 3, context)

            context.run_task("Fight_ReturnMainWindow")
            # 压血相关
            # # 这里进夹层压血
            # if self.mars.target_earthgate_para >= 0 and self.mars.is_demontitle_enable:
            #     self.mars.gotoSpecialLayer(context)
            #     fightUtils.cast_magic("土", "石肤术", context)
            #     if not fightUtils.cast_magic("暗", "死亡波纹", context):
            #         if not fightUtils.cast_magic("火", " 末日审判", context):
            #             fightUtils.cast_magic("土", "地震术", context)
            #     for _ in range(20):
            #         if fightUtils.checkBuffStatus("神圣重生", context):
            #             logger.info("发现神圣重生buff, 使用祝福术尝试复活")
            #             fightUtils.cast_magic("光", "祝福术", context)
            #         else:
            #             time.sleep(3)
            #             break
            #     self.mars.Control_TenpecentHP(context)
            #     context.run_task("Screenshot")
            #     self.mars.leaveSpecialLayer(context)
            #     context.run_task("Fight_ReturnMainWindow")

            fightUtils.title_learn("战斗", 5, "剑圣", 1, context)
            context.run_task("Fight_ReturnMainWindow")

            fightUtils.title_learn_branch("战斗", 5, "攻击强化", 3, context)
            fightUtils.title_learn_branch("战斗", 5, "魔力强化", 3, context)
            fightUtils.title_learn_branch("战斗", 5, "生命强化", 3, context)
            context.run_task("Fight_ReturnMainWindow")

            OpenDetail = context.run_task("Bag_Open")
            if OpenDetail:
                time.sleep(1)
                for _ in range(2):
                    if fightUtils.findItem(
                        "武器大师执照", True, context, threshold=0.8
                    ):
                        break
        else:
            logger.info("需要手动结算，不放柱子直接暂离")
        # 压血相关
        # # 这里进夹层压血
        # if self.mars.target_earthgate_para >= 0:
        #     self.mars.gotoSpecialLayer(context)
        #     death = None
        #     for i in range(20):
        #         fightUtils.cast_magic("光", "祝福术", context)
        #         death = context.run_recognition(
        #             "Fight_FindRespawn",
        #             context.tasker.controller.post_screencap().wait().get(),
        #         )
        #         if death:
        #             logger.info(f"已死亡，准备出图")
        #             self.mars.isDeath = True
        #             context.run_task("Screenshot")
        #             break
        #         elif self.mars.layers == 99:
        #             logger.info(f"当前在99层，大概率无法死亡，走正常流程离开")
        #             time.sleep(3)
        #             context.run_task("Fight_ReturnMainWindow")
        #             self.mars.leaveSpecialLayer(context)
        #             context.run_task("Fight_ReturnMainWindow")
        #             context.run_task("Screenshot")
        #             break
        #         if i > 15:
        #             time.sleep(3)
        #             if not self.mars.Check_GridAndMonster(context, False):
        #                 context.run_task("Screenshot")
        #                 logger.info(f"怪物不在了，无法死亡，走正常流程离开")
        #                 time.sleep(3)
        #                 context.run_task("Fight_ReturnMainWindow")
        #                 self.mars.leaveSpecialLayer(context)
        #                 context.run_task("Fight_ReturnMainWindow")
        #                 context.run_task("Screenshot")
        #                 break
        #     context.run_task(
        #         "WaitStableNode_ForOverride",
        #         pipeline_override={
        #             "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 100}}
        #         },
        #     )
        #     if death:
        #         logger.info("可以出图了")
        #         context.run_task("Fight_FindLeaveText")
        #         time.sleep(3)
        #         if context.run_recognition(
        #             "ConfirmButton",
        #             context.tasker.controller.post_screencap().wait().get(),
        #         ):
        #             context.run_task("ConfirmButton")

        self.mars.isLeaveMaze = True
        # 到这可以出图了
