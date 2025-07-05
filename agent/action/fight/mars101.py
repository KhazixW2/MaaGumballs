from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger

from action.fight import fightUtils
from action.fight import fightProcessor

import time

boss_x, boss_y = 360, 800


@AgentServer.custom_action("Mars101")
class Mars101(CustomAction):
    def __init__(self):
        super().__init__()
        self.isTitle_L3 = False
        self.isTitle_L56 = False
        self.isTitle_L76 = False
        self.useEarthGate = 0
        self.isShutDownTitan = False
        self.is_android_skill_enabled = False
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
        1. 检查56层的称号: 位面点满即可
        2. 大地之前确认魔法系点满
        3. 检查66层的称号: 位面，大铸剑师，大剑师都点满
        """
        if (self.layers == 3 or self.layers == 4) and self.isTitle_L3 == False:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 1, context)
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L3 = True
        elif self.layers == 56 or self.layers == 57:
            if self.isTitle_L56 == False:

                fightUtils.title_learn("魔法", 1, "魔法学徒", 3, context)
                fightUtils.title_learn("魔法", 2, "黑袍法师", 1, context)
                fightUtils.title_learn("魔法", 3, "咒术师", 1, context)
                fightUtils.title_learn("魔法", 4, "土系大师", 1, context)
                fightUtils.title_learn("魔法", 5, "位面先知", 1, context)
                context.run_task("Fight_ReturnMainWindow")

                fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)
                fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)
                fightUtils.title_learn_branch("魔法", 5, "魔法强化", 3, context)
                context.run_task("Fight_ReturnMainWindow")

                fightUtils.title_learn("魔法", 4, "土系大师", 3, context)
                fightUtils.title_learn("魔法", 2, "黑袍法师", 3, context)
                context.run_task("Fight_ReturnMainWindow")

                context.run_task("Save_Status")
                context.run_task("Fight_ReturnMainWindow")
                self.isTitle_L56 = True

        elif (self.layers == 61 or self.layers == 71) and self.useEarthGate < 2:

            fightUtils.title_learn("魔法", 2, "黑袍法师", 3, context)
            fightUtils.title_learn("魔法", 3, "咒术师", 3, context)
            fightUtils.title_learn("魔法", 4, "土系大师", 3, context)
            context.run_task("Fight_ReturnMainWindow")

            fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "魔法强化", 3, context)

            context.run_task("Fight_ReturnMainWindow")
            context.run_task("Save_Status")
            context.run_task("Fight_ReturnMainWindow")
            self.isuseEarthGate = False

        elif self.layers == 76 or self.layers == 77 and self.isTitle_L76 == False:
            fightUtils.title_learn("战斗", 1, "见习战士", 3, context)
            fightUtils.title_learn("战斗", 2, "战士", 3, context)
            fightUtils.title_learn("战斗", 3, "剑舞者", 3, context)
            fightUtils.title_learn("战斗", 4, "大剑师", 3, context)
            context.run_task("Fight_ReturnMainWindow")

            fightUtils.title_learn("冒险", 1, "寻宝者", 3, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 3, context)
            fightUtils.title_learn("冒险", 3, "锻造师", 3, context)
            fightUtils.title_learn("冒险", 4, "武器大师", 3, context)
            fightUtils.title_learn("冒险", 5, "大铸剑师", 1, context)
            context.run_task("Fight_ReturnMainWindow")

            fightUtils.title_learn_branch("冒险", 5, "攻击强化", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "魔法强化", 3, context)
            context.run_task("Fight_ReturnMainWindow")

            if fightUtils.title_check("巨龙", context):
                fightUtils.title_learn("巨龙", 1, "亚龙血统", 3, context)
                fightUtils.title_learn("巨龙", 2, "初级龙族血统", 3, context)
                fightUtils.title_learn("巨龙", 3, "中级龙族血统", 3, context)
                fightUtils.title_learn("巨龙", 4, "高级龙族血统", 3, context)
                fightUtils.title_learn("巨龙", 5, "邪龙血统", 1, context)
                context.run_task("Fight_ReturnMainWindow")

                fightUtils.title_learn_branch("巨龙", 5, "生命强化", 3, context)
                # fightUtils.title_learn_branch("巨龙", 5, "攻击强化", 3, context)
                fightUtils.title_learn_branch("巨龙", 5, "攻击强化", 3, context)

            context.run_task("Save_Status")
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L76 = True

    def Check_DefaultStatus(self, context: Context):

        # 检查冈布奥状态
        tempNum = self.layers % 10
        if (
            (50 <= self.layers <= 79) and (tempNum == 1 or tempNum == 5 or tempNum == 9)
        ) or self.layers >= 80:
            StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
            CurrentHP = float(StatusDetail["当前生命值"])
            MaxHp = float(StatusDetail["最大生命值"])
            HPStatus = CurrentHP / MaxHp

            if HPStatus < 0.8:
                while HPStatus < 0.8:
                    if not fightUtils.cast_magic("光", "神恩术", context):
                        if not fightUtils.cast_magic("水", "治疗术", context):
                            if not fightUtils.cast_magic("水", "治愈术", context):
                                logger.info("没有任何治疗方法了= =")
                                break
                    context.run_task("Fight_ReturnMainWindow")
                    StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
                    CurrentHP = float(StatusDetail["当前生命值"])
                    MaxHp = float(StatusDetail["最大生命值"])
                    HPStatus = CurrentHP / MaxHp
                    logger.info(f"current hp is {CurrentHP}, HPStatus is {HPStatus}")
            else:
                logger.info("当前生命值大于80%，不使用治疗")

        return True

    def handle_android_skill_event(self, context: Context):
        target_skill_list = ["外接皮", "机械起搏器"]
        if (
            self.layers == 5 or self.layers == 6
        ) and self.is_android_skill_enabled == False:
            for skill in target_skill_list:
                if context.run_recognition(
                    "Mars_Android_Skill_Open",
                    context.tasker.controller.post_screencap().wait().get(),
                ):
                    context.run_task(
                        "Mars_Android_Skill_Open",
                        pipeline_override={
                            "Mars_Android_Skill_Choose": {
                                "expected": skill,
                            }
                        },
                    )
                    self.is_android_skill_enabled = True

    def handle_boss_event(self, context: Context):
        if context.run_recognition(
            "Fight_OpenedDoor", context.tasker.controller.post_screencap().wait().get()
        ):
            context.run_task("Fight_OpenedDoor")

        else:

            for _ in range(3):
                fightUtils.cast_magic_special("生命颂歌", context)

            actions = [
                lambda: fightUtils.cast_magic("光", "祝福术", context),
                lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                lambda: fightUtils.cast_magic("水", "冰锥术", context),
                lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
                lambda: context.tasker.controller.post_click(boss_x, boss_y).wait(),
            ]
            index = 0
            for _ in range(10):
                # 执行当前动作
                actions[index]()
                time.sleep(0.5)

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
            self.handle_MarsReward_event(context)
            if self.isShutDownTitan == False and self.layers > 80:
                if fightUtils.cast_magic_special("泰坦之足", context):
                    self.isShutDownTitan = True
            context.run_task("Fight_OpenedDoor")
        return True

    def handle_earthgate_event(self, context: Context):
        if (self.layers == 61 or self.layers == 71) and self.useEarthGate < 2:
            if fightUtils.cast_magic("土", "大地之门", context):
                self.useEarthGate += 1
            elif self.layers == 71:
                self.useEarthGate = 2
            self.handle_clearCurLayer_event(context)
            # 是否检查大地成功

    def handle_preLayers_event(self, context: Context):
        self.handle_android_skill_event(context)
        self.Check_DefaultEquipment(context)
        self.Check_DefaultTitle(context)
        self.Check_DefaultStatus(context)

        return True

    def handle_perfect_event(self, context: Context):
        # 检测完美击败
        if context.run_recognition(
            "Fight_Perfect", context.tasker.controller.post_screencap().wait().get()
        ):
            logger.info(f"第{self.layers} 完美击败")
            while context.run_recognition(
                "Fight_Perfect",
                context.tasker.controller.post_screencap().wait().get(),
            ):
                pass

    def handle_before_leave_maze_event(self, context: Context):
        for _ in range(3):
            fightUtils.cast_magic_special("生命颂歌", context)

        context.run_task("Mars_GotoSpecialLayer")
        while not context.run_recognition(
            "Fight_OpenedDoor", context.tasker.controller.post_screencap().wait().get()
        ):
            time.sleep(1)
        context.run_task("Fight_ReturnMainWindow")
        OpenDetail = context.run_task("Bag_Open")
        if OpenDetail:
            fightUtils.findItem("电能试剂", True, context)
        time.sleep(1)

        context.tasker.controller.post_click(635, 928).wait()
        context.run_task("Fight_ReturnMainWindow")
        for _ in range(3):
            fightUtils.cast_magic_special("生命颂歌", context)

        context.run_task("Mars_GotoSpecialLayer")
        while not context.run_recognition(
            "Fight_OpenedDoor", context.tasker.controller.post_screencap().wait().get()
        ):
            time.sleep(1)
        context.run_task("Fight_ReturnMainWindow")
        OpenDetail = context.run_task("Bag_Open")
        if OpenDetail:
            fightUtils.findItem("能量电池", True, context)
        time.sleep(1)

        context.tasker.controller.post_click(635, 928).wait()
        context.run_task("Fight_ReturnMainWindow")
        for _ in range(3):
            fightUtils.cast_magic_special("生命颂歌", context)

        fightUtils.title_learn("战斗", 5, "剑圣", 1, context)
        context.run_task("Fight_ReturnMainWindow")

        fightUtils.title_learn_branch("战斗", 5, "攻击强化", 3, context)
        fightUtils.title_learn_branch("战斗", 5, "魔力强化", 3, context)
        fightUtils.title_learn_branch("战斗", 5, "生命强化", 3, context)
        context.run_task("Fight_ReturnMainWindow")
        OpenDetail = context.run_task("Bag_Open")
        if OpenDetail:
            for _ in range(2):
                if fightUtils.findItem("武器大师执照", True, context, threshold=0.8):
                    break

        logger.info("可以出图了")
        # 到这可以出图了

    def handle_downstair_event(self, context: Context):
        recoDetail = context.run_task("Fight_OpenedDoor")
        if not recoDetail.nodes and context.run_recognition(
            "FindKeyHole", context.tasker.controller.post_screencap().wait().get()
        ):
            logger.warning("检查到神秘的洞穴捏，请冒险者大人检查！！")
            fightUtils.send_alert("洞穴警告", "发现神秘洞穴，请及时处理！")

            while not context.run_recognition(
                "Fight_OpenedDoor",
                context.tasker.controller.post_screencap().wait().get(),
            ):
                time.sleep(3)

            logger.info("冒险者大人已找到钥匙捏，继续探索")
            context.run_task("Fight_OpenedDoor")

    def handle_MarsRuinsShop_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Mars_RuinsShop", image):
            context.run_task("Mars_RuinsShop")

    def handle_MarsReward_event(self, context: Context):
        if self.layers % 2 == 1 or context.run_recognition(
            "Mars_Reward", context.tasker.controller.post_screencap().wait().get()
        ):
            context.run_task("Mars_Reward")
        if (
            self.layers >= 30
            and self.layers % 10 == 0
            and context.run_recognition(
                "Mars_BossReward",
                context.tasker.controller.post_screencap().wait().get(),
            )
        ):
            context.run_task("Mars_BossReward")

    def handle_MarsBody_event(self, context: Context):
        while context.run_recognition(
            "Mars_Body", context.tasker.controller.post_screencap().wait().get()
        ):
            context.run_task("Mars_Body")

    def handle_MarsStele_event(self, context: Context):
        if context.run_recognition(
            "Mars_Stele", context.tasker.controller.post_screencap().wait().get()
        ):
            context.run_task("Mars_Stele")
            time.sleep(1)

    def handle_MarsStatue_event(self, context: Context):
        if self.layers >= 10 and context.run_recognition(
            "Mars_Statue", context.tasker.controller.post_screencap().wait().get()
        ):
            context.run_task("Mars_Statue")
            if self.isShutDownTitan == False and self.layers > 80:
                if fightUtils.cast_magic_special("泰坦之足", context):
                    self.isShutDownTitan = True

    def handle_postLayers_event(self, context: Context):
        self.handle_perfect_event(context)
        self.Check_DefaultStatus(context)
        self.handle_MarsBody_event(context)
        self.handle_MarsStele_event(context)
        self.handle_MarsRuinsShop_event(context)
        self.handle_MarsStatue_event(context)
        self.handle_MarsReward_event(context)
        self.handle_earthgate_event(context)
        if self.layers == 99:
            self.handle_before_leave_maze_event(context)
        else:
            self.handle_downstair_event(context)

    def handle_clearCurLayer_event(self, context: Context):
        # boss层开始探索
        if self.layers >= 30 and self.layers % 10 == 0:
            # boss召唤动作
            time.sleep(6)
            self.handle_boss_event(context)
            # 检测神龙
            time.sleep(1)
            img = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition("Fight_FindDragon", img):
                logger.info("是神龙,俺,俺们有救了！！！")
                fightUtils.dragonwish("工资", context)
                logger.info("神龙带肥家lo~")

            return False
        # 小怪层探索
        else:
            context.run_task("Mars_Fight_ClearCurrentLayer")

        return True

    def handle_interrupt_event(self, context: Context):
        # 检测卡剧情
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition(
            "JJC_Inter_Confirm",
            image,
        ):
            logger.info("检测到卡剧情, 本层重新探索")
            context.run_task("JJC_Inter_Confirm")
            return False

        # 检测卡返回
        if context.run_recognition("BackText", image):
            logger.info("检测到卡返回, 本层重新探索")
            context.run_task("Fight_ReturnMainWindow")
            return False

        return True

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        # initialize
        self.initialize(context)

        while self.layers <= 101:
            # 检查是否停止任务
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)

            # 检查当前层数, 确保不是0层
            context.run_task("Fight_ReturnMainWindow")
            tempLayers = -1
            while tempLayers <= 0 and (
                RunResult := context.run_recognition(
                    "Fight_CheckLayer",
                    context.tasker.controller.post_screencap().wait().get(),
                )
            ):

                tempLayers = fightUtils.extract_num_layer(RunResult.best_result.text)
                if context.tasker.stopping:
                    logger.info("检测到停止任务, 开始退出agent")
                    return CustomAction.RunResult(success=False)
            self.layers = tempLayers

            logger.info(f"Start Explore {self.layers} layer.")

            # 检测是否触发战前事件
            self.handle_preLayers_event(context)

            # 探索当前层
            if not self.handle_clearCurLayer_event(context):
                continue

            # 检查是否触发中断事件
            if not self.handle_interrupt_event(context):
                continue

            # 检查是否触发战后事件
            self.handle_postLayers_event(context)

            if self.layers == 99:
                logger.info(f"current layers {self.layers}, 开始退出agent")
                break

        logger.info(f"马尔斯探索结束，当前到达{self.layers}层")

        context.run_task("Fight_LeaveMaze")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Mars_Fight_ClearCurrentLayer")
class Mars_Fight_ClearCurrentLayer(CustomAction):

    def __init__(self):
        super().__init__()
        self.fightProcessor = fightProcessor.FightProcessor()
        # 进行特殊配置以适应Mars
        self.fightProcessor.grid_count = 40
        self.fightProcessor.hit_monster_count = 3

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        self.fightProcessor.clearCurrentLayer(context)
        return CustomAction.RunResult(success=True)
