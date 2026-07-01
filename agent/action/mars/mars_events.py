from typing import TYPE_CHECKING

from maa.context import Context
from action.fight import fightUtils
from action.fight.fightUtils import timing_decorator
from utils import logger

if TYPE_CHECKING:
    from action.fight.mars101 import Mars101

import time


class MarsEventDispatcher:
    """马尔斯101事件分发器：统一处理Mars副本各类事件"""

    def __init__(self, mars: "Mars101") -> None:
        self.mars: "Mars101" = mars

    @timing_decorator
    def handle_MarsExchangeShop_event(self, context: Context, image):
        # MarsDagger : ExchangeForDagger
        # MarsHighLevelStaff : ExchangeForHighlevel
        # MarsMagicNecklace : ExchangeForHighlevel
        # 大于30层才处理交换商店事件
        target = None
        exchange_dir = "fight/Mars/MarsExchangeDir/ExchangeForDagger"
        if self.mars.layers >= 30 and self.mars.layers % 10 == 0:
            return True
        if (
            (self.mars.layers > 60) or (self.mars.useEarthGate > 0)
        ) and context.run_recognition("Mars_Exchange_Shop", image).hit:
            logger.info("触发Mars交换战利品事件")
            context.run_task("Mars_Exchange_Shop")
            nodedetail = context.run_task("Mars_Exchange_Shop_Check")
            if nodedetail:
                for node in nodedetail.nodes:
                    if node.name == "Mars_Exchange_Shop_Check_Dagger":
                        target = "短剑"
                        exchange_dir = "fight/Mars/MarsExchangeDir/ExchangeForDagger"
                        exchange_dir_2 = "fight/Mars/MarsExchangeDir/ExchangeForDagger"
                    elif node.name == "Mars_Exchange_Shop_Check_Highlevel_1":
                        target = "魔法伤害加成法杖"
                        exchange_dir = "fight/Mars/MarsExchangeDir/ExchangeForHighlevel"
                        exchange_dir_2 = (
                            "fight/Mars/MarsExchangeDir/ExchangeForHighlevel_2"
                        )
                    elif node.name == "Mars_Exchange_Shop_Check_Highlevel_2":
                        target = "魔法伤害加成项链"
                        exchange_dir = "fight/Mars/MarsExchangeDir/ExchangeForHighlevel"
                        exchange_dir_2 = (
                            "fight/Mars/MarsExchangeDir/ExchangeForHighlevel_2"
                        )
                if target:
                    logger.info(f"交换商店出现了{target}")
                    if context.run_recognition(
                        "Mars_Exchange_Shop_Add",
                        context.tasker.controller.post_screencap().wait().get(),
                    ).hit:
                        for _ in range(5):
                            context.run_task(
                                "Mars_Exchange_Shop_Add",
                                pipeline_override={
                                    "Mars_Exchange_Shop_Add_Equipment_Choose": {
                                        "template": exchange_dir
                                    },
                                    "Mars_Exchange_Shop_Add_Equipment_Choose_2": {
                                        "template": exchange_dir_2
                                    },
                                },
                            )
                            if context.run_recognition(
                                "Mars_Exchange_Shop_Add_Equipment_Select",
                                context.tasker.controller.post_screencap().wait().get(),
                            ).hit:
                                context.run_task(
                                    "Mars_Exchange_Shop_Add_Equipment_Select"
                                )
                            else:
                                logger.info("没有可供兑换的战利品了,跳过这次交换")
                                break

                            if AddButtonRecoDetail := context.run_recognition(
                                "Mars_Exchange_Shop_AddButtonReco",
                                context.tasker.controller.post_screencap().wait().get(),
                            ):
                                if AddButtonRecoDetail.hit:
                                    box = AddButtonRecoDetail.best_result.box
                                    for _ in range(10):
                                        context.tasker.controller.post_click(
                                            box[0] + box[2] // 2,
                                            box[1] + box[3] // 2,
                                        ).wait()
                                        time.sleep(0.02)
                            else:
                                logger.warning(
                                    "一般不会到这里,进入这里说明由于未知原因离开交换商店了。"
                                )
                            context.run_task("Mars_Exchange_Shop_Confirm_Exchange")

                            if context.run_recognition(
                                "Fight_MainWindow",
                                context.tasker.controller.post_screencap().wait().get(),
                            ).hit:
                                if target is not None:
                                    logger.info(f"已经交换了十把{target}~")
                                break
                            else:
                                logger.info("可用于更换的战利品没有了, 去获取更多吧~")
                else:
                    logger.info("这个交换商店没有任何目标战利品, 去其他楼层找吧~")
            context.run_task("Fight_ReturnMainWindow")
            return True

    @timing_decorator
    def handle_MarsRuinsShop_event(self, context: Context, image):
        if self.mars.layers >= 30 and self.mars.layers % 10 == 0:
            return True
        if context.run_recognition("Mars_RuinsShop", image).hit:
            logger.info("触发Mars商店事件")
            context.run_task("Mars_RuinsShop")
            return True
        return False

    @timing_decorator
    def handle_MarsReward_event(self, context: Context, image=None):
        normalReward = self.mars.layers % 2 == 1
        bossReward = self.mars.layers >= 30 and self.mars.layers % 10 == 0
        if not (normalReward or bossReward):
            return True
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()

        if normalReward:
            self.mars.handle_MarsStele_event(context, image)
            context.run_task(
                "WaitStableNode_ForOverride",
                pipeline_override={
                    "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 100}}
                },
            )
            self.mars.Check_GridAndMonster(context)
            for _ in range(5):
                if not context.run_recognition("Mars_Reward", image).hit:
                    logger.debug("当前截图中奖励可能被遮挡, 再次截图尝试")
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
            if context.run_recognition("Mars_Reward", image).hit:
                logger.info("触发Mars奖励事件")
                mars_reward_detail = context.run_task("Mars_Reward")
                if mars_reward_detail and mars_reward_detail.nodes[0].completed:
                    for node in mars_reward_detail.nodes:
                        if node.name == "Mars_Inter_Confirm_Fail":
                            logger.info("领取Mars奖励失败, 为了防止卡死, 跳过这次领取")
                            return False
                return True

        if bossReward and context.run_recognition("Mars_BossReward", image).hit:
            logger.info("触发MarsBoss奖励事件")
            context.run_task("Mars_BossReward")
            if self.mars.isGetTitanFoot == False and self.mars.layers >= 80:
                if fightUtils.cast_magic_special("泰坦之足", context):
                    self.mars.isGetTitanFoot = True
            if self.mars.isGetMagicAssist == False:
                if fightUtils.cast_magic_special("魔法助手", context):
                    self.mars.isGetMagicAssist = True
            return True
        return True

    @timing_decorator
    def handle_MarsBody_event(self, context: Context, image):
        if self.mars.layers >= 30 and self.mars.layers % 10 == 0:
            return True

        if bodyRecoDetail := context.run_recognition("Mars_Body", image):
            if not bodyRecoDetail.hit:
                return True

            logger.info("触发Mars摸金事件")
            for body in bodyRecoDetail.filtered_results:
                box = body.box
                context.tasker.controller.post_click(
                    box[0] + box[2] // 2,
                    box[1] + box[3] // 2,
                ).wait()
                context.run_task(
                    "WaitStableNode_ForOverride",
                    pipeline_override={
                        "WaitStableNode_ForOverride": {
                            "pre_wait_freezes": {"time": 100}
                        }
                    },
                )
                img = context.tasker.controller.post_screencap().wait().get()
                if context.run_recognition(
                    "Mars_Inter_Confirm_Success",
                    img,
                ).hit:
                    context.run_task("Mars_Inter_Confirm_Success")
                elif context.run_recognition("Mars_Inter_Confirm_Pickup", img).hit:
                    logger.info("触发墓碑事件")
                    context.run_task("Mars_Inter_Confirm_Pickup")
                    time.sleep(3)
                    context.run_task("Mars_Inter_Confirm_Success")
                    time.sleep(3)
                    context.run_task("Mars_Inter_Confirm_Success")
                else:
                    logger.info("可能在夹层中有怪物没有清理")
                    context.run_task("Mars_Inter_Confirm_Fail")
                    return False
            return True
        for _ in range(3):
            temp_is99 = self.mars.layers == 99
            temp_leave = self.mars.layers == self.mars.target_leave_layer_para
            temp_astrological = self.mars.astrological_title_para
            if not (temp_is99 or temp_leave or temp_astrological):
                break

            context.run_task("Screenshot")
            if context.run_recognition(
                "Mars_Tomb", context.tasker.controller.post_screencap().wait().get()
            ).hit:
                logger.info("触发墓碑事件")
                context.run_task("Mars_Tomb")
                time.sleep(3)
                context.run_task("Mars_Inter_Confirm_Success")
                context.run_task("Fight_ReturnMainWindow")
                break
            else:
                logger.info("没有触发墓碑事件, 等待1秒后重试")
                time.sleep(1)
        return True

    @timing_decorator
    def handle_MarsStele_event(self, context: Context, image):
        if context.run_recognition("Mars_Stele", image).hit:
            logger.info("触发Mars斩断事件")
            context.run_task("Mars_Stele")
            return True
        return False

    @timing_decorator
    def handle_MarsStatue_event(self, context: Context, image=None):
        if self.mars.layers >= 30 and self.mars.layers % 10 == 0:
            return False
        if self.mars.layers < 10 and self.mars.useEarthGate < 1:
            return False
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Mars_Statue", image).hit:
            logger.info(f"触发Mars白胡子老头事件, 献祭一下战利品吧~")
            if self.mars.useEarthGate > 0 and self.mars.layers < 80:
                logger.info(f"大地已回来，可以开始献祭至高战利品了")
                context.run_task(
                    "Mars_Statue",
                    pipeline_override={"Mars_Statue_Open_Next2": {"enabled": True}},
                )
            else:
                context.run_task(
                    "Mars_Statue",
                    pipeline_override={"Mars_Statue_Open_Next2": {"enabled": False}},
                )
            if self.mars.isGetTitanFoot == False and self.mars.layers > 80:
                if fightUtils.cast_magic_special("泰坦之足", context):
                    self.mars.isGetTitanFoot = True
            if self.mars.isGetMagicAssist == False:
                if fightUtils.cast_magic_special("魔法助手", context):
                    self.mars.isGetMagicAssist = True
            return True
        return False
