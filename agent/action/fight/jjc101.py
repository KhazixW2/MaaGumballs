from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger

from action.fight import fightUtils

import time

cols, rows = 5, 6
roi_list = fightUtils.calRoiList()
roi_matrix = [roi_list[i * cols : (i + 1) * cols] for i in range(rows)]
visited = [[0] * cols for _ in range(rows)]
boss_x, boss_y = 360, 800


@AgentServer.custom_action("JJC101")
class JJC101(CustomAction):
    def __init__(self):
        super().__init__()
        self.isHaveSpartanHat = False
        self.isHaveDog = False
        self.layers = 1  # 原layers变量

    def initialize(self, context: Context):
        # 检查当前层数
        RunResult = context.run_task("Fight_CheckLayer")
        if RunResult.nodes:
            self.layers = fightUtils.extract_numbers(
                RunResult.nodes[0].recognition.best_result.text
            )

        # 进入地图初始化
        logger.info(f"当前层数: {self.layers}, 进入地图初始化")
        context.run_task("Bag_Open")
        if not fightUtils.checkEquipment("头盔", 7, "斯巴达的头盔", context):
            if fightUtils.findEquipment(7, "斯巴达的头盔", True, context):
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
        if self.layers == 1 or self.layers == 27 or self.layers == 64:
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
            else:
                logger.info("背包打开失败")
                return False
        elif self.layers >= 30 and self.layers % 10 == 1:  # 装备土系魔法书
            OpenDetail = context.run_task("Bag_Open")
            if OpenDetail.nodes:
                if not fightUtils.checkEquipment("宝物", 6, "土系魔法书", context):
                    fightUtils.findEquipment(6, "土系魔法书", True, context)

                if not fightUtils.checkEquipment("项链", 6, "星月教挂坠", context):
                    fightUtils.findEquipment(6, "星月教挂坠", True, context)

                context.run_task("Fight_ReturnMainWindow")
            else:
                logger.info("背包打开失败")
                return False
        elif self.layers == 94 or self.layers == 95:
            if not fightUtils.checkEquipment("头盔", 7, "斯巴达的头盔", context):
                fightUtils.findEquipment(7, "斯巴达的头盔", True, context)

        logger.info(f"current layers {self.layers},装备检查完成")
        return True

    def Check_DefaultTitle(self, context: Context):
        """
        检查默认称号
        1. 检查1、29、64和89层的称号
        """
        if self.layers == 1:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 4, context)
            fightUtils.title_learn("冒险", 1, "寻宝者", 4, context)
            context.run_task("Fight_ReturnMainWindow")
        elif self.layers == 27:
            fightUtils.title_learn("战斗", 1, "见习战士", 1, context)
            fightUtils.title_learn("战斗", 2, "战士", 3, context)
            fightUtils.title_learn("战斗", 3, "剑舞者", 1, context)
            fightUtils.title_learn("战斗", 4, "炎龙武士", 1, context)
            fightUtils.title_learn("战斗", 5, "毁灭公爵", 1, context)

            context.run_task("Fight_ReturnMainWindow")
            fightUtils.title_learn("魔法", 1, "魔法学徒", 3, context)
            fightUtils.title_learn("魔法", 2, "白袍法师", 1, context)
            fightUtils.title_learn("魔法", 3, "祭司", 1, context)
            fightUtils.title_learn("魔法", 4, "气系大师", 1, context)
            fightUtils.title_learn("魔法", 5, "传奇法师", 1, context)

            context.run_task("Fight_ReturnMainWindow")
            fightUtils.title_learn_branch("魔法", 5, "生命强化", 1, context)
            fightUtils.title_learn_branch("战斗", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("战斗", 5, "攻击强化", 3, context)

            context.run_task("Fight_ReturnMainWindow")
            context.run_task("Save_Status")
            context.run_task("Fight_ReturnMainWindow")
        elif self.layers == 64:
            fightUtils.title_learn("冒险", 1, "寻宝者", 4, context)
            fightUtils.title_learn("冒险", 2, "探险家", 1, context)
            fightUtils.title_learn("冒险", 3, "暗行者", 1, context)
            fightUtils.title_learn("冒险", 4, "魔盗", 1, context)
            fightUtils.title_learn("冒险", 5, "异界游侠", 1, context)

            context.run_task("Fight_ReturnMainWindow")
            fightUtils.title_learn_branch("冒险", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "攻击强化", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "魔力强化", 3, context)

            fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "魔法强化", 3, context)
            context.run_task("Fight_ReturnMainWindow")
        elif self.layers == 89:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 3, context)
            fightUtils.title_learn("魔法", 2, "白袍法师", 3, context)
            fightUtils.title_learn("魔法", 4, "气系大师", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)

            context.run_task("Fight_ReturnMainWindow")
        return True

    def Check_DefaultStatus(self, context: Context):
        # boos战前和战后操作
        if (
            self.layers >= 51
            and self.layers <= 90
            and (self.layers % 10 == 9 or self.layers % 10 == 1)
        ):
            context.run_task("JJC_OpenForceOfNature")
            StatusDetail: dict = fightUtils.checkGumballsStatusV2(context)
            if (
                float(StatusDetail["当前生命值"]) / float(StatusDetail["最大生命值"])
                <= 0.7
            ):
                logger.info("当前生命值小于70%，使用治疗")

                fightUtils.cast_magic("气", "静电术", context)
                for _ in range(5):
                    if not fightUtils.cast_magic("光", "神恩术", context):
                        fightUtils.cast_magic("水", "治疗术", context)
            else:
                logger.info("当前生命值大于70%，不使用治疗")

        # 保命
        if (
            self.layers == 89
            and fightUtils.checkBuffStatus("神圣重生", context) != True
        ):
            fightUtils.cast_magic("光", "神圣重生", context)

        return True

    def handle_abattoir_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if self.layers % 10 == 5 and context.run_recognition(
            "JJC_Find_Abattoir",
            image,
        ):
            logger.info(f"current layers {self.layers} 开始进入角斗场战斗！！！")
            context.run_task("JJC_Find_Abattoir")
            if self.layers <= 25:
                fightUtils.cast_magic("光", "祝福术", context)
                for _ in range(3):
                    fightUtils.cast_magic_special("天眼", context)
            elif self.layers <= 55:
                fightUtils.cast_magic("火", "失明术", context, (boss_x, boss_y))
                for _ in range(3):
                    context.tasker.controller.post_click(boss_x, boss_y).wait()
                    time.sleep(0.3)
                for _ in range(3):
                    if fightUtils.cast_magic("光", "祝福术", context):
                        pass
                    elif fightUtils.cast_magic("水", "治疗术", context):
                        pass
                    elif fightUtils.cast_magic("土", "石肤术", context):
                        pass
            elif self.layers <= 75:
                context.run_task("Bag_Open")
                fightUtils.findItem("异域的灯芯", True, context, boss_x, boss_y)
                context.run_task("Bag_Open")
                fightUtils.findItem("异域的灯芯", True, context, boss_x, boss_y)
                for _ in range(3):
                    if fightUtils.cast_magic("光", "祝福术", context):
                        pass
                    elif fightUtils.cast_magic("水", "治疗术", context):
                        pass
                    elif fightUtils.cast_magic("土", "石肤术", context):
                        pass
            else:
                # 打开背包
                time.sleep(3)
                context.run_task("Bag_Open")
                fightUtils.findItem("异域的灯芯", True, context, boss_x, boss_y)
                context.run_task("Bag_Open")
                fightUtils.findItem("异域的灯芯", True, context, boss_x, boss_y)

            time.sleep(1)
            context.run_task("Fight_Victory")
            context.run_task("JJC_Abattoir_Chest")
            context.run_task("Fight_OpenedDoor")
        return True

    def handle_boos_80_event(self, context: Context):
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
        time.sleep(3)

    def handle_boos_100_event(self, context: Context):
        fightUtils.cast_magic("气", "静电场", context)
        fightUtils.cast_magic("火", "毁灭之刃", context)
        fightUtils.cast_magic("暗", "变形术", context)
        for _ in range(6):
            context.tasker.controller.post_click(boss_x, boss_y).wait()
            time.sleep(0.1)

    def handle_boos_event(self, context: Context):
        if self.layers <= 60:
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
            self.handle_boos_80_event(context)

        elif self.layers <= 100:
            if fightUtils.cast_magic("气", "时间停止", context):
                self.handle_boos_100_event(context)
            else:
                self.handle_boos_80_event(context)
        # 捡东西
        time.sleep(2)
        context.run_task("Fight_OpenedDoor")
        return True

    def handle_dog_event(self, context: Context):
        # 自动叫狗事件
        if self.layers >= 27 and self.layers <= 29 and self.isHaveDog != True:
            if fightUtils.Auto_CallDog(context):
                self.isHaveDog = True
            elif self.layers == 29:
                logger.error("29层未触发毁灭, 自动叫狗失败, 太黑了吧, 用户来接管吧")
                return False
        return True

    def handle_layers_event(self, context: Context):
        self.Check_DefaultEquipment(context)
        self.Check_DefaultTitle(context)
        self.Check_DefaultStatus(context)
        self.handle_dog_event(context)
        self.handle_abattoir_event(context)
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

            # 检查当前层数
            RunResult = context.run_task("Fight_CheckLayer")
            if RunResult.nodes:
                self.layers = fightUtils.extract_numbers(
                    RunResult.nodes[0].recognition.best_result.text
                )

            # 检查是否到达100层
            if self.layers == 96:
                logger.info(f"current layers {self.layers}, 开始退出agent")
                break
            logger.info(f"Start Explore {self.layers} layer.")

            # 检测是否触发层数事件
            self.handle_layers_event(context)

            # Boos层开始探索
            if self.layers >= 30 and self.layers % 10 == 0:
                # boss召唤动作
                time.sleep(6)
                self.handle_boos_event(context)
                # 检测神龙
                time.sleep(1)
                img = context.tasker.controller.post_screencap().wait().get()
                if context.run_recognition("Fight_FindDragon", img):
                    logger.info("是神龙,俺,俺们有救了！！！")
                    fightUtils.dragonwish("工资", context)
                    logger.info("神龙带肥家lo~")

                continue

            # 小怪层探索
            else:
                if (
                    self.layers >= 85
                    and self.layers % 2 == 0
                    and fightUtils.cast_magic("土", "地震术", context)
                ):
                    pass
                else:
                    context.run_task("JJC_Fight_ClearCurrentLayer")
            time.sleep(1)

            # 检测完美击败
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition(
                "Fight_Perfect",
                image,
            ):
                time.sleep(2)

            # 检测卡剧情
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition(
                "JJC_Inter_Confirm",
                image,
            ):
                logger.info("检测到卡剧情, 本层重新探索")
                context.run_task("JJC_Inter_Confirm")
                continue

            # 检测卡返回
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition("BackText", image):
                logger.info("检测到卡返回, 本层重新探索")
                context.run_task("Fight_ReturnMainWindow")
                continue

            # 胜利者石柱
            if self.layers <= 26:
                context.run_task("JJC_StoneChest")

            # 寻找斯巴达头盔
            if self.isHaveSpartanHat != True:
                # 检测三次斯巴达的头盔，检查到了就提前结束检查
                for _ in range(3):
                    img = context.tasker.controller.post_screencap().wait().get()
                    if context.run_recognition("JJC_Find_Body", img):
                        context.run_task("JJC_Find_Body")
                        self.isHaveSpartanHat = True
                        logger.info("已有斯巴达头盔，或找到斯巴达头盔了！！")
                        break

            # 该层探索结束
            recoDetail = context.run_task("Fight_OpenedDoor")
            if recoDetail.nodes:
                pass
            else:
                img = context.tasker.controller.post_screencap().wait().get()
                if context.run_recognition("FindKeyHole", img):
                    logger.warning("检查到钥匙孔，请自行检查")
                    time.sleep(60)
                    return CustomAction.RunResult(success=False)

        logger.info(f"竞技场探索结束，当前到达{self.layers}层")
        context.run_task("Fight_LeaveMaze")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC_Fight_ClearCurrentLayer")
class JJC_Fight_ClearCurrentLayer(CustomAction):

    def CheckMonsterCnt(self, context: Context):
        global visited
        img = context.tasker.controller.post_screencap().wait().get()

        # 检测是否有怪物并攻击
        for r in range(rows):
            for c in range(cols):  # 重试次数
                if visited[r][c] >= 30:
                    continue
                # 计算 ROI 区域
                x, y, w, h = roi_matrix[r][c]
                roi_image = img[y : y + h, x : x + w]
                left_bottom_roi = roi_image[0:60, 0:60].copy()  # 提取左上角 20x20 区域
                left_reco_detail = context.run_recognition(
                    "GridMonsterCheckTemplate",
                    left_bottom_roi,
                    pipeline_override={
                        "GridMonsterCheckTemplate": {
                            "recognition": "ColorMatch",
                            "method": 4,
                            "lower": [190, 35, 35],
                            "upper": [230, 65, 65],
                            "count": 20,
                        }
                    },
                )

                if left_reco_detail:
                    visited[r][c] += 1
                    # logger.info(f"检测({r + 1},{c + 1})有怪物: {x}, {y}, {w}, {h}")
                    for _ in range(3):
                        context.tasker.controller.post_click(
                            x + w // 2, y + h // 2
                        ).wait()
                        time.sleep(0.1)
        return True

    def CheckClosedDoor(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if recoDetail := context.run_recognition("Fight_ClosedDoor", image):
            for r in range(rows):
                for c in range(cols):
                    if fightUtils.is_roi_in_or_mostly_in(
                        recoDetail.box, roi_matrix[r][c]
                    ):
                        logger.info(f"识别到 ClosedDoor 位于 {r+1},{c+1}")
                        return r, c
        return 0, 0

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # 初始化
        isCheckDragon = False
        FailCheckMonsterCnt = 0
        FailCheckGridCnt = 0
        checkGridCnt = 0
        global visited
        DoorX, DoorY = self.CheckClosedDoor(context)
        visited = [[0] * cols for _ in range(rows)]
        visited[DoorX][DoorY] = 999

        if context.run_recognition(
            "Fight_CheckDragonBall",
            context.tasker.controller.post_screencap().wait().get(),
        ):
            isCheckDragon = True
        else:
            isCheckDragon = False

        # 开始清理当前层
        cnt = 15
        while cnt > 0:
            if context.tasker.stopping:
                logger.info("JJC_Fight_ClearCurrentLayer 被停止")
                return CustomAction.RunResult(success=False)

            # 截图
            img = context.tasker.controller.post_screencap().wait().get()

            # 检测神龙
            if isCheckDragon and context.run_recognition("Fight_FindDragon", img):
                logger.info("是神龙,俺,俺们有救了！！！")
                fightUtils.dragonwish("工资", context)
                logger.info("神龙带肥家lo~")
                continue

            # 检测地板
            cnt -= 1
            checkGridCnt = 0
            for r in range(rows):
                for c in range(cols):  # 重试次数
                    # 如果已经访问过该格子，并且已经清理过，跳过
                    if visited[r][c] >= 5:
                        continue

                    # 计算 ROI 区域
                    x, y, w, h = roi_matrix[r][c]
                    roi_image = img[y : y + h, x : x + w]
                    left_bottom_roi = roi_image[
                        h - 15 : h, 0:20
                    ].copy()  # 提取左下角 20x20 区域
                    right_bottom_roi = roi_image[
                        h - 15 : h, w - 20 : w
                    ].copy()  # 提取右下角 20x20 区域

                    left_reco_detail = context.run_recognition(
                        "GridCheckTemplate",
                        left_bottom_roi,
                        pipeline_override={
                            "GridCheckTemplate": {
                                "recognition": "ColorMatch",
                                "method": 4,
                                "lower": [130, 135, 143],
                                "upper": [170, 175, 183],
                                "count": 10,
                            }
                        },
                    )
                    right_reco_detail = context.run_recognition(
                        "GridCheckTemplate",
                        right_bottom_roi,
                        pipeline_override={
                            "GridCheckTemplate": {
                                "recognition": "ColorMatch",
                                "method": 4,
                                "lower": [130, 135, 143],
                                "upper": [170, 175, 183],
                                "count": 10,
                            }
                        },
                    )

                    if left_reco_detail or right_reco_detail:
                        context.tasker.controller.post_click(
                            x + w // 2, y + h // 2
                        ).wait()
                        visited[r][c] += 1
                        checkGridCnt += 1
                        time.sleep(0.05)

            # 检测怪物并进行攻击
            if not self.CheckMonsterCnt(context):
                FailCheckMonsterCnt += 1

            # 检测grid是否清理完, 几次清理完则退出
            if not checkGridCnt:
                FailCheckGridCnt += 1

            # 如果提前清理完该层，那么不需要继续等待，可以提前退出
            if FailCheckMonsterCnt >= 5 or FailCheckGridCnt >= 3:
                logger.info("找不到怪物或格子, 检测下一层的门")
                break

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
            pipeline_override={"Seleect_InputBox_Text": {"input_text": "自然之子"}},
        )

        # logger.info("选择贵族")
        context.run_task(
            "Select_Gumball_2",
            pipeline_override={"Seleect_InputBox_Text": {"input_text": "贵族"}},
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
        # fightUtils.checkGumballsStatusV2(context)
        context.run_task("Bag_Open")
        if not fightUtils.findItem("东方剪纸", False, context):
            logger.info("未找到东方剪纸, 已经叫过狗了")
            self.isHaveDog = True
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
