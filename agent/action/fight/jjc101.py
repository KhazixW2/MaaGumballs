from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger

from action.fight import fightUtils
from action.fight import fightProcessor

import time

boss_x, boss_y = 360, 800


@AgentServer.custom_action("JJC101")
class JJC101(CustomAction):
    def __init__(self):
        super().__init__()
        self.isHaveSpartanHat = False
        self.isHaveDog = False
        self.isTitle_L1 = False
        self.isTitle_L36 = False
        self.isTitle_L63 = False
        self.layers = 1

    def initialize(self, context: Context):
        self.__init__()
        logger.info("JJC101初始化完成")
        # 检查当前层数
        context.run_task("Fight_ReturnMainWindow")
        RunResult = context.run_task("Fight_CheckLayer")
        if RunResult.nodes:
            self.layers = fightUtils.extract_num_layer(
                RunResult.nodes[0].recognition.best_result.text
            )

        # 进入地图初始化
        logger.info(f"当前层数: {self.layers}, 进入地图初始化")
        context.run_task("Bag_Open")
        # 检查是否已装备斯巴达的头盔
        has_helmet = fightUtils.checkEquipment("头盔", 7, "斯巴达的头盔", context)
        if not has_helmet:
            # 若未装备，则尝试寻找该头盔
            found_helmet = fightUtils.findEquipment(7, "斯巴达的头盔", False, context)
            self.isHaveSpartanHat = found_helmet
        else:
            self.isHaveSpartanHat = True

        if not fightUtils.findItem("东方剪纸", False, context):
            logger.info("未找到东方剪纸, 已经叫过狗了")
            self.isHaveDog = True

        context.run_task("Fight_ReturnMainWindow")

    def Check_DefaultEquipment(self, context: Context):
        """
        检查默认装备
        1. 检查第1层和第27层的装备
        """
        if self.layers == 1 or self.layers == 26 or self.layers == 63:
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
        elif self.layers >= 30 and self.layers % 10 == 1:  # 装备土系魔法书
            OpenDetail = context.run_task("Bag_Open")
            if OpenDetail.nodes:

                if not fightUtils.checkEquipment("宝物", 6, "土系魔法书", context):
                    fightUtils.findEquipment(6, "土系魔法书", True, context)

                if not fightUtils.checkEquipment("盔甲", 6, "执政官铠甲", context):
                    fightUtils.findEquipment(6, "执政官铠甲", True, context)

                if not fightUtils.checkEquipment("鞋子", 6, "次元靴", context):
                    fightUtils.findEquipment(6, "次元靴", True, context)

                if not fightUtils.checkEquipment("项链", 6, "星月教挂坠", context):
                    fightUtils.findEquipment(6, "星月教挂坠", True, context)
                context.run_task("Fight_ReturnMainWindow")
                logger.info(f"current layers {self.layers},装备检查完成")
            else:
                logger.info("背包打开失败")
                return False

        elif self.layers == 94 or self.layers == 95:
            context.run_task("Fight_ReturnMainWindow")
            OpenDetail = context.run_task("Bag_Open")
            if not fightUtils.checkEquipment("头盔", 7, "斯巴达的头盔", context):
                fightUtils.findEquipment(7, "斯巴达的头盔", True, context)
            logger.info(f"current layers {self.layers},装备检查完成")

            context.run_task("Fight_ReturnMainWindow")

        return True

    def Check_DefaultTitle(self, context: Context):
        """
        检查默认称号
        1. 检查1、36、64和89层的称号
        """
        if (self.layers == 1 or self.layers == 2) and self.isTitle_L1 == False:
            fightUtils.title_learn("冒险", 1, "寻宝者", 1, context)
            fightUtils.title_learn("冒险", 2, "探险家", 3, context)
            fightUtils.title_learn("魔法", 1, "魔法学徒", 1, context)
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L1 = True
        elif (self.layers == 36 or self.layers == 37) and self.isTitle_L36 == False:

            fightUtils.title_learn("战斗", 1, "见习战士", 1, context)
            fightUtils.title_learn("战斗", 2, "战士", 3, context)
            fightUtils.title_learn("战斗", 3, "剑舞者", 3, context)
            fightUtils.title_learn("战斗", 4, "炎龙武士", 3, context)
            fightUtils.title_learn("战斗", 5, "毁灭公爵", 1, context)

            context.run_task("Fight_ReturnMainWindow")
            fightUtils.title_learn("魔法", 1, "魔法学徒", 3, context)
            fightUtils.title_learn("魔法", 2, "白袍法师", 1, context)
            fightUtils.title_learn("魔法", 3, "祭司", 1, context)
            fightUtils.title_learn("魔法", 4, "气系大师", 1, context)
            fightUtils.title_learn("魔法", 5, "传奇法师", 1, context)

            context.run_task("Fight_ReturnMainWindow")
            fightUtils.title_learn_branch("战斗", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("战斗", 5, "攻击强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "生命强化", 1, context)
            fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)

            context.run_task("Fight_ReturnMainWindow")
            context.run_task("Save_Status")
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L36 = True
        elif (self.layers == 63 or self.layers == 64) and self.isTitle_L63 == False:

            fightUtils.title_learn("冒险", 1, "寻宝者", 2, context)
            fightUtils.title_learn("冒险", 2, "探险家", 1, context)
            fightUtils.title_learn("冒险", 3, "暗行者", 1, context)
            fightUtils.title_learn("冒险", 4, "魔盗", 1, context)
            fightUtils.title_learn("冒险", 5, "异界游侠", 1, context)

            context.run_task("Fight_ReturnMainWindow")
            fightUtils.title_learn("魔法", 2, "白袍法师", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "魔法强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)
            self.isTitle_L63 = True
            context.run_task("Fight_ReturnMainWindow")
        return True

    def Check_DefaultStatus(self, context: Context):

        # 检查冈布奥状态
        tempNum = self.layers % 10
        if (
            (self.layers >= 55 and (tempNum == 1 or tempNum == 5 or tempNum == 9))
            or (self.layers >= 90 and tempNum == 4)
            or (self.layers == 39)
        ):
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

        context.run_task("Fight_ReturnMainWindow")
        if tempNum == 9 and self.layers >= 61 and self.layers <= 90:
            fightUtils.OpenNatureSwitch(False, context)
            logger.info("开启自然之力")
        elif tempNum == 1 and self.layers >= 61 and self.layers <= 90:
            fightUtils.OpenNatureSwitch(True, context)
            logger.info("开启自然守护")

        # 保命
        if self.layers == 89 and not fightUtils.checkBuffStatus("神圣重生", context):
            fightUtils.cast_magic("光", "神圣重生", context)

        return True

    def handle_abattoir_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if (self.layers % 10 == 5 or self.layers % 10 == 4) and context.run_recognition(
            "JJC_Find_Abattoir",
            image,
        ):
            logger.info(f"进入角斗场战斗！！！")
            context.run_task("JJC_Find_Abattoir")
            if self.layers <= 35:
                fightUtils.cast_magic("光", "祝福术", context)
                for _ in range(3):
                    fightUtils.cast_magic_special("天眼", context)

            elif self.layers <= 45:
                if not fightUtils.cast_magic("火", "失明术", context, (boss_x, boss_y)):
                    fightUtils.cast_magic("暗", "诅咒术", context, (boss_x, boss_y))
                for _ in range(3):
                    if not fightUtils.cast_magic("光", "祝福术", context):
                        if not fightUtils.cast_magic("水", "治疗术", context):
                            fightUtils.cast_magic("土", "石肤术", context)

            elif self.layers <= 55:
                if not fightUtils.cast_magic("火", "失明术", context, (boss_x, boss_y)):
                    fightUtils.cast_magic("暗", "诅咒术", context, (boss_x, boss_y))
                for _ in range(3):
                    if not fightUtils.cast_magic("水", "寒冰护盾", context):
                        if not fightUtils.cast_magic("水", "治疗术", context):
                            fightUtils.cast_magic("土", "石肤术", context)

            elif self.layers <= 75:
                for _ in range(2):
                    context.run_task("Bag_Open")
                    fightUtils.findItem("异域的灯芯", True, context, boss_x, boss_y)
                for _ in range(3):
                    if not fightUtils.cast_magic("水", "寒冰护盾", context):
                        if not fightUtils.cast_magic("水", "治疗术", context):
                            fightUtils.cast_magic("土", "石肤术", context)
            else:
                for _ in range(2):
                    context.run_task("Bag_Open")
                    fightUtils.findItem("异域的灯芯", True, context, boss_x, boss_y)
            if context.run_recognition(
                "Fight_Victory", context.tasker.controller.post_screencap().wait().get()
            ):
                context.run_task("Fight_Victory")
            time.sleep(2)
            context.run_task("JJC_Abattoir_Chest")
            context.run_task("Fight_OpenedDoor")
        return True

    def handle_boss_80_event(self, context: Context):
        fightUtils.cast_magic("火", "失明术", context)
        fightUtils.cast_magic("气", "静电场", context)
        if not fightUtils.cast_magic("水", "冰锥术", context):
            if not fightUtils.cast_magic("暗", "变形术", context):
                fightUtils.cast_magic("土", "石肤术", context)
        fightUtils.cast_magic("水", "寒冰护盾", context)
        fightUtils.cast_magic("水", "寒冰护盾", context)
        fightUtils.cast_magic("土", "石肤术", context)
        fightUtils.cast_magic("光", "神恩术", context)
        for _ in range(3):
            context.tasker.controller.post_click(boss_x, boss_y).wait()

    def handle_boss_80_90_event(self, context: Context):
        fightUtils.OpenNatureSwitch(True, context)
        logger.info("没有时停，开启自然守护流打法")
        fightUtils.cast_magic("火", "失明术", context)
        fightUtils.PushOne_defense(context)
        fightUtils.PushOne_defense(context)

        # 循环——直到boss死亡：使用动作队列逐个执行并检查boss状态
        actions = [
            lambda: fightUtils.cast_magic("水", "冰锥术", context),
            lambda: fightUtils.PushOne_defense(context),
            lambda: fightUtils.cast_magic("土", "石肤术", context),
            lambda: fightUtils.cast_magic("火", "失明术", context),
            lambda: fightUtils.PushOne_defense(context),
            lambda: fightUtils.PushOne_defense(context),
            lambda: fightUtils.PushOne_defense(context),
        ]

        index = 0
        for _ in range(10):
            # 执行当前动作
            actions[index]()

            # 检查boss是否存在
            if context.run_recognition(
                "Fight_CheckBossStatus",
                context.tasker.controller.post_screencap().wait().get(),
            ):
                logger.info(f"当前层数 {self.layers} 已经击杀boss")
                fightUtils.OpenNatureSwitch(False, context)
                return True

            # 移动到下一个动作，循环执行
            index = (index + 1) % len(actions)

        logger.warning("十多个回合还没有拿下，是不是狗子挂了")
        return False

    def handle_boss_100_event(self, context: Context):
        fightUtils.cast_magic("气", "静电场", context)
        fightUtils.cast_magic("火", "毁灭之刃", context)
        fightUtils.cast_magic("气", "瓦解射线", context)
        for _ in range(6):
            context.tasker.controller.post_click(boss_x, boss_y).wait()
            time.sleep(0.3)

    def handle_boss_100Dragon_event(self, context: Context):
        fightUtils.cast_magic("火", "失明术", context)
        for _ in range(2):
            context.tasker.controller.post_click(boss_x, boss_y).wait()
        fightUtils.cast_magic("特殊", "龙威", context)
        for _ in range(2):
            context.tasker.controller.post_click(boss_x, boss_y).wait()
        fightUtils.cast_magic("火", "失明术", context)
        for _ in range(2):
            context.tasker.controller.post_click(boss_x, boss_y).wait()

    def handle_boss_event(self, context: Context):
        if self.layers == 30:
            fightUtils.cast_magic("光", "祝福术", context)
            for _ in range(3):
                fightUtils.cast_magic_special("天眼", context)

        elif self.layers <= 60:
            fightUtils.cast_magic("光", "祝福术", context)
            for _ in range(5):
                context.tasker.controller.post_click(boss_x, boss_y).wait()
                time.sleep(0.1)

        elif self.layers <= 70:
            fightUtils.cast_magic("水", "冰锥术", context)
            for _ in range(4):
                context.tasker.controller.post_click(boss_x, boss_y).wait()
                time.sleep(0.1)
            fightUtils.cast_magic("土", "石肤术", context)
            fightUtils.cast_magic("水", "治疗术", context)

        elif self.layers <= 80:
            self.handle_boss_80_90_event(context)

        elif self.layers <= 100:
            if fightUtils.cast_magic("气", "时间停止", context):
                self.handle_boss_100_event(context)
            else:
                self.handle_boss_80_90_event(context)
        # 捡东西
        time.sleep(3)
        context.run_task("Fight_OpenedDoor")
        return True

    def handle_dog_event(self, context: Context):
        # 自动叫狗事件
        if self.layers >= 36 and self.layers <= 39 and self.isHaveDog != True:
            if fightUtils.Auto_CallDog(context):
                self.isHaveDog = True
            elif self.layers == 39:
                logger.error("39层未触发毁灭, 自动叫狗失败, 太黑了吧, 用户来接管吧")
                fightUtils.send_alert(
                    "严重警告", "39层叫狗失败,可能是没有触发毁灭，请用户手动接管"
                )
                return False
        return True

    def handle_preLayers_event(self, context: Context):
        self.Check_DefaultEquipment(context)
        self.Check_DefaultTitle(context)
        self.handle_dog_event(context)
        self.handle_abattoir_event(context)
        return True

    def handle_perfect_event(self, context: Context):
        # 检测完美击败
        if not self.isHaveSpartanHat and context.run_recognition(
            "Fight_Perfect", context.tasker.controller.post_screencap().wait().get()
        ):
            logger.info(f"第{self.layers} 完美击败")
            while context.run_recognition(
                "Fight_Perfect",
                context.tasker.controller.post_screencap().wait().get(),
            ):
                pass

    def handle_sparta_event(self, context: Context):
        # 寻找斯巴达头盔
        if not self.isHaveSpartanHat:
            # 检测三次斯巴达的头盔，检查到了就提前结束检查
            time.sleep(1)
            for _ in range(5):
                img = context.tasker.controller.post_screencap().wait().get()
                if context.run_recognition("JJC_Find_Body", img):
                    context.run_task("JJC_Find_Body")
                    self.isHaveSpartanHat = True
                    logger.info("已有斯巴达头盔，或找到斯巴达头盔了！！")
                    break

    def handle_skillShop_event(self, context: Context):
        # 打开技能商店
        if self.layers >= 40:
            return True
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_SkillShop", image):
            logger.info("打开技能商店")
            context.run_task("Fight_SkillShop")

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
                if context.tasker.stopping:
                    logger.info("检测到停止任务, 开始退出agent")
                    return False
                time.sleep(3)

            logger.info("冒险者大人已找到钥匙捏，继续探索")
            context.run_task("Fight_OpenedDoor")
        return True

    def handle_stone_event(self, context: Context):
        if self.layers <= 29 and context.run_recognition(
            "JJC_StoneChest", context.tasker.controller.post_screencap().wait().get()
        ):
            context.run_task("JJC_StoneChest")

    def handle_postLayers_event(self, context: Context):
        self.handle_perfect_event(context)
        self.Check_DefaultStatus(context)
        self.handle_stone_event(context)
        self.handle_sparta_event(context)
        self.handle_skillShop_event(context)
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
            if (
                self.layers >= 85
                and self.layers % 2 == 1
                and fightUtils.cast_magic("土", "地震术", context)
            ):
                time.sleep(3)
            else:
                context.run_task("JJC_Fight_ClearCurrentLayer")

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

        while self.layers < 101:
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

            # 检查是否到达100层
            if self.layers == 95:
                logger.info(f"current layers {self.layers}, 开始退出agent")
                break

            # 探索当前层
            if not self.handle_clearCurLayer_event(context):
                continue

            # 检查是否触发中断事件
            if not self.handle_interrupt_event(context):
                continue

            # 检查是否触发战后事件
            self.handle_postLayers_event(context)

        logger.info(f"竞技场探索结束，当前到达{self.layers}层")
        context.run_task("Fight_LeaveMaze")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC_Fight_ClearCurrentLayer")
class JJC_Fight_ClearCurrentLayer(CustomAction):

    def __init__(self):
        super().__init__()
        self.fightProcessor = fightProcessor.FightProcessor()

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        self.fightProcessor.clearCurrentLayer(context)
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Fight_Select")
class Fight_Select(CustomAction):
    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # logger.info("选择药剂中")
        context.run_task("Select_Drug")

        # logger.info("选择神器中")
        context.run_task("Select_Artifact")

        # logger.info("选择自然之子中")
        context.run_task(
            "Select_Gumball_1",
            pipeline_override={"select_InputBox_Text": {"input_text": "自然之子"}},
        )

        # logger.info("选择贵族")
        context.run_task(
            "Select_Gumball_2",
            pipeline_override={"select_InputBox_Text": {"input_text": "贵族"}},
        )

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Fight_CallDog")
class Fight_CallDog(CustomAction):
    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        if fightUtils.Auto_CallDog(context):
            return CustomAction.RunResult(success=True)
        return CustomAction.RunResult(success=False)


@AgentServer.custom_action("Fight_TestAction")
class Fight_TestAction(CustomAction):
    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        fightUtils.autoOpenPicup(context)
        # fightUtils.checkGumballsStatusV2(context)
        # fightUtils.title_learn_branch("魔法", 5, "魔力强化", 1, context)
        # fightUtils.title_learn_branch("魔法", 5, "生命强化", 2, context)

        # fightUtils.title_learn("魔法", 2, "白袍法师", 3, context)
        # fightUtils.title_learn("魔法", 3, "祭司", 3, context)
        # fightUtils.title_learn("魔法", 4, "气系大师", 3, context)

        # fightUtils.disassembleEquipment(
        #     6,
        #     [
        #         "土系魔法书",
        #         "气系魔法书",
        #         "火系魔法书",
        #         "水系魔法书",
        #         "光系魔法书",
        #         "暗系魔法书",
        #         "执政官铠甲",
        #         "骨灰指轮",
        #         "次元靴",
        #         "大德鲁伊斗篷",
        #         "法老面具",
        #         "格斗大师拳套",
        #         "圣者的日记",
        #         "伊斯坦丁",
        #     ],
        #     context,
        # )
        fightUtils.title_learn_branch("魔法", 5, "攻击强化", 3, context)
        fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)
        fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC_DragonWishTest")
class JJC_DragonWishTest(CustomAction):

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        fightUtils.dragonwish("工资", context)

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC_CalEarning")
class JJC_CalEarning(CustomAction):
    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        time.sleep(5)
        for _ in range(10):
            context.tasker.controller.post_click(360, 640)
            time.sleep(0.5)
            context.tasker.controller.post_click(360, 640)
        image = context.tasker.controller.post_screencap().wait().get()
        if recoDetail := context.run_recognition(
            "CallEarning_Reco",
            image,
            pipeline_override={
                "CallEarning_Reco": {
                    "recognition": "OCR",
                    "expected": ["获得"],
                    "roi": [78, 940, 471, 116],
                },
            },
        ):
            EarningDetail = fightUtils.pair_by_distance(recoDetail.all_results, 400)
            logger.info(EarningDetail)

        context.run_task("ReturnBigMap")
        time.sleep(3)
        context.run_task("Start_Up")

        return CustomAction.RunResult(success=True)
