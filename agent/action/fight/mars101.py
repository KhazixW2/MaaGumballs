from math import floor
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger, send_message

from action.fight.fightUtils import timing_decorator
from action.fight import fightUtils
from action.fight import fightProcessor
from action.mars.mars_hp import MarsHPManager
from action.mars.mars_boss import MarsBossHandler
from action.mars.mars_title import MarsTitleManager
from action.mars.mars_special_layer import MarsSpecialLayerManager
from action.mars.mars_earth_gate import MarsEarthGateManager
from action.mars.mars_events import MarsEventDispatcher
from action.mars.mars_settlement import MarsSettlementManager

import time
import json


@AgentServer.custom_action("Mars101")
class Mars101(CustomAction):
    def __init__(self):
        super().__init__()
        self.useEarthGate = 0
        self.isGetTitanFoot = False
        self.isGetMagicAssist = False
        self.isUseMagicAssist = False
        self.is_android_skill_enabled = False
        self.isLeaveMaze = False
        self.is_demontitle_enable = False
        self.isDeath = False
        self.useDemon = 0
        self.layers = 1

    def initialize(self, context: Context):
        self.__init__()
        logger.info("马尔斯101初始化完成")
        # 检查当前层数
        context.run_task("Fight_ReturnMainWindow")
        RunResult = context.run_task("Fight_CheckLayer")
        if RunResult.nodes:
            self.layers = fightUtils.extract_num_layer(
                RunResult.nodes[0].recognition.best_result.text
            )

        # 进入地图初始化
        logger.info(f"当前层数: {self.layers}, 进入地图初始化")
        if fightUtils.check_magic_special("魔法助手", context):
            self.isGetMagicAssist = True
            logger.info(f"已获得魔法助手")
            if self.layers > self.target_leave_layer_para - 19:
                self.isUseMagicAssist = True
                logger.info(f"已开启魔法助手")

        if fightUtils.check_magic_special("泰坦之足", context):
            logger.info(f"已获得泰坦之足")
            self.isGetTitanFoot = True

        # 如果恶魔系称号期望开启，那么在初始化阶段启用手记获取称号
        if self.astrological_title_para:
            context.run_task("Fight_ReturnMainWindow")
            OpenDetail = context.run_task("Bag_Open")
            if OpenDetail:
                time.sleep(1)
                fightUtils.findItem("阿瑞斯的手记", True, context, threshold=0.8)
            time.sleep(1)

            if context.run_recognition(
                "Mars_GetDemonTitle_Confirm",
                context.tasker.controller.post_screencap().wait().get(),
            ).hit:
                taskdetail = context.run_task("Mars_GetDemonTitle_Confirm")
            else:
                taskdetail = context.run_task("Mars_GetDemonTitle_Confirm_2")
            if taskdetail.nodes and taskdetail.nodes[0].completed:
                logger.info("已获得恶魔系称号")
                self.is_demontitle_enable = True
            else:
                logger.info("获取恶魔系称号失败")

        if self.director_para:
            # 名导心得相关
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
                        "template": "fight/Mars/Mars_Director1.png"
                    }
                },
            )
            for _ in range(5):
                context.run_task("Mars_Director_ATK_Confirm")
            context.run_task("Fight_ReturnMainWindow")

        self.hp_manager = MarsHPManager(self)
        self.boss_handler = MarsBossHandler(self)
        self.title_manager = MarsTitleManager(self)
        self.special_layer_manager = MarsSpecialLayerManager(self)
        self.earth_gate_manager = MarsEarthGateManager(self)
        self.events_dispatcher = MarsEventDispatcher(self)
        self.settlement_manager = MarsSettlementManager(self)

    def Check_CurrentLayers(self, context: Context):
        tempLayers = fightUtils.handle_currentlayer_event(context)
        self.layers = tempLayers
        return True

    def Check_GridAndMonster(
        self, context: Context, clear=True, checkGrid=True, checkMonster=True
    ):
        """
        检查当前层是否有地板或者怪物残留
        :param context: 上下文对象
        :param clear: 是否清除残留
        :param checkGrid: 是否检查地板
        :param checkMonster: 是否检查怪物
        :return: 是否存在地板或者怪物
        """
        context.run_task(
            "WaitStableNode_ForOverride",
            pipeline_override={
                "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 100}}
            },
        )
        processor = fightProcessor.FightProcessor()
        if processor.checkGirdAndMonster(
            context,
            context.tasker.controller.post_screencap().wait().get(),
            checkGrid=checkGrid,
            checkMonster=checkMonster,
        ):
            if clear:
                logger.info("有地板或者怪物残留，再次清层")
                result = context.run_task(
                    "Mars_Fight_ClearCurrentLayer",
                    pipeline_override={
                        "Mars_Fight_ClearCurrentLayer": {
                            "custom_action_param": {"layers": self.layers}
                        }
                    },
                )
                # logger.info(f"再次清层结果: {result}")
            if checkMonster:
                logger.info("有怪物残留")
            if checkGrid:
                logger.info("有地板残留")
            return True
        logger.info("无地板或者怪物残留")
        # context.run_task("Screenshot")
        return False

    def Check_DefaultEquipment(self, context: Context):
        """
        检查默认装备
        1. 检查出图装备
        """
        if self.layers == 59:
            OpenDetail = context.run_task("Bag_Open")
            if OpenDetail.nodes:
                if not fightUtils.checkEquipment("腰带", 1, "贵族丝带", context):
                    fightUtils.findEquipment(1, "贵族丝带", True, context)
                if not fightUtils.checkEquipment("戒指", 2, "礼仪戒指", context):
                    fightUtils.findEquipment(2, "礼仪戒指", True, context)
                if not fightUtils.checkEquipment("披风", 3, "天鹅绒斗篷", context):
                    fightUtils.findEquipment(3, "天鹅绒斗篷", True, context)
                if not fightUtils.checkEquipment("宝物", 7, "冒险家竖琴", context):
                    fightUtils.findEquipment(7, "冒险家竖琴", True, context)
                time.sleep(1)
                context.run_task("Fight_ReturnMainWindow")
                logger.info(f"current layers {self.layers},装备检查完成")
            else:
                logger.info("背包打开失败")
                context.run_task("Fight_ReturnMainWindow")
                return False
        return True

    def Check_DefaultTitle(self, context: Context):
        """检查默认称号（委托给 MarsTitleManager）"""
        return self.title_manager.Check_DefaultTitle(context)

    def Check_DefaultStatus(self, context: Context):
        """检查冈布奥状态（委托给 MarsHPManager）"""
        return self.hp_manager.Check_DefaultStatus(context)

    def Get_CurrentHPStatus(self, context: Context):
        """获取当前HP百分比（委托给 MarsHPManager）"""
        return self.hp_manager.Get_CurrentHPStatus(context)

    @timing_decorator
    def Control_TenpecentHP(self, context: Context):
        """安全压血主逻辑（委托给 MarsHPManager）"""
        return self.hp_manager.Control_TenpecentHP(context)

    def Test_Stoneskin_Damage(self, context: Context, test_rounds: int):
        """测试石肤术伤害（委托给 MarsHPManager）"""
        return self.hp_manager.Test_Stoneskin_Damage(context, test_rounds)

    def handle_android_skill_event(self, context: Context):
        target_skill_list = ["外接皮", "生物导体"]
        if (
            self.layers == 5 or self.layers == 6
        ) and self.is_android_skill_enabled == False:
            for skill in target_skill_list:
                if skill == "外接皮":
                    target_skill_checkroi = [266, 605, 96, 96]
                if skill == "生物导体":
                    target_skill_checkroi = [550, 605, 96, 96]
                if context.run_recognition(
                    "Mars_Android_Skill",
                    context.tasker.controller.post_screencap().wait().get(),
                ).hit:
                    context.run_task(
                        "Mars_Android_Skill",
                        pipeline_override={
                            "Mars_Android_Skill_Choose": {
                                "expected": skill,
                            },
                            "Mars_Android_Skill_Choose_Fail": {
                                "roi": target_skill_checkroi
                            },
                            "Mars_Android_Skill_Choose_Success": {
                                "roi": target_skill_checkroi
                            },
                        },
                    )
                    self.is_android_skill_enabled = True
        context.run_task("Fight_ReturnMainWindow")
        return True

    def handle_boss_event(self, context: Context):
        """处理Boss层战斗（委托给 MarsBossHandler）"""
        return self.boss_handler.handle_boss_event(context)

    def handle_EarthGate_event(self, context: Context):
        """大地之门施放与等待（委托给 MarsEarthGateManager）"""
        return self.earth_gate_manager.handle_EarthGate_event(context)

    def handle_preLayers_event(self, context: Context):
        with fightUtils.timing_section("pre.inter_confirm"):
            if self.layers == 99 or self.layers == self.target_leave_layer_para:
                img = context.tasker.controller.post_screencap().wait().get()
                if context.run_recognition(
                    "Mars_Inter_Confirm_Success",
                    img,
                ).hit:
                    context.run_task("Mars_Inter_Confirm_Success")
        with fightUtils.timing_section("pre.skill_assist"):
            self.handle_android_skill_event(context)
            self.handle_UseMagicAssist_event(context)
        # 添加开场检查血量，防止意外
        with fightUtils.timing_section("pre.survival_buff"):
            if (
                self.layers > self.target_leave_layer_para - 20
            ) and self.layers % 10 != 0:
                self.Check_DefaultStatus(context)
                if not fightUtils.checkBuffStatus("寒冰护盾", context):
                    if self.layers > self.target_leave_layer_para - 10:
                        fightUtils.cast_magic("气", "静电场", context)
                        fightUtils.cast_magic("水", "寒冰护盾", context)
                        # 这里检查是否有远程怪物存在
                        if self.Check_GridAndMonster(
                            context, clear=False, checkGrid=False, checkMonster=True
                        ):
                            logger.info("当前层有远程怪物, 寒冰护盾替换成极光屏障")
                            if not fightUtils.cast_magic("水", "极光屏障", context):
                                fightUtils.cast_magic("水", "寒冰护盾", context)
                    else:
                        fightUtils.cast_magic("水", "寒冰护盾", context)
        # 在100~110层时释放地震，减少技能消耗，提高清层效率
        with fightUtils.timing_section("pre.earthquake"):
            if self.isUseMagicAssist and 100 < self.layers < 110:
                fightUtils.cast_magic("土", "地震术", context)
        # self.Check_DefaultEquipment(context)
        return True

    def handle_perfect_event(self, context: Context):
        # 检测完美击败
        if (self.layers % 2 == 1) and context.run_recognition(
            "Fight_Perfect", context.tasker.controller.post_screencap().wait().get()
        ).hit:
            logger.info(f"第{self.layers} 完美击败")
            while context.run_recognition(
                "Fight_Perfect",
                context.tasker.controller.post_screencap().wait().get(),
            ).hit:
                pass

    def handle_before_leave_maze_event(self, context: Context):
        """出图前结算（委托给 MarsSettlementManager）"""
        return self.settlement_manager.handle_before_leave_maze_event(context)

    def handle_MarsExchangeShop_event(self, context: Context, image):
        """交换商店事件（委托给 MarsEventDispatcher）"""
        return self.events_dispatcher.handle_MarsExchangeShop_event(context, image)

    def handle_MarsRuinsShop_event(self, context: Context, image):
        """商店事件（委托给 MarsEventDispatcher）"""
        return self.events_dispatcher.handle_MarsRuinsShop_event(context, image)

    def handle_MarsReward_event(self, context: Context, image=None):
        """奖励事件（委托给 MarsEventDispatcher）"""
        return self.events_dispatcher.handle_MarsReward_event(context, image)

    def handle_MarsBody_event(self, context: Context, image):
        """摸金/墓碑事件（委托给 MarsEventDispatcher）"""
        return self.events_dispatcher.handle_MarsBody_event(context, image)

    @timing_decorator
    def handle_MarsStele_event(self, context: Context, image):
        """斩断事件（委托给 MarsEventDispatcher）"""
        return self.events_dispatcher.handle_MarsStele_event(context, image)

    def handle_MarsStatue_event(self, context: Context, image=None):
        """白胡子老头献祭事件（委托给 MarsEventDispatcher）"""
        return self.events_dispatcher.handle_MarsStatue_event(context, image)

    def handle_SpecialLayer_event(self, context: Context, image):
        """处理休息室事件（委托给 MarsSpecialLayerManager）"""
        return self.special_layer_manager.handle_SpecialLayer_event(context, image)

    def handle_UseMagicAssist_event(self, context: Context):
        if (
            self.isGetMagicAssist
            # 大于100层就开启魔法助手
            and self.layers > 100
            and self.isUseMagicAssist == False
        ):
            logger.info("开启魔法助手帮助推图")
            fightUtils.cast_magic_special("魔法助手", context)
            self.isUseMagicAssist = True

    def handle_respawn_event(self, context: Context, image=None) -> bool:
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()
        if not context.run_recognition("Fight_FindRespawn", image).hit:
            return False
        logger.info("检测到死亡， 尝试小SL")
        fightUtils.Saveyourlife(context)
        fightUtils.cast_magic("水", "治疗术", context)
        fightUtils.cast_magic("土", "石肤术", context)
        return True

    def handle_postLayers_event(self, context: Context):
        # self.handle_perfect_event(context)
        # 等待画面稳定
        context.run_task(
            "WaitStableNode_ForOverride",
            pipeline_override={
                "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 100}}
            },
        )
        fightUtils.handle_dragon_event("马尔斯", context)
        with fightUtils.timing_section("post.default_status"):
            self.Check_DefaultStatus(context)
        # 检查默认装备，提升稳定性
        self.Check_DefaultEquipment(context)
        # 临时使用， 小恶魔活动结束直接删除即可
        if (
            # 距离出图楼层还有30层
            self.layers > self.target_leave_layer_para - 29
            and (self.layers - 1) % 10 == 0
        ):
            if self.is_demontitle_enable and self.useDemon < 3:
                fightUtils.openBagAndUseItem("小恶魔", True, context)
                self.useDemon += 1
            if (
                self.target_earthgate_para == 2
                and self.useEarthGate < self.target_earthgate_para
                and self.layers >= 100
                and self.target_leave_layer_para >= 129
            ):
                # 把当前的大地次数记作目标大地次数，不要尝试大地，提前出图
                self.target_earthgate_para = self.useEarthGate
                self.target_leave_layer_para = 119
        with fightUtils.timing_section("post.reward"):
            self.handle_MarsReward_event(context)
        context.run_task("Fight_ReturnMainWindow")

        image = context.tasker.controller.post_screencap().wait().get()
        with fightUtils.timing_section("post.body"):
            self.handle_MarsBody_event(context, image)
        with fightUtils.timing_section("post.ruins_shop"):
            self.handle_MarsRuinsShop_event(context, image)
        context.run_task("Fight_ReturnMainWindow")
        with fightUtils.timing_section("post.statue"):
            self.handle_MarsStatue_event(context, image)
        with fightUtils.timing_section("post.exchange_shop"):
            self.handle_MarsExchangeShop_event(context, image)
        # 点称号挪到战后，确保购买战利品有足够的探索点
        with fightUtils.timing_section("post.title"):
            self.Check_DefaultTitle(context)

        if self.handle_respawn_event(context, image):
            return False

        with fightUtils.timing_section("post.special_layer"):
            special_layer_ok = self.handle_SpecialLayer_event(context, image)
        if not special_layer_ok:
            # 如果卡剧情(离开),则返回False, 重新清理该层
            return False

        earth_gate_hit = self.handle_EarthGate_event(context)
        if earth_gate_hit:
            # 大地成功,需要回到战前准备开始清理该层，大地失败则继续往下走
            return False

        # 检测隐藏冈布奥
        hide_gumball_hit = False
        if self.layers >= 100:
            hide_gumball_hit = context.run_recognition(
                "Mars_HideGumball",
                context.tasker.controller.post_screencap().wait().get(),
            ).hit
        if hide_gumball_hit:
            # 识别到了隐藏冈布奥
            logger.info("检测到隐藏冈布奥")
            context.run_task("Mars_HideGumball")
            self.Check_DefaultStatus(context)
            context.run_task("Fight_OpenedDoor")
            logger.info("离开隐藏冈布奥夹层")
            context.run_task("Screenshot")
            return False
        # 重新清理当前层，防止影响出图层

        should_leave_maze = (self.layers >= self.target_leave_layer_para - 2) or (
            101 > self.layers > 97 and self.isGetMagicAssist == False
        )
        goto_special_layer_hit = False
        if should_leave_maze:
            goto_special_layer_hit = context.run_recognition(
                "Mars_GotoSpecialLayer",
                context.tasker.controller.post_screencap().wait().get(),
            ).hit
        if should_leave_maze and goto_special_layer_hit:
            with fightUtils.timing_section("post.before_leave"):
                self.handle_before_leave_maze_event(context)
        else:
            processor = fightProcessor.FightProcessor()
            if processor.get_last_door_kind(self.layers) == "opened":
                logger.debug("post.opened_door_check cached opened door hit")
                opened_door_hit = True
            else:
                opened_door_detail = context.run_recognition("Fight_OpenedDoor", image)
                opened_door_hit = bool(opened_door_detail and opened_door_detail.hit)
                if opened_door_hit:
                    processor.cache_door_from_box(
                        opened_door_detail.box, "opened", self.layers
                    )
            if not opened_door_hit:
                context.run_task(
                    "Mars_Fight_ClearCurrentLayer",
                    pipeline_override={
                        "Mars_Fight_ClearCurrentLayer": {
                            "custom_action_param": {"layers": self.layers}
                        }
                    },
                )
            if self.handle_respawn_event(context):
                return False
            logger.info("触发下楼事件")
            with fightUtils.timing_section("post.downstair"):
                fightUtils.handle_downstair_event(context)
        return True

    def handle_clearCurLayer_event(self, context: Context):
        # boss层开始探索
        if self.layers >= 30 and self.layers % 10 == 0:
            # boss召唤动作
            with fightUtils.timing_section("fight.boss"):
                if not self.handle_boss_event(context):
                    return False
        # 小怪层探索
        else:
            with fightUtils.timing_section("fight.normal_task_total"):
                context.run_task(
                    "Mars_Fight_ClearCurrentLayer",
                    pipeline_override={
                        "Mars_Fight_ClearCurrentLayer": {
                            "custom_action_param": {"layers": self.layers}
                        }
                    },
                )
        return True

    def handle_interrupt_event(self, context: Context):
        time.sleep(0.1)
        image = context.tasker.controller.post_screencap().wait().get()
        if self.handle_respawn_event(context, image):
            return False

        processor = fightProcessor.FightProcessor()
        if processor.checkGirdAndMonster(
            context, image, checkMonster=False, checkGrid=True
        ):
            logger.debug("当前截图仍有地板，本层重新探索")
            return False

        if context.run_recognition(
            "Mars_Inter_Confirm_Success",
            image,
        ).hit:
            logger.info("检测到卡剧情, 本层重新探索")
            context.run_task("Screenshot")
            context.run_task("Mars_Inter_Confirm_Success")
            return False

        if context.run_recognition(
            "Mars_Inter_Confirm_Fail",
            image,
        ).hit:
            if self.handle_respawn_event(context, image):
                return False
            logger.info("检测到卡离开, 本层重新探索")
            context.run_task("Mars_Inter_Confirm_Fail")
            return False

        # 检测卡返回
        if context.run_recognition("BackText", image).hit:
            logger.info("检测到卡返回, 本层重新探索")
            context.run_task("Screenshot")
            context.run_task("Fight_ReturnMainWindow")
            return False

        return True

    def gotoSpecialLayer(self, context: Context):
        """进入休息室（委托给 MarsSpecialLayerManager）"""
        return self.special_layer_manager.gotoSpecialLayer(context)

    def leaveSpecialLayer(self, context: Context):
        """离开休息室（委托给 MarsSpecialLayerManager）"""
        return self.special_layer_manager.leaveSpecialLayer(context)

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        self.target_leave_layer_para = int(
            context.get_node_data("Mars_Target_Layer_Setting")["recognition"]["param"][
                "expected"
            ][0]
        )
        self.target_earthgate_para = int(
            context.get_node_data("Mars_Target_Earthgate_Setting")["recognition"][
                "param"
            ]["expected"][0]
        )
        self.target_magicgumball_para = str(
            context.get_node_data("select_InputBox_Text2")["action"]["param"][
                "input_text"
            ]
        )
        self.astrological_title_para = (
            context.get_node_data("Mars_Astrological_Title_Setting")["recognition"][
                "param"
            ]["expected"][0]
        ).lower() == "true"
        self.director_para = (
            context.get_node_data("Mars_Director_Title_Setting")["recognition"][
                "param"
            ]["expected"][0]
        ).lower() == "true"
        self.manual_leave_para = context.get_node_data("Fight_ManualLeave")[
            "recognition"
        ]["param"]["expected"][0]
        logger.info(f"结算方式：{self.manual_leave_para}")
        # initialize
        self.initialize(context)
        logger.info(f"本次任务目标层数: {self.target_leave_layer_para}")

        while self.layers <= 159:
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)

            if self.handle_respawn_event(context):
                continue

            # 检查当前层数, 确保不是0层
            with fightUtils.timing_section("layer.current_check"):
                if not self.Check_CurrentLayers(context):
                    return CustomAction.RunResult(success=False)
            logger.info(f"Start Explore {self.layers} layer.")

            # 检测是否触发战前事件
            with fightUtils.timing_section("pre.layer"):
                self.handle_preLayers_event(context)

            # 探索当前层
            with fightUtils.timing_section("fight.layer_total"):
                clear_layer_ok = self.handle_clearCurLayer_event(context)
            if not clear_layer_ok:
                continue

            # 检查是否触发中断事件
            with fightUtils.timing_section("fight.interrupt_check"):
                interrupt_ok = self.handle_interrupt_event(context)
            if not interrupt_ok:
                continue

            # 检查是否触发战后事件, 战后事件是否出现异常
            with fightUtils.timing_section("post.layer"):
                post_layer_ok = self.handle_postLayers_event(context)
            if not post_layer_ok:
                continue
            if self.isLeaveMaze:
                logger.info(f"current layers {self.layers},出图准备完成,开始退出agent")
                break

        logger.info(f"马尔斯探索结束，当前到达{self.layers}层")

        # 手动结算·暂离
        if self.manual_leave_para in ["清怪暂离", "九柱暂离"]:
            time.sleep(1)
            context.run_task("Save_Status")
            send_message(
                "MaaGB",
                f"当前到达{self.layers}层，已暂离保存，请冒险者大人快来结算吧~",
            )
        else:
            context.run_task("Fight_LeaveMaze")

        # 获取并打印统计信息
        stats = fightUtils.get_time_statistics()
        for func_name, data in stats.items():
            logger.info(
                f"{func_name} 执行 {data['count']} 次，总耗时: {data['total_time']:.4f}秒"
            )
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Mars_Fight_ClearCurrentLayer")
class Mars_Fight_ClearCurrentLayer(CustomAction):

    def __init__(self):
        super().__init__()
        self.fightProcessor = fightProcessor.FightProcessor(target_wish="马尔斯")

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # 读取传入的层数参数（兼容 dict/对象）
        layers_arg = json.loads(argv.custom_action_param)["layers"]
        if layers_arg is not None:
            # logger.info(f"Mars_Fight_ClearCurrentLayer 接收到 layers={layers_arg}")
            try:
                # 作为变量传入处理器，后续可按需使用
                self.fightProcessor.layers = layers_arg
            except Exception:
                pass

        # 进行特殊配置以适应Mars
        self.fightProcessor.grid_count = 40
        self.fightProcessor.targetWish = "马尔斯"
        with fightUtils.timing_section("fight.normal_processor_total"):
            self.fightProcessor.clearCurrentLayer(context, isclearall=True)
        return CustomAction.RunResult(success=True)
