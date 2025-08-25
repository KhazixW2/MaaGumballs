from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger

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
        self.isTitle_L28 = False
        self.isTitle_L58 = False
        self.isTitle_L76 = False
        self.useEarthGate = 0
        self.isGetTitanFoot = False
        self.isGetMagicAssist = False
        self.isUseMagicAssist = False
        self.is_android_skill_enabled = False
        self.isLeaveMaze = False
        self.isAutoPickup = False
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
        # 初始化魔法助手状态
        if fightUtils.check_magic_special("魔法助手", context):
            self.isGetMagicAssist = True
            logger.info(f"已获得魔法助手")
            if self.layers > self.target_leave_layer_para - 19:
                self.isUseMagicAssist = True
                logger.info(f"已开启魔法助手")
        # 初始化泰坦之足状态
        if fightUtils.check_magic_special("泰坦之足", context):
            logger.info(f"已获得泰坦之足")
            self.isGetTitanFoot = True

    def Check_CurrentLayers(self, context: Context):
        tempLayers = fightUtils.handle_currentlayer_event(context)
        self.layers = tempLayers
        return True

    def Check_DefaultEquipment(self, context: Context):
        """
        检查默认装备
        1. 检查出图装备
        """
        if self.layers == 51:
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
                return False
        return True

    def Check_DefaultTitle(self, context: Context):
        """
        检查默认称号
        1. 检查1层的称号: 魔法学徒点满
        2. 检查28层称号: 点满符文师
        3. 检查58层的称号: 位面点满即可
        4. 检查76层的称号: 位面，大铸剑师，大剑师都点满
        """
        if (self.layers >= 1 and self.layers <= 3) and self.isTitle_L1 == False:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 3, context)
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L1 = True
            return True
        elif (self.layers >= 28 and self.layers <= 33) and self.isTitle_L28 == False:
            fightUtils.title_learn("冒险", 1, "寻宝者", 1, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 1, context)
            fightUtils.title_learn("冒险", 3, "符文师", 3, context)
            self.isTitle_L28 = True
            return True
        elif (self.layers >= 58 and self.layers <= 63) and self.isTitle_L58 == False:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 3, context)
            fightUtils.title_learn("魔法", 2, "黑袍法师", 3, context)
            fightUtils.title_learn("魔法", 3, "咒术师", 1, context)
            fightUtils.title_learn("魔法", 4, "土系大师", 1, context)
            fightUtils.title_learn("魔法", 5, "位面先知", 1, context)
            fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "魔法强化", 3, context)
            context.run_task("Fight_ReturnMainWindow")

            context.run_task("Save_Status")
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L58 = True
            return True

        elif (self.layers >= 76 and self.layers <= 81) and self.isTitle_L76 == False:
            fightUtils.title_learn("战斗", 1, "见习战士", 3, context)
            fightUtils.title_learn("战斗", 2, "战士", 3, context)
            fightUtils.title_learn("战斗", 3, "剑舞者", 3, context)
            fightUtils.title_learn("战斗", 4, "大剑师", 3, context)
            fightUtils.title_learn("魔法", 2, "黑袍法师", 3, context)
            # fightUtils.title_learn("魔法", 3, "咒术师", 3, context)
            # fightUtils.title_learn("魔法", 4, "土系大师", 3, context)
            fightUtils.title_learn("冒险", 1, "寻宝者", 3, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 3, context)
            # fightUtils.title_learn("冒险", 3, "符文师", 3, context)
            fightUtils.title_learn("冒险", 4, "武器大师", 3, context)
            fightUtils.title_learn("冒险", 5, "大铸剑师", 1, context)
            fightUtils.title_learn_branch("冒险", 5, "攻击强化", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "生命强化", 3, context)
            # fightUtils.title_learn_branch("冒险", 5, "魔法强化", 3, context)
            if self.astrological_title_para:
                fightUtils.title_learn("占星", 1, "占星学徒", 1, context)
                fightUtils.title_learn("占星", 2, "星象观测者", 3, context)
                fightUtils.title_learn("占星", 3, "星象守卫", 3, context)
                fightUtils.title_learn("占星", 4, "星辰守望者", 3, context)
                fightUtils.title_learn("占星", 5, "星界裁决者", 1, context)
                fightUtils.title_learn_branch("占星", 5, "攻击强化", 3, context)
                fightUtils.title_learn_branch("占星", 5, "生命强化", 3, context)

            context.run_task("Fight_ReturnMainWindow")
            context.run_task("Save_Status")
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L76 = True
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
            StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
            CurrentHP = float(StatusDetail["当前生命值"])
            MaxHp = float(StatusDetail["最大生命值"])
            HPStatus = CurrentHP / MaxHp
            logger.info(f"current hp is {CurrentHP}, HPStatus is {HPStatus}")

            if HPStatus < 0.8:
                if self.layers <= 60:
                    fightUtils.cast_magic_special("生命颂歌", context)
                while HPStatus < 0.8:
                    if not fightUtils.cast_magic("水", "治疗术", context):
                        if not fightUtils.cast_magic("水", "治愈术", context):
                            if not fightUtils.cast_magic("光", "神恩术", context):
                                logger.info("没有任何治疗方法了= =")
                                break
                    context.run_task("Fight_ReturnMainWindow")
                    StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
                    AfterHP = float(StatusDetail["当前生命值"])
                    MaxHp = float(StatusDetail["最大生命值"])
                    HPStatus = AfterHP / MaxHp
                    logger.info(f"current hp is {AfterHP}, HPStatus is {HPStatus}")
                    if AfterHP == CurrentHP:
                        logger.info("当前生命值没有变化，使用痊愈术或者神恩术")
                        if not fightUtils.cast_magic("水", "治愈术", context):
                            if not fightUtils.cast_magic("光", "神恩术", context):
                                logger.info("没有任何治疗方法了= =")
                                break
            else:
                logger.info("当前生命值大于80%，不使用治疗")

            # 保命
            if self.layers >= 51 and not fightUtils.checkBuffStatus(
                "神圣重生", context
            ):
                fightUtils.cast_magic("光", "神圣重生", context)
        return True

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
                ):
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

    def handle_boss_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_OpenedDoor", image):
            if context.run_recognition("Mars_BossReward", image):
                self.handle_MarsReward_event(context, image)
            context.run_task("Fight_OpenedDoor")
        else:
            time.sleep(6)
            fightUtils.cast_magic_special("生命颂歌", context)
            if self.target_magicgumball_para == "波塞冬" and (self.useEarthGate > 0):

                fightUtils.cast_magic("气", "静电场", context)
                fightUtils.cast_magic(
                    "水", "冰锥术", context, (boss_slave_1_x, boss_slave_1_y)
                )
                fightUtils.cast_magic(
                    "水", "冰锥术", context, (boss_slave_2_x, boss_slave_2_y)
                )
            else:
                fightUtils.cast_magic("光", "祝福术", context)
                context.tasker.controller.post_click(
                    boss_slave_1_x, boss_slave_1_y
                ).wait()
                time.sleep(3)
                context.tasker.controller.post_click(
                    boss_slave_2_x, boss_slave_2_y
                ).wait()
                time.sleep(1)
            fightUtils.cast_magic_special("生命颂歌", context)
            fightUtils.cast_magic_special("生命颂歌", context)

            actions = []
            if self.target_magicgumball_para == "波塞冬":
                if self.layers == 60 and self.useEarthGate == 0:
                    logger.info("波塞冬阵容,59层出现拉绳子,无大地到达60层")
                    actions = [
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
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
                elif self.layers < 100:
                    actions = [
                        lambda: fightUtils.cast_magic(
                            "水", "冰锥术", context, (boss_x, boss_y)
                        ),
                        lambda: context.tasker.controller.post_click(
                            boss_x, boss_y
                        ).wait(),
                    ]
                elif self.layers >= 100 and self.layers <= 120:
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
                elif self.layers >= 90 and self.layers <= 120:
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
                actions[index]()
                time.sleep(1)

                # 检查boss是否存在
                if context.run_recognition(
                    "Fight_CheckBossStatus",
                    context.tasker.controller.post_screencap().wait().get(),
                ):
                    logger.info(f"当前层数 {self.layers} 已经击杀boss")
                    break

                index = (index + 1) % len(actions)

            # 捡东西
            time.sleep(1)
            self.handle_MarsReward_event(
                context, image=context.tasker.controller.post_screencap().wait().get()
            )
            if self.isGetTitanFoot == False and self.layers >= 80:
                if fightUtils.cast_magic_special("泰坦之足", context):
                    self.isGetTitanFoot = True
                    # 关闭泰坦之足
            if self.isGetMagicAssist == False:
                if fightUtils.cast_magic_special("魔法助手", context):
                    self.isGetMagicAssist = True
                    # 关闭魔法助手
            context.run_task("Fight_OpenedDoor")
        return True

    def handle_EarthGate_event(self, context: Context):
        """
        大地成功返回True,否则返回False
        """
        if (
            ((self.layers > 50) and (self.layers % 10 == 9))
            # 如果59遇到拉绳子无法大地，那么尝试在61或者62大地
            or (61 <= self.layers <= 62)
        ) and self.useEarthGate < self.target_earthgate_para:
            # 识别释放大地时没有拉绳子的洞
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition(
                "FindKeyHole", image
            ) and context.run_recognition("Fight_ClosedDoor", image):
                logger.info("当前层无法释放大地，跳过")
                return False
            time.sleep(1)
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

    def handle_preLayers_event(self, context: Context):
        self.handle_android_skill_event(context)
        self.handle_UseMagicAssist_event(context)
        # 添加开场检查血量，防止意外
        if (self.layers > self.target_leave_layer_para - 10) and self.layers % 10 != 0:
            self.Check_DefaultStatus(context)
            for _ in range(2):
                fightUtils.cast_magic("水", "寒冰护盾", context)

        # self.Check_DefaultEquipment(context)
        return True

    def handle_perfect_event(self, context: Context):
        # 检测完美击败
        if (self.layers % 2 == 1) and context.run_recognition(
            "Fight_Perfect", context.tasker.controller.post_screencap().wait().get()
        ):
            logger.info(f"第{self.layers} 完美击败")
            while context.run_recognition(
                "Fight_Perfect",
                context.tasker.controller.post_screencap().wait().get(),
            ):
                pass

    def handle_before_leave_maze_event(self, context: Context):
        logger.info("触发Mars结算事件")
        context.run_task("Fight_ReturnMainWindow")
        for _ in range(3):
            fightUtils.cast_magic_special("生命颂歌", context)

        self.gotoSpecialLayer(context)
        context.run_task("Fight_ReturnMainWindow")
        OpenDetail = context.run_task("Bag_Open")
        if OpenDetail:
            time.sleep(1)
            fightUtils.findItem("电能试剂", True, context)
        time.sleep(1)

        self.leaveSpecialLayer(context)
        context.run_task("Fight_ReturnMainWindow")
        for _ in range(3):
            fightUtils.cast_magic_special("生命颂歌", context)
        self.gotoSpecialLayer(context)
        context.run_task("Fight_ReturnMainWindow")
        OpenDetail = context.run_task("Bag_Open")
        if OpenDetail:
            time.sleep(1)
            fightUtils.findItem("能量电池", True, context)
        time.sleep(1)

        self.leaveSpecialLayer(context)
        context.run_task("Fight_ReturnMainWindow")
        for _ in range(3):
            fightUtils.cast_magic_special("生命颂歌", context)

        if fightUtils.title_check("巨龙", context):
            fightUtils.title_learn("巨龙", 1, "亚龙血统", 3, context)
            fightUtils.title_learn("巨龙", 2, "初级龙族血统", 3, context)
            fightUtils.title_learn("巨龙", 3, "中级龙族血统", 3, context)
            fightUtils.title_learn("巨龙", 4, "高级龙族血统", 3, context)
        context.run_task("Fight_ReturnMainWindow")

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
                if fightUtils.findItem("武器大师执照", True, context, threshold=0.8):
                    break

        logger.info("可以出图了")
        self.isLeaveMaze = True
        # 到这可以出图了

    @timing_decorator
    def handle_MarsExchangeShop_event(self, context: Context, image):
        # 大于10层才处理交换商店事件
        if self.layers > 10 and context.run_recognition("Mars_Exchange_Shop", image):
            logger.info("触发Mars交换战利品事件")
            context.run_task("Mars_Exchange_Shop")
            if context.run_recognition(
                "Mars_Exchange_Shop_Check",
                context.tasker.controller.post_screencap().wait().get(),
            ):
                logger.info("交换商店出现了短剑")
                if context.run_recognition(
                    "Mars_Exchange_Shop_Add",
                    context.tasker.controller.post_screencap().wait().get(),
                ):
                    for _ in range(5):
                        context.run_task("Mars_Exchange_Shop_Add")
                        if context.run_recognition(
                            "Mars_Exchange_Shop_Add_Equipment_Select",
                            context.tasker.controller.post_screencap().wait().get(),
                        ):
                            context.run_task("Mars_Exchange_Shop_Add_Equipment_Select")
                        else:
                            logger.info("没有短剑，法杖和盾牌之外的装备了,跳过这次交换")
                            break

                        if AddButtonRecoDetail := context.run_recognition(
                            "Mars_Exchange_Shop_AddButtonReco",
                            context.tasker.controller.post_screencap().wait().get(),
                        ):
                            box = AddButtonRecoDetail.best_result.box
                            for _ in range(10):
                                context.tasker.controller.post_click(
                                    box[0] + box[2] // 2,
                                    box[1] + box[3] // 2,
                                ).wait()
                                time.sleep(0.05)
                        else:
                            logger.warning(
                                "一般不会到这里,进入这里说明由于未知原因离开交换商店了。"
                            )
                        context.run_task("Mars_Exchange_Shop_Confirm_Exchange")

                        # 如果交换完已经在桌面了，说明10个短剑都交换完了
                        if context.run_recognition(
                            "Fight_MainWindow",
                            context.tasker.controller.post_screencap().wait().get(),
                        ):
                            logger.info("已经交换了十把短剑~")
                            break
                        else:
                            logger.info("可用于更换的战利品没有了, 去获取更多吧~")
            else:
                logger.info("这个交换商店没有短剑, 去其他楼层找吧~")
            context.run_task("Fight_ReturnMainWindow")
            return True

    @timing_decorator
    def handle_MarsRuinsShop_event(self, context: Context, image):
        if context.run_recognition("Mars_RuinsShop", image):
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
        logger.debug("单数层再次清层")
        context.run_task("Mars_Fight_ClearCurrentLayer")
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()
        for _ in range(5):
            if not context.run_recognition("Mars_Reward", image):
                logger.debug("当前截图中奖励可能被遮挡, 再次截图尝试")
                time.sleep(1)
                image = context.tasker.controller.post_screencap().wait().get()
            else:
                break

        if normalReward and context.run_recognition("Mars_Reward", image):
            logger.info("触发Mars奖励事件")
            mars_reward_detail = context.run_task("Mars_Reward")
            if mars_reward_detail.nodes:
                for node in mars_reward_detail.nodes:
                    if node.name == "Mars_Inter_Confirm_Fail":
                        logger.info("领取Mars奖励失败, 为了防止卡死, 跳过这次领取")
                        return False
            return True

        if bossReward and context.run_recognition("Mars_BossReward", image):
            logger.info("触发MarsBoss奖励事件")
            context.run_task("Mars_BossReward")
            return True
        return True

    @timing_decorator
    def handle_MarsBody_event(self, context: Context, image):
        # 摸金事件卡返回基本只会发生在夹层中
        if bodyRecoDetail := context.run_recognition("Mars_Body", image):
            logger.info("触发Mars摸金事件")
            for body in bodyRecoDetail.filterd_results:
                box = body.box
                context.tasker.controller.post_click(
                    box[0] + box[2] // 2,
                    box[1] + box[3] // 2,
                ).wait()
                time.sleep(1)
                if context.run_recognition(
                    "Mars_Inter_Confirm_Success",
                    context.tasker.controller.post_screencap().wait().get(),
                ):
                    context.run_task("Mars_Inter_Confirm_Success")
                else:
                    logger.info("可能在夹层中有怪物没有清理")
                    context.run_task("Mars_Inter_Confirm_Fail")
                    return False
            return True
        return True

    @timing_decorator
    def handle_MarsStele_event(self, context: Context, image):
        if self.layers % 2 == 1 and context.run_recognition("Mars_Stele", image):
            logger.info("触发Mars斩断事件")
            context.run_task("Mars_Stele")
            return True
        return False

    @timing_decorator
    def handle_MarsStatue_event(self, context: Context, image=None):
        if self.layers < 10 and self.useEarthGate < 1:
            return False
        if image is None:
            image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Mars_Statue", image):
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
        if (
            (30 <= self.layers + 1 <= 120)
            and ((self.layers + 1) % 10 == 0)
            and context.run_recognition(
                "Mars_GotoSpecialLayer",
                image,
            )
        ):
            logger.info("触发Mars休息室事件")
            if not self.gotoSpecialLayer(context):
                return False
            context.run_task("Mars_Shower")
            context.run_task("Mars_EatBread")
            if self.target_magicgumball_para == "波塞冬":
                if self.layers >= 99:
                    fightUtils.cast_magic(
                        "土",
                        "石肤术",
                        context,
                    )
                if self.useEarthGate > 0:
                    fightUtils.cast_magic(
                        "暗",
                        "死亡波纹",
                        context,
                    )
                    if self.layers <= 59:
                        times = 1
                    elif 59 < self.layers < 99:
                        times = 2
                    else:
                        times = 3
                    for _ in range(times):
                        fightUtils.cast_magic(
                            "水",
                            "冰锥术",
                            context,
                            (special_layer_monster_1_x, special_layer_monster_1_y),
                        )
                    for _ in range(times):
                        fightUtils.cast_magic(
                            "水",
                            "冰锥术",
                            context,
                            (special_layer_monster_2_x, special_layer_monster_2_y),
                        )
            context.run_task("Fight_ReturnMainWindow")
            self.leaveSpecialLayer(context)
            # 检查一下状态
            self.Check_DefaultStatus(context)

            return True
        return True

    def handle_UseMagicAssist_event(self, context: Context):
        if (
            self.isGetMagicAssist
            and self.layers > self.target_leave_layer_para - 19
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
        fightUtils.handle_dragon_event("马尔斯", context)
        self.Check_DefaultStatus(context)

        image = context.tasker.controller.post_screencap().wait().get()
        self.handle_MarsBody_event(context, image)
        self.handle_MarsStele_event(context, image)
        self.handle_MarsRuinsShop_event(context, image)
        self.handle_MarsReward_event(context, image)
        self.handle_MarsStatue_event(context)
        self.handle_MarsExchangeShop_event(context, image)
        # 点称号挪到战后，确保购买战利品有足够的探索点
        self.Check_DefaultTitle(context)

        if not self.handle_SpecialLayer_event(context, image):
            # 如果卡剧情(离开),则返回False, 重新清理该层
            return False
        if self.handle_EarthGate_event(context):
            # 大地成功,需要回到战前准备开始清理该层，大地失败则继续往下走
            return False
        # if 101 >= self.layers >= 97:
        #     StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
        #     atk = int(StatusDetail["攻击"])

        if (
            (self.layers >= self.target_leave_layer_para - 2)
            # 到了99层依然没有获得魔法助手就结算
            or (101 > self.layers > 97 and self.isGetMagicAssist == False)
        ) and context.run_recognition(
            "Mars_GotoSpecialLayer",
            context.tasker.controller.post_screencap().wait().get(),
        ):
            self.handle_before_leave_maze_event(context)
        else:
            if self.isAutoPickup == self.target_autopickup_para:
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
            self.handle_boss_event(context)
            fightUtils.handle_dragon_event("马尔斯", context)
            return False
        # 小怪层探索
        else:
            context.run_task("Mars_Fight_ClearCurrentLayer")

        return True

    @timing_decorator
    def handle_interrupt_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        # 检测隐藏冈布奥
        if context.run_recognition(
            "Mars_HideGumball",
            image,
        ):
            logger.info("检测到隐藏冈布奥, 本层重新探索")
            context.run_task("Mars_HideGumball")
            return False

        if context.run_recognition(
            "Mars_Inter_Confirm_Success",
            image,
        ):
            logger.info("检测到卡剧情, 本层重新探索")
            context.run_task("Mars_Inter_Confirm_Success")
            return False

        if context.run_recognition(
            "Mars_Inter_Confirm_Fail",
            image,
        ):
            logger.info("检测到卡离开, 本层重新探索")
            context.run_task("Mars_Inter_Confirm_Fail")
            return False

        # 检测卡返回
        if context.run_recognition("BackText", image):
            logger.info("检测到卡返回, 本层重新探索")
            context.run_task("Fight_ReturnMainWindow")
            return False

        return True

    def gotoSpecialLayer(self, context: Context):
        context.run_task("Fight_ReturnMainWindow")
        if context.run_recognition(
            "Mars_GotoSpecialLayer",
            context.tasker.controller.post_screencap().wait().get(),
        ):

            mars_gotoSpecialLayer_detail = context.run_task("Mars_GotoSpecialLayer")
            if mars_gotoSpecialLayer_detail.nodes:
                for node in mars_gotoSpecialLayer_detail.nodes:
                    if node.name == "Mars_Inter_Confirm_Fail":
                        logger.info("进入休息室失败, 需要重新清理当前层")
                        return False
            while not context.run_recognition(
                "Mars_LeaveSpecialLayer",
                context.tasker.controller.post_screencap().wait().get(),
            ):
                time.sleep(1)
            logger.info("进入休息室")
            return True
        return True

    def leaveSpecialLayer(self, context: Context):
        context.run_task("Fight_ReturnMainWindow")
        if context.run_recognition(
            "Mars_LeaveSpecialLayer",
            context.tasker.controller.post_screencap().wait().get(),
        ):

            context.run_task("Mars_LeaveSpecialLayer")
            while not context.run_recognition(
                "Mars_GotoSpecialLayer",
                context.tasker.controller.post_screencap().wait().get(),
            ):
                time.sleep(1)
            logger.info("离开休息室")
            return True
        return False

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
        self.astrological_title_para = bool(
            context.get_node_data("Mars_Astrological_Title_Setting")["recognition"][
                "param"
            ]["expected"][0]
        )

        # initialize
        self.initialize(context)
        logger.info(f"本次任务目标层数: {self.target_leave_layer_para}")

        while self.layers <= 159:
            # 检查是否停止任务
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
        self.fightProcessor = fightProcessor.FightProcessor()

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # 进行特殊配置以适应Mars
        self.fightProcessor.grid_count = 40
        self.fightProcessor.hit_monster_count = 3
        self.fightProcessor.targetWish = "马尔斯"
        self.fightProcessor.clearCurrentLayer(context, isclearall=True)
        return CustomAction.RunResult(success=True)
