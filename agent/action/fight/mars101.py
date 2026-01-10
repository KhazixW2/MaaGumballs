from math import floor
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger, send_message

from action.fight.fightUtils import timing_decorator
from action.fight import fightUtils
from action.fight import fightProcessor

import time
import json


boss_x, boss_y = 360, 800
boss_slave_1_x, boss_slave_1_y = 100, 660
boss_slave_2_x, boss_slave_2_y = 640, 660
special_layer_monster_1_x, special_layer_monster_1_y = 90, 650
special_layer_monster_2_x, special_layer_monster_2_y = 363, 650


@AgentServer.custom_action("Mars101")
class Mars101(CustomAction):
    def __init__(self):
        super().__init__()
        self.isTitle_L1 = False
        self.isTitle_L10 = False
        self.isTitle_L61 = False
        self.isTitle_L86 = False
        self.useEarthGate = 0
        self.isGetDragonTitle = False
        self.isGetTitanFoot = False
        self.isGetMagicAssist = False
        self.isUseMagicAssist = False
        self.is_android_skill_enabled = False
        self.isLeaveMaze = False
        self.isAutoPickup = False
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
                "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 200}}
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

    @timing_decorator
    def Check_DefaultTitle(self, context: Context):
        """
        检查默认称号
        1. 检查1层的称号: 魔法学徒点满
        2. 检查28层称号: 点满符文师
        3. 检查61层的称号: 位面点满即可
        4. 检查86层的称号: 位面，大铸剑师，大剑师都点满
        """
        if (self.layers >= 1 and self.layers <= 3) and self.isTitle_L1 == False:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 4, context)
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L1 = True
            return True
        elif (self.layers >= 10 and self.layers <= 13) and self.isTitle_L10 == False:
            fightUtils.title_learn("冒险", 1, "寻宝者", 1, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 1, context)
            fightUtils.title_learn("冒险", 3, "符文师", 4, context)
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L10 = True
            return True
        elif (self.layers >= 61 and self.layers <= 63) and self.isTitle_L61 == False:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 1, context)
            fightUtils.title_learn("魔法", 2, "黑袍法师", 1, context)
            fightUtils.title_learn("魔法", 3, "咒术师", 2, context)
            fightUtils.title_learn("魔法", 4, "土系大师", 1, context)
            fightUtils.title_learn("魔法", 5, "位面先知", 1, context)
            fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "魔法强化", 3, context)
            context.run_task("Fight_ReturnMainWindow")

            self.isTitle_L61 = True
            return True

        elif (self.layers >= 86 and self.layers <= 88) and self.isTitle_L86 == False:
            fightUtils.title_learn("战斗", 1, "见习战士", 3, context)
            fightUtils.title_learn("战斗", 2, "战士", 3, context)
            fightUtils.title_learn("战斗", 3, "剑舞者", 3, context)
            fightUtils.title_learn("战斗", 4, "大剑师", 3, context)
            fightUtils.title_learn("魔法", 2, "黑袍法师", 3, context)
            # fightUtils.title_learn("魔法", 3, "咒术师", 3, context)
            # fightUtils.title_learn("魔法", 4, "土系大师", 3, context)
            fightUtils.title_learn("冒险", 1, "寻宝者", 2, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 2, context)
            if self.isTitle_L10 == False:
                fightUtils.title_learn("冒险", 3, "符文师", 3, context)
                self.isTitle_L10 = True
            # fightUtils.title_learn("冒险", 3, "符文师", 3, context)
            fightUtils.title_learn("冒险", 4, "武器大师", 3, context)
            fightUtils.title_learn("冒险", 5, "大铸剑师", 1, context)
            fightUtils.title_learn_branch("冒险", 5, "攻击强化", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "生命强化", 3, context)
            # fightUtils.title_learn_branch("冒险", 5, "魔法强化", 3, context)
            if self.astrological_title_para and self.is_demontitle_enable:
                logger.info("点了恶魔")
                fightUtils.title_learn("恶魔", 1, "堕落者", 1, context)
                fightUtils.title_learn("恶魔", 2, "下位恶魔", 3, context)
                fightUtils.title_learn("恶魔", 3, "中位恶魔", 3, context)
                fightUtils.title_learn("恶魔", 4, "上位恶魔", 3, context)
                fightUtils.title_learn("恶魔", 5, "恶魔大领主", 1, context)
                fightUtils.title_learn_branch("恶魔", 5, "攻击强化", 3, context)
                fightUtils.title_learn_branch(
                    "恶魔", 5, "攻击强化", 3, context, repeatable=True
                )
                fightUtils.title_learn_branch("恶魔", 5, "生命强化", 3, context)
            else:
                logger.info("没点恶魔")
            if fightUtils.title_check("巨龙", context):
                self.isGetDragonTitle = True
                fightUtils.title_learn("巨龙", 1, "亚龙血统", 3, context)
                fightUtils.title_learn("巨龙", 2, "初级龙族血统", 3, context)

            context.run_task("Fight_ReturnMainWindow")

            self.isTitle_L86 = True
            return True
        return False

    @timing_decorator
    def Check_DefaultStatus(self, context: Context):
        """检查冈布奥状态"""
        tempNum = self.layers % 10
        if (
            (11 <= self.layers <= 79) and (tempNum == 1 or tempNum == 5 or tempNum == 9)
        ) or self.layers >= 80:
            # 如果大地回来，低于60层就不检查状态
            if (self.layers <= 60) and self.useEarthGate > 0:
                return True
            cast_time = 0
            StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
            CurrentHP = float(StatusDetail["当前生命值"])
            MaxHp = float(StatusDetail["最大生命值"])
            HPStatus = CurrentHP / MaxHp
            logger.info(f"current hp is {CurrentHP}, HPStatus is {HPStatus}")

            if HPStatus < 0.8:
                if self.layers <= 60:
                    fightUtils.cast_magic_special("生命颂歌", context)
                if self.layers >= 110:
                    fightUtils.cast_magic("气", "静电场", context)
                cast_state = {"痊愈术": True, "神恩术": True, "治疗术": True}
                while HPStatus < 0.8:
                    cast_time += 1
                    # 防止禁疗状态下一直尝试治疗术，防止无限循环
                    if cast_time > 5:
                        break
                    if cast_state["痊愈术"]:
                        if not fightUtils.cast_magic("水", "痊愈术", context):
                            cast_state["痊愈术"] = False
                    elif cast_state["神恩术"]:
                        if not fightUtils.cast_magic("光", "神恩术", context):
                            cast_state["神恩术"] = False
                    elif not fightUtils.cast_magic("水", "治疗术", context):
                        logger.info("没有任何治疗方法了= =")
                        break
                    context.run_task("Fight_ReturnMainWindow")
                    StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
                    AfterHP = float(StatusDetail["当前生命值"])
                    MaxHp = float(StatusDetail["最大生命值"])
                    HPStatus = AfterHP / MaxHp
                    logger.info(f"current hp is {AfterHP}, HPStatus is {HPStatus}")
            else:
                logger.info("当前生命值大于80%，不使用治疗")

            # 保命
            if self.layers >= 51 and not fightUtils.checkBuffStatus(
                "神圣重生", context
            ):
                fightUtils.cast_magic("光", "神圣重生", context)
        return True

    def Get_CurrentHPStatus(self, context: Context):
        StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
        CurrentHP = float(StatusDetail["当前生命值"])
        MaxHp = float(StatusDetail["最大生命值"])
        HPStatus = CurrentHP / MaxHp
        return HPStatus

    def Control_TenpecentHP(self, context: Context):
        """
        尽可能压低目标血量，同时确保目标不会死亡。

        该函数先使用三次石肤术测试最大伤害，计算祝福术伤害为石肤术最大伤害的8倍，
        如果当前血量可以接受石肤术或者祝福术的最大伤害则释放对应法术，如果血量不满足则停止压血。

        整个过程中会记录石肤术和祝福术的实际伤害，并动态修正最大伤害值，以提高压血精度。

        Args:
            context: 战斗上下文对象

        Returns:
            float: 最终血量百分比，如果失败则返回特殊值
                  -1: 目标死亡
                  10000000: 技能可能被免疫
        """
        # 常量定义
        SAFETY_MARGIN = 0.08  # 安全余量，防止过度压血导致死亡
        MAX_ATTEMPTS = 20  # 最大尝试次数
        TEST_ROUNDS = 3  # 测试伤害的轮次
        MIN_CHANGE_THRESHOLD = 0.01  # 最小血量变化阈值（1%）
        CONSECUTIVE_STALL_LIMIT = 3  # 连续无变化最大次数
        BLESSING_DAMAGE_MULTIPLIER = 9  # 祝福术伤害是石肤术最大伤害的9倍
        DAMAGE_HISTORY_SIZE = 3  # 保留最近几次伤害记录用于计算平均值

        current_hp = self.Get_CurrentHPStatus(context)
        logger.info(f"开始安全压血操作，初始血量: {current_hp:.2%}")

        # 测试石肤术伤害
        _, max_stoneskin_damage = self.Test_Stoneskin_Damage(context, TEST_ROUNDS)
        if max_stoneskin_damage is None:
            logger.warning("测试未造成伤害，可能被免疫")
            return 10000000  # 测试失败，返回特殊值

        blessing_damage = max_stoneskin_damage * BLESSING_DAMAGE_MULTIPLIER

        logger.info(
            f"测试完成 - 石肤术初始最大伤害: {max_stoneskin_damage:.2%}, "
            f"祝福术初始预计伤害: {blessing_damage:.2%}"
        )
        # 测试石肤术伤害之后更新一下当前血量
        current_hp = self.Get_CurrentHPStatus(context)
        stoneskin_damage_history = []  # 石肤术伤害历史
        blessing_damage_history = []  # 祝福术伤害历史

        # 执行压血循环
        attempts = 0
        consecutive_no_change = 0

        while attempts < MAX_ATTEMPTS:
            # 计算安全可减少的血量（保留安全边界）
            safe_hp_to_reduce = current_hp - SAFETY_MARGIN

            if blessing_damage <= safe_hp_to_reduce and current_hp > 0.1:
                prev_hp = current_hp
                logger.info(
                    f"使用祝福术，当前血量: {current_hp:.2%}, 预计最大伤害: {blessing_damage:.2%}"
                )

                fightUtils.cast_magic("光", "祝福术", context)
                context.run_task("Fight_ReturnMainWindow")
                current_hp = self.Get_CurrentHPStatus(context)

                # 记录实际伤害并更新最大伤害值
                actual_damage = prev_hp - current_hp
                if actual_damage > 0:
                    blessing_damage_history.append(actual_damage)
                    if len(blessing_damage_history) > DAMAGE_HISTORY_SIZE:
                        blessing_damage_history.pop(0)

                    new_max_blessing = max(blessing_damage_history)
                    if new_max_blessing > blessing_damage:
                        logger.info(
                            f"祝福术最大伤害上调: {blessing_damage:.2%} -> {new_max_blessing:.2%}"
                        )
                        blessing_damage = new_max_blessing
                    elif new_max_blessing < blessing_damage * 0.8:
                        logger.info(
                            f"祝福术最大伤害下调: {blessing_damage:.2%} -> {new_max_blessing:.2%}"
                        )
                        blessing_damage = new_max_blessing
                    # 祝福术伤害调整不影响石肤术伤害预期

            # 检查是否可以使用石肤术
            elif max_stoneskin_damage <= safe_hp_to_reduce and current_hp > 0.1:
                # 石肤术伤害适中，不会导致死亡
                prev_hp = current_hp
                logger.info(
                    f"使用石肤术，当前血量: {current_hp:.2%}, 预计最大伤害: {max_stoneskin_damage:.2%}"
                )

                fightUtils.cast_magic("土", "石肤术", context)
                context.run_task("Fight_ReturnMainWindow")
                current_hp = self.Get_CurrentHPStatus(context)

                if current_hp <= 0:
                    logger.error("目标在压血过程中死亡，使用技能: 石肤术")
                    return -1

                # 记录实际伤害并更新最大伤害值
                actual_damage = prev_hp - current_hp
                if actual_damage > 0:
                    stoneskin_damage_history.append(actual_damage)
                    # 保持历史记录在指定大小
                    if len(stoneskin_damage_history) > DAMAGE_HISTORY_SIZE:
                        stoneskin_damage_history.pop(0)

                    # 更新石肤术最大伤害估计（使用历史最大值）
                    new_max_stoneskin = max(stoneskin_damage_history)
                    if new_max_stoneskin > max_stoneskin_damage:
                        logger.info(
                            f"石肤术最大伤害上调: {max_stoneskin_damage:.2%} -> {new_max_stoneskin:.2%}"
                        )
                        max_stoneskin_damage = new_max_stoneskin
                        # 不再使用石肤术的数据更新祝福术的伤害预期

            # 如果两种技能都可能导致死亡，则退出
            else:
                logger.info(
                    f"无法安全压血，当前血量: {current_hp:.2%}, 石肤术最大伤害: {max_stoneskin_damage:.2%}, 祝福术最大伤害: {blessing_damage:.2%}"
                )
                return current_hp

            # 检查血量变化
            hp_change = prev_hp - current_hp
            attempts += 1

            # 记录每次施法的效果
            if hp_change > 0:
                logger.info(f"造成伤害: {hp_change:.2%}, 当前血量: {current_hp:.2%}")
                consecutive_no_change = 0
            else:
                logger.warning(f"未造成伤害（可能被免疫），当前血量: {current_hp:.2%}")
                consecutive_no_change += 1

                # 如果连续无明显变化，提前结束
                if consecutive_no_change >= CONSECUTIVE_STALL_LIMIT:
                    logger.warning(
                        f"连续{CONSECUTIVE_STALL_LIMIT}次无明显变化，提前结束压血"
                    )
                    return current_hp

        # 最终检查
        if stoneskin_damage_history or blessing_damage_history:
            logger.info(f"压血完成，最终血量: {current_hp:.2%}，总施法次数: {attempts}")
            if stoneskin_damage_history:
                logger.info(
                    f"石肤术伤害记录: {[f'{d:.2%}' for d in stoneskin_damage_history]}, 最终最大伤害: {max_stoneskin_damage:.2%}"
                )
            if blessing_damage_history:
                logger.info(
                    f"祝福术伤害记录: {[f'{d:.2%}' for d in blessing_damage_history]}, 最终最大伤害: {blessing_damage:.2%}"
                )
        else:
            logger.info(
                f"压血完成，最终血量: {current_hp:.2%}，总施法次数: {attempts}，未记录到有效伤害"
            )

        return current_hp

    def Test_Stoneskin_Damage(self, context: Context, test_rounds: int) -> tuple:
        """测试石肤术的平均伤害和最大伤害。

        Args:
            context: 战斗上下文
            test_rounds: 测试轮次

        Returns:
            tuple: (avg_damage, max_damage) 或 (None, None) 如果失败
        """
        effective_casts = 0
        damage_values = []

        for _ in range(test_rounds):
            prev_hp = self.Get_CurrentHPStatus(context)
            fightUtils.cast_magic("土", "石肤术", context)
            context.run_task("Fight_ReturnMainWindow")
            current_hp = self.Get_CurrentHPStatus(context)

            if current_hp <= 0:
                logger.error("测试阶段目标死亡")
                return None, None

            if prev_hp > current_hp:
                damage = prev_hp - current_hp
                damage_values.append(damage)
                effective_casts += 1
                logger.debug(f"测试第{effective_casts}次，伤害: {damage:.2%}")

        if effective_casts == 0:
            return None, None

        avg_damage = sum(damage_values) / effective_casts
        max_damage = max(damage_values)

        return avg_damage, max_damage

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

    @timing_decorator
    def handle_boss_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_OpenedDoor", image).hit:
            return True

        else:
            context.run_task(
                "WaitStableNode_ForOverride",
                pipeline_override={
                    "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 200}}
                },
            )
            fightUtils.cast_magic_special("生命颂歌", context)
            if self.target_magicgumball_para == "波塞冬":
                fightUtils.cast_magic(
                    "水", "冰锥术", context, (boss_slave_1_x, boss_slave_1_y)
                )
                context.tasker.controller.post_click(
                    boss_slave_1_x, boss_slave_1_y
                ).wait()
                fightUtils.cast_magic(
                    "水", "冰锥术", context, (boss_slave_2_x, boss_slave_2_y)
                )
                context.tasker.controller.post_click(
                    boss_slave_2_x, boss_slave_2_y
                ).wait()
            else:
                fightUtils.cast_magic("光", "祝福术", context)
                context.tasker.controller.post_click(
                    boss_slave_1_x, boss_slave_1_y
                ).wait()
                time.sleep(2)
                context.tasker.controller.post_click(
                    boss_slave_2_x, boss_slave_2_y
                ).wait()
            fightUtils.cast_magic_special("生命颂歌", context)
            if self.layers >= 120:
                fightUtils.cast_magic("土", "石肤术", context, (boss_x, boss_y))
            fightUtils.cast_magic_special("生命颂歌", context)

            actions = []
            if self.target_magicgumball_para == "波塞冬":
                if self.layers < 110:
                    actions = [
                        lambda: fightUtils.cast_magic(
                            "水", "冰锥术", context, (boss_x, boss_y)
                        ),
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
                    ]
                elif self.layers >= 110 and self.layers <= 150:
                    actions = [
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
                        lambda: fightUtils.cast_magic(
                            "水", "冰锥术", context, (boss_x, boss_y)
                        ),
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
                    ]
            else:
                if self.layers <= 80:
                    actions = [
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
                    ]
                elif self.layers >= 90 and self.layers <= 150:
                    actions = [
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
                        lambda: fightUtils.cast_magic("水", "冰锥术", context),
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
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
                        "WaitStableNode_ForOverride": {
                            "pre_wait_freezes": {"time": 300}
                        }
                    },
                )

                # 检查boss是否存在
                if context.run_recognition(
                    "Fight_CheckBossStatus",
                    context.tasker.controller.post_screencap().wait().get(),
                ).hit:
                    logger.info(f"当前层数 {self.layers} 已经击杀boss")
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

        return True

    def handle_EarthGate_event(self, context: Context):
        """
        大地成功返回True,否则返回False
        """
        if (
            ((self.layers > 60) and (self.layers % 10 == 9))
            # 在61~63层时释放大地，或者x9(>60)层时释放大地
            or (61 <= self.layers <= 63)
        ) and self.useEarthGate < self.target_earthgate_para:
            # 识别是否门关着
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition("Fight_ClosedDoor", image).hit:
                logger.info("当前层无法释放大地，跳过")
                return False
            context.run_task("Fight_ReturnMainWindow")
            if fightUtils.check_magic("土", "大地之门", context):
                fightUtils.cast_magic("气", "静电场", context)
                if self.isUseMagicAssist:
                    # 关闭魔法助手, 节省卷轴
                    fightUtils.cast_magic_special("魔法助手", context)
                    self.isUseMagicAssist = False
                if fightUtils.cast_magic("土", "大地之门", context):
                    templayer = self.layers
                    for _ in range(10):
                        logger.info(f"等待大地之门特效结束")
                        self.Check_CurrentLayers(context)
                        if self.layers != templayer and self.layers != -1:
                            logger.info(f"大地之门特效结束, 当前层数为{self.layers}")
                            self.useEarthGate += 1
                            return True
                        time.sleep(1)
        return False

    @timing_decorator
    def handle_preLayers_event(self, context: Context):
        if self.layers == 99 or self.layers == self.target_leave_layer_para:
            img = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition(
                "Mars_Inter_Confirm_Success",
                img,
            ).hit:
                context.run_task("Mars_Inter_Confirm_Success")
        self.handle_android_skill_event(context)
        self.handle_UseMagicAssist_event(context)
        # 添加开场检查血量，防止意外
        if (self.layers > self.target_leave_layer_para - 20) and self.layers % 10 != 0:
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

    @timing_decorator
    def handle_before_leave_maze_event(self, context: Context):
        logger.info("触发Mars结算事件")
        context.run_task("Fight_ReturnMainWindow")
        if not self.manual_leave_para:
            # 名导心得相关
            if self.director_para:
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
            if self.isUseMagicAssist:
                fightUtils.cast_magic_special("魔法助手", context)
                self.isUseMagicAssist = False

            for _ in range(3):
                fightUtils.cast_magic_special("生命颂歌", context)

            self.gotoSpecialLayer(context)
            fightUtils.openBagAndUseItem("电能试剂", True, context)

            self.leaveSpecialLayer(context)
            context.run_task("Fight_ReturnMainWindow")
            for _ in range(3):
                fightUtils.cast_magic_special("生命颂歌", context)
            self.gotoSpecialLayer(context)
            fightUtils.openBagAndUseItem("能量电池", True, context)

            self.leaveSpecialLayer(context)
            context.run_task("Fight_ReturnMainWindow")
            for _ in range(3):
                fightUtils.cast_magic_special("生命颂歌", context)
            context.run_task("Screenshot")
            logger.info("截图保存检查柱子")
            fightUtils.title_learn("魔法", 3, "咒术师", 1, context)
            if fightUtils.title_check("巨龙", context):
                fightUtils.title_learn("巨龙", 1, "亚龙血统", 3, context)
                fightUtils.title_learn("巨龙", 2, "初级龙族血统", 3, context)
                if self.layers > 100:
                    fightUtils.title_learn("巨龙", 3, "中级龙族血统", 3, context)
                    fightUtils.title_learn("巨龙", 4, "高级龙族血统", 3, context)

                if self.useEarthGate > 1:
                    fightUtils.title_learn("巨龙", 5, "邪龙血统", 1, context)
                    fightUtils.title_learn_branch("巨龙", 5, "攻击强化", 3, context)
                    fightUtils.title_learn_branch(
                        "巨龙", 5, "攻击强化", 3, context, repeatable=True
                    )
                    fightUtils.title_learn_branch("巨龙", 5, "生命强化", 3, context)

            context.run_task("Fight_ReturnMainWindow")
            # 压血相关
            # # 这里进夹层压血
            # if self.target_earthgate_para >= 0 and self.is_demontitle_enable:
            #     self.gotoSpecialLayer(context)
            #     fightUtils.cast_magic("土", "石肤术", context)
            #     if not fightUtils.cast_magic("暗", "死亡波纹", context):
            #         if not fightUtils.cast_magic("火", " 末日审判", context):
            #             fightUtils.cast_magic("土", "地震术", context)

            #     for _ in range(20):
            #         if fightUtils.checkBuffStatus("神圣重生", context):
            #             logger.info("发现神圣重生buff, 使用祝福术尝试复活")
            #             fightUtils.cast_magic("光", "祝福术", context)
            #         else:
            #             time.sleep(5)
            #             break

            #     self.Control_TenpecentHP(context)
            #     # 增加截图调试
            #     context.run_task(
            #         "WaitStableNode_ForOverride",
            #         pipeline_override={
            #             "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 100}}
            #         },
            #     )
            #     context.run_task("Screenshot")
            #     self.leaveSpecialLayer(context)
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
            logger.info("需要手动结算")
        # 压血相关
        # # 这里进夹层压血
        # if self.target_earthgate_para >= 0:
        #     self.gotoSpecialLayer(context)
        #     death = None

        #     for i in range(20):
        #         fightUtils.cast_magic("光", "祝福术", context)
        #         death = context.run_recognition(
        #             "Fight_FindRespawn",
        #             context.tasker.controller.post_screencap().wait().get(),
        #         )
        #         if death:
        #             logger.info(f"已死亡，准备出图")
        #             self.isDeath = True
        #             context.run_task("Screenshot")
        #             break
        #         elif self.layers == 99:
        #             logger.info(f"当前在99层，大概率无法死亡，走正常流程离开")
        #             time.sleep(3)
        #             context.run_task("Fight_ReturnMainWindow")
        #             self.leaveSpecialLayer(context)
        #             context.run_task("Fight_ReturnMainWindow")
        #             context.run_task("Screenshot")
        #             break
        #         if i > 15:
        #             time.sleep(3)
        #             if not self.Check_GridAndMonster(context, False):
        #                 context.run_task("Screenshot")
        #                 logger.info(f"怪物不在了，无法死亡，走正常流程离开")
        #                 time.sleep(3)
        #                 context.run_task("Fight_ReturnMainWindow")
        #                 self.leaveSpecialLayer(context)
        #                 context.run_task("Fight_ReturnMainWindow")
        #                 context.run_task("Screenshot")
        #                 break

        #     # 增加截图调试
        #     context.run_task(
        #         "WaitStableNode_ForOverride",
        #         pipeline_override={
        #             "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 100}}
        #         },
        #     )
        #     if death:
        #         logger.info("可以出图了")
        #         context.run_task("Fight_FindLeaveText")
        #         # 等待6秒
        #         time.sleep(6)
        #         if context.run_recognition(
        #             "ConfirmButton",
        #             context.tasker.controller.post_screencap().wait().get(),
        #         ):
        #             context.run_task("ConfirmButton")

        self.isLeaveMaze = True
        # 到这可以出图了

    @timing_decorator
    def handle_MarsExchangeShop_event(self, context: Context, image):
        # MarsDagger : ExchangeForDagger
        # MarsHighLevelStaff : ExchangeForHighlevel
        # MarsMagicNecklace : ExchangeForHighlevel
        # 大于10层才处理交换商店事件
        target = None
        exchange_dir = "fight/Mars/MarsExchangeDir/ExchangeForDagger"
        if self.layers >= 30 and self.layers % 10 == 0:
            return True
        if (
            self.layers > 10
            and context.run_recognition("Mars_Exchange_Shop", image).hit
        ):
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
                            # context.run_task("Screenshot")
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

                            # 如果交换完已经在桌面了，说明10个短剑都交换完了
                            if context.run_recognition(
                                "Fight_MainWindow",
                                context.tasker.controller.post_screencap().wait().get(),
                            ).hit:
                                if target != None:
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
        if self.layers >= 30 and self.layers % 10 == 0:
            return True
        if context.run_recognition("Mars_RuinsShop", image).hit:
            logger.info("触发Mars商店事件")
            context.run_task("Mars_RuinsShop")
            return True
        return False

    @timing_decorator
    def handle_MarsReward_event(self, context: Context, image=None):
        normalReward = self.layers % 2 == 1
        bossReward = self.layers >= 30 and self.layers % 10 == 0
        if not (normalReward or bossReward):
            return True
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()

        if normalReward:
            self.handle_MarsStele_event(context, image)
            context.run_task(
                "WaitStableNode_ForOverride",
                pipeline_override={
                    "WaitStableNode_ForOverride": {"pre_wait_freezes": {"time": 100}}
                },
            )
            self.Check_GridAndMonster(context)
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
        if normalReward and context.run_recognition("Mars_Reward", image).hit:
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
            if self.isGetTitanFoot == False and self.layers >= 80:
                if fightUtils.cast_magic_special("泰坦之足", context):
                    self.isGetTitanFoot = True
                    # 关闭泰坦
            if self.isGetMagicAssist == False:
                if fightUtils.cast_magic_special("魔法助手", context):
                    self.isGetMagicAssist = True
                    # 关闭魔法助手
            return True
        return True

    @timing_decorator
    def handle_MarsBody_event(self, context: Context, image):
        if self.layers >= 30 and self.layers % 10 == 0:
            return True

        # 摸金事件卡返回基本只会发生在夹层中
        if bodyRecoDetail := context.run_recognition("Mars_Body", image):
            if bodyRecoDetail.hit:
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
            if self.astrological_title_para == False:
                # 不开启恶魔称号基本不用考虑墓碑压血
                break
            if self.layers == 99 or self.layers == self.target_leave_layer_para:
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
                    time.sleep(1)
            else:
                break
        return True

    @timing_decorator
    def handle_MarsStele_event(self, context: Context, image):
        if self.layers >= 30 and self.layers % 10 == 0:
            return True
        if self.layers % 2 == 1 and context.run_recognition("Mars_Stele", image).hit:
            logger.info("触发Mars斩断事件")
            context.run_task("Mars_Stele")
            return True
        return False

    @timing_decorator
    def handle_MarsStatue_event(self, context: Context, image=None):
        if self.layers >= 30 and self.layers % 10 == 0:
            return False
        if self.layers < 10 and self.useEarthGate < 1:
            return False
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Mars_Statue", image).hit:
            logger.info(f"触发Mars白胡子老头事件, 献祭一下战利品吧~")
            if self.useEarthGate > 0 and self.layers < 80:
                # 说明大地回来了，可以开始献祭至高战利品了
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
            if self.isGetTitanFoot == False and self.layers > 80:
                if fightUtils.cast_magic_special("泰坦之足", context):
                    self.isGetTitanFoot = True
                    # 关闭泰坦
            if self.isGetMagicAssist == False:
                if fightUtils.cast_magic_special("魔法助手", context):
                    self.isGetMagicAssist = True
                    # 关闭魔法助手
            return True
        return False

    @timing_decorator
    def handle_SpecialLayer_event(self, context: Context, image):
        # 波塞冬不放柱子，用冰锥打裸男
        if (30 <= self.layers + 1 <= 150) and ((self.layers + 1) % 10 == 0):
            for _ in range(5):
                if not context.run_recognition("Mars_GotoSpecialLayer", image).hit:
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
            if not self.gotoSpecialLayer(context):
                return False
            if self.isUseMagicAssist:
                fightUtils.cast_magic("土", "石肤术", context)
            if self.layers < 100:
                context.run_task("Mars_Shower")
            context.run_task("Mars_EatBread")
            if self.target_magicgumball_para == "波塞冬":
                if self.layers <= 89:
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
            self.Check_DefaultStatus(context)

            return True
        return True

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

    def handle_auto_pickup_event(self, context: Context):
        logger.info("开启自动拾取, 等待动画结束")
        context.run_task("Fight_PickUpAll_Emptyfloor")
        self.isAutoPickup = True

    @timing_decorator
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
        self.handle_MarsReward_event(context)
        context.run_task("Fight_ReturnMainWindow")

        image = context.tasker.controller.post_screencap().wait().get()
        self.handle_MarsBody_event(context, image)
        self.handle_MarsRuinsShop_event(context, image)
        context.run_task("Fight_ReturnMainWindow")
        self.handle_MarsStatue_event(context, image)
        self.handle_MarsExchangeShop_event(context, image)
        # 点称号挪到战后，确保购买战利品有足够的探索点
        self.Check_DefaultTitle(context)

        if context.run_recognition("Fight_FindRespawn", image).hit:
            logger.info("检测到死亡， 尝试小SL")
            fightUtils.Saveyourlife(context)
            fightUtils.cast_magic("水", "治疗术", context)
            fightUtils.cast_magic("土", "石肤术", context)
            return False

        if not self.handle_SpecialLayer_event(context, image):
            # 如果卡剧情(离开),则返回False, 重新清理该层
            return False

        if self.handle_EarthGate_event(context):
            # 大地成功,需要回到战前准备开始清理该层，大地失败则继续往下走
            return False

        # 检测隐藏冈布奥
        if (
            self.layers >= 90
            and context.run_recognition(
                "Mars_HideGumball",
                context.tasker.controller.post_screencap().wait().get(),
            ).hit
        ):
            # 识别到了隐藏冈布奥
            logger.info("检测到隐藏冈布奥")
            context.run_task("Mars_HideGumball")
            self.Check_DefaultStatus(context)
            context.run_task("Fight_OpenedDoor")
            logger.info("离开隐藏冈布奥夹层")
            context.run_task("Screenshot")
            return False
        # 重新清理当前层，防止影响出图层

        if (
            (self.layers >= self.target_leave_layer_para - 2)
            # 到了99层依然没有获得魔法助手就结算
            or (101 > self.layers > 97 and self.isGetMagicAssist == False)
        ) and context.run_recognition(
            "Mars_GotoSpecialLayer",
            context.tasker.controller.post_screencap().wait().get(),
        ).hit:
            self.handle_before_leave_maze_event(context)
        else:
            if self.isAutoPickup == self.target_autopickup_para:
                if not context.run_recognition("Fight_OpenedDoor", image).hit:
                    context.run_task(
                        "Mars_Fight_ClearCurrentLayer",
                        pipeline_override={
                            "Mars_Fight_ClearCurrentLayer": {
                                "custom_action_param": {"layers": self.layers}
                            }
                        },
                    )
                if context.run_recognition(
                    "Fight_FindRespawn",
                    context.tasker.controller.post_screencap().wait().get(),
                ).hit:
                    logger.info("下楼事件前检测到死亡， 尝试小SL")
                    fightUtils.Saveyourlife(context)
                    fightUtils.cast_magic("水", "治疗术", context)
                    fightUtils.cast_magic("土", "石肤术", context)
                    return False
                logger.info("触发下楼事件")
                fightUtils.handle_downstair_event(context)
            else:
                logger.info("触发开启自动拾取事件")
                self.handle_auto_pickup_event(context)
        return True

    @timing_decorator
    def handle_clearCurLayer_event(self, context: Context):
        # boss层开始探索
        if self.layers >= 30 and self.layers % 10 == 0:
            # boss召唤动作
            if not self.handle_boss_event(context):
                return False
        # 小怪层探索
        else:
            context.run_task(
                "Mars_Fight_ClearCurrentLayer",
                pipeline_override={
                    "Mars_Fight_ClearCurrentLayer": {
                        "custom_action_param": {"layers": self.layers}
                    }
                },
            )
        return True

    @timing_decorator
    def handle_interrupt_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_FindRespawn", image).hit:
            logger.info("检测到死亡， 尝试小SL")
            fightUtils.Saveyourlife(context)
            fightUtils.cast_magic("水", "治疗术", context)
            fightUtils.cast_magic("土", "石肤术", context)
            return False

        if context.run_recognition(
            "Mars_Inter_Confirm_Success",
            image,
        ).hit:
            logger.info("检测到卡剧情, 本层重新探索")
            context.run_task("Mars_Inter_Confirm_Success")
            return False

        if context.run_recognition(
            "Mars_Inter_Confirm_Fail",
            image,
        ).hit:
            if context.run_recognition("Fight_FindRespawn", image).hit:
                logger.info("检测到死亡， 尝试小SL")
                fightUtils.Saveyourlife(context)
                fightUtils.cast_magic("水", "治疗术", context)
                fightUtils.cast_magic("土", "石肤术", context)
                return False
            logger.info("检测到卡离开, 本层重新探索")
            context.run_task("Mars_Inter_Confirm_Fail")
            return False

        # 检测卡返回
        if context.run_recognition("BackText", image).hit:
            logger.info("检测到卡返回, 本层重新探索")
            context.run_task("Fight_ReturnMainWindow")
            return False

        return True

    def gotoSpecialLayer(self, context: Context):
        context.run_task("Fight_ReturnMainWindow")
        time.sleep(1)
        if context.run_recognition(
            "Mars_GotoSpecialLayer",
            context.tasker.controller.post_screencap().wait().get(),
        ).hit:

            context.run_task("Mars_GotoSpecialLayer")
            for _ in range(10):
                if context.run_recognition(
                    "Mars_GotoSpecialLayer_Confirm",
                    context.tasker.controller.post_screencap().wait().get(),
                ).hit:
                    context.run_task("Mars_GotoSpecialLayer_Confirm")
                    break
                if context.run_recognition(
                    "Mars_Inter_Confirm_Fail",
                    context.tasker.controller.post_screencap().wait().get(),
                ).hit:
                    context.run_task("Mars_Inter_Confirm_Fail")
                    logger.info("进入休息室失败, 需要重新清理当前层")
                    return False
                time.sleep(1)

            while not context.run_recognition(
                "Mars_LeaveSpecialLayer",
                context.tasker.controller.post_screencap().wait().get(),
            ).hit:
                time.sleep(1)
            logger.info("进入休息室")
            return True
        return True

    def leaveSpecialLayer(self, context: Context):
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
        self.target_autopickup_para = bool(
            context.get_node_data("Fight_PickUpAll_Emptyfloor")["enabled"]
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
        self.manual_leave_para = bool(
            context.get_node_data("Fight_ManualLeave")["enabled"]
        )
        logger.info(f"手动结算：{self.manual_leave_para}")
        # initialize
        self.initialize(context)
        logger.info(f"本次任务目标层数: {self.target_leave_layer_para}")

        while self.layers <= 159:
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)

            # 检查当前层数, 确保不是0层
            if not self.Check_CurrentLayers(context):
                return CustomAction.RunResult(success=False)
            logger.info(f"Start Explore {self.layers} layer.")

            # 检测是否触发战前事件
            self.handle_preLayers_event(context)

            # 探索当前层
            if not self.handle_clearCurLayer_event(context):
                continue

            # 检查是否触发中断事件
            if not self.handle_interrupt_event(context):
                continue

            # 检查是否触发战后事件, 战后事件是否出现异常
            if not self.handle_postLayers_event(context):
                continue
            if self.isLeaveMaze:
                logger.info(f"current layers {self.layers},出图准备完成,开始退出agent")
                break

        logger.info(f"马尔斯探索结束，当前到达{self.layers}层")

        # 手动结算·暂离
        if self.manual_leave_para:
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
        self.fightProcessor.clearCurrentLayer(context, isclearall=True)
        return CustomAction.RunResult(success=True)
