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


@AgentServer.custom_action("mars101")
class mars101(CustomAction):
    def __init__(self):
        super().__init__()
        # self.isHaveSpartanHat = False
        # self.isHaveDog = False
        self.isTitle_L1 = False
        self.isTitle_L49 = False
        # self.isTitle_L63 = False
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

    def Check_DefaultEquipment(self, context: Context):
        """
        检查默认装备
        1. 检查出图装备
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
        return True

    def Check_DefaultTitle(self, context: Context):
        """
        检查默认称号
        1. 检查49层的称号
        """
        if (self.layers == 1 or self.layers == 2) and self.isTitle_L1 == False:
            fightUtils.title_learn("冒险", 1, "寻宝者", 1, context)
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L1 = True
        elif (self.layers == 48 or self.layers == 49) and self.isTitle_L49 == False:

            context.run_task("Fight_ReturnMainWindow")
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
            context.run_task("Save_Status")
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L49 = True

    def Check_DefaultStatus(self, context: Context):

        # 检查冈布奥状态
        tempNum = self.layers % 10
        if (self.layers >= 55 and (tempNum == 1 or tempNum == 5 or tempNum == 9)) or (
            self.layers >= 90 and tempNum == 4
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

        # 保命
        if self.layers == 89 and not fightUtils.checkBuffStatus("神圣重生", context):
            fightUtils.cast_magic("光", "神圣重生", context)

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

    def handle_boos_100_event(self, context: Context):
        fightUtils.cast_magic("气", "静电场", context)
        fightUtils.cast_magic("火", "毁灭之刃", context)
        fightUtils.cast_magic("气", "瓦解射线", context)
        for _ in range(6):
            context.tasker.controller.post_click(boss_x, boss_y).wait()
            time.sleep(0.3)

    def handle_boos_100Dragon_event(self, context: Context):
        fightUtils.cast_magic("火", "失明术", context)
        for _ in range(2):
            context.tasker.controller.post_click(boss_x, boss_y).wait()
        fightUtils.cast_magic("特殊", "龙威", context)
        for _ in range(2):
            context.tasker.controller.post_click(boss_x, boss_y).wait()
        fightUtils.cast_magic("火", "失明术", context)
        for _ in range(2):
            context.tasker.controller.post_click(boss_x, boss_y).wait()

    def handle_boos_event(self, context: Context):
        if self.layers <= 60:
            for _ in range(3):
                if not fightUtils.cast_magic_special("生命颂歌", context):
                    break
            fightUtils.cast_magic("光", "祝福术", context)
            for _ in range(5):
                context.tasker.controller.post_click(boss_x, boss_y).wait()

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

    def handle_preLayers_event(self, context: Context):
        logger.info(f"第{self.layers}层 战前准备")
        self.Check_DefaultEquipment(context)
        self.Check_DefaultTitle(context)
        return True

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

    def handle_marsRuinsShop_event(self, context: Context):
        # 打开技能商店
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("mars_RuinsShop", image):
            context.run_task("mars_RuinsShop")

    def handle_marsReward_event(self, context: Context):
        if context.run_recognition(
            "mars_Reward", context.tasker.controller.post_screencap().wait().get()
        ):
            context.run_task("mars_Reward")
        if context.run_recognition(
            "mars_BossReward", context.tasker.controller.post_screencap().wait().get()
        ):
            context.run_task("mars_BossReward")

    def handle_marsBody_event(self, context: Context):
        while context.run_recognition(
            "mars_Body", context.tasker.controller.post_screencap().wait().get()
        ):
            context.run_task("mars_Body")

    def handle_marsStele_event(self, context: Context):
        if context.run_recognition(
            "mars_Stele", context.tasker.controller.post_screencap().wait().get()
        ):
            context.run_task("mars_Stele")

    def handle_postLayers_event(self, context: Context):
        logger.info(f"第{self.layers}层 战后事件检测中")
        self.Check_DefaultStatus(context)
        self.handle_marsBody_event(context)
        self.handle_marsStele_event(context)
        self.handle_marsReward_event(context)
        self.handle_downstair_event(context)

    def handle_clearCurLayer_event(self, context: Context):
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

            return False
        # 小怪层探索
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


@AgentServer.custom_action("mars_Fight_ClearCurrentLayer")
class mars_Fight_ClearCurrentLayer(CustomAction):

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
                LeftBottomImg = roi_image[0:60, 0:60].copy()  # 提取左下角 20x20 区域
                left_detected = fightUtils.rgb_pixel_count(
                    LeftBottomImg, [190, 35, 35], [235, 65, 65], 20, context
                )
                if left_detected:
                    visited[r][c] += 1
                    # logger.info(f"检测({r + 1},{c + 1})有怪物: {x}, {y}, {w}, {h}")
                    for _ in range(3):
                        context.tasker.controller.post_click(
                            x + w // 2, y + h // 2
                        ).wait()
                        time.sleep(0.1)
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

    def CheckOpenedDoor(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if recoDetail := context.run_recognition("Fight_OpenedDoor", image):
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
        if DoorX == 0 and DoorY == 0:
            DoorX, DoorY = self.CheckOpenedDoor(context)
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
        cnt = 18
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
                    LeftBottomImg = roi_image[
                        h - 15 : h, 0:20
                    ].copy()  # 提取左下角 20x20 区域
                    RightBottomImg = roi_image[
                        h - 15 : h, w - 20 : w
                    ].copy()  # 提取右下角 20x20 区域

                    # OpenCV方式
                    left_detected = fightUtils.rgb_pixel_count(
                        LeftBottomImg, [130, 135, 143], [170, 175, 183], 50, context
                    )
                    right_detected = fightUtils.rgb_pixel_count(
                        RightBottomImg, [130, 135, 143], [170, 175, 183], 50, context
                    )

                    if left_detected or right_detected:
                        context.tasker.controller.post_click(
                            x + w // 2, y + h // 2
                        ).wait()
                        visited[r][c] += 1
                        checkGridCnt += 1
                        time.sleep(0.1)

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
