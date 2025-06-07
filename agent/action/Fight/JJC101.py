from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from loguru import logger

from action import Utils
from action.Fight import FightUtils

import time

cols, rows = 5, 6
roi_list = Utils.calRoiList()
roi_matrix = [roi_list[i * cols : (i + 1) * cols] for i in range(rows)]
visited = [[0] * cols for _ in range(rows)]


@AgentServer.custom_action("JJC101")
class JJC101(CustomAction):
    # 从一个字符串里面识仅识别一串数字, 并返回

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # 检查当前层数
        layers = 1
        RunResult = context.run_task("Fight_CheckLayer")
        if RunResult.nodes:
            layers = Utils.extract_numbers(
                RunResult.nodes[0].recognition.best_result.text
            )
            logger.info(f"current layer {layers}")

        # 检查当前层数是否小于29层
        while layers < 101:
            # 检查是否停止任务
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)

            # 检查当前层数
            RunResult = context.run_task("Fight_CheckLayer")
            if RunResult.nodes:
                layers = Utils.extract_numbers(
                    RunResult.nodes[0].recognition.best_result.text
                )

            # 检查是否到达100层
            if layers > 100:
                logger.info("到达101层, 开始退出agent")
                continue

            # 角斗场事件
            image = context.tasker.controller.post_screencap().wait().get()
            if layers % 10 == 5 and context.run_recognition(
                "JJC_Find_Abattoir",
                image,
            ):
                if layers < 30:
                    context.run_task("JJC_Find_Abattoir")
                    FightUtils.cast_magic("光", "祝福术", context)
                    FightUtils.cast_magic_special("天眼", context)
                    FightUtils.cast_magic_special("天眼", context)
                    FightUtils.cast_magic_special("天眼", context)
                elif layers >= 30:
                    context.run_task("JJC_Find_Abattoir")
                    FightUtils.cast_magic("土", "石肤术", context)
                    FightUtils.cast_magic("土", "石肤术", context)

                context.run_task("JJC_Fight_ClearCurrentLayer")
                context.run_task("JJC_Abattoir_Chest")
                context.run_task("Fight_OpenedDoor")

            # Boos层开始探索
            if layers >= 30 and layers % 10 == 0:
                # todo
                if layers <= 70:
                    FightUtils.cast_magic("土", "石肤术", context)
                    context.tasker.controller.post_click(640, 360)
                    time.sleep(0.3)
                    context.tasker.controller.post_click(640, 360)
                    time.sleep(0.3)
                    context.tasker.controller.post_click(640, 360)
                    time.sleep(0.3)
                elif layers >= 80 and layers <= 100:
                    if layers >= 90:
                        FightUtils.cast_magic("气", "时间停止", context)
                    FightUtils.cast_magic("气", "瓦解射线", context)
                    context.run_task("JJC_Fight_ClearCurrentLayer")

                context.run_task("Fight_OpenedDoor")
                continue

            # 小怪层探索
            else:
                logger.info(f"Start Explore {layers} layer.")
                context.run_task("JJC_Fight_ClearCurrentLayer")
            time.sleep(1)

            # 检测卡返回，误点击
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition(
                "JJC_Inter_Confirm",
                image,
            ):
                logger.info("检测到卡返回, 本层重新探索")
                context.run_task("JJC_Inter_Confirm")
                continue

            # 胜利者石柱
            context.run_task("JJC_StoneChest")

            # 寻找身体
            img = context.tasker.controller.post_screencap().wait().get()
            RunResult = context.run_recognition("JJC_Find_Body", img)
            if RunResult:
                logger.info("找到斯巴达实体啦")
                context.run_task("JJC_Find_Body")

            # 该层探索结束
            context.run_task("Fight_OpenedDoor")

        logger.info("到达101层, 成功探索1次竞技场101")
        context.run_task("Fight_LeaveMaze")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC_Fight_ClearCurrentLayer")
class JJC_Fight_ClearCurrentLayer(CustomAction):
    def CheckMonster(self, context: Context):
        # 检测是否有怪物并攻击
        image = context.tasker.controller.post_screencap().wait().get()
        checkMonsterDetail = context.run_recognition(
            "GridCheckMonster",
            image,
            pipeline_override={
                "GridCheckMonster": {
                    "recognition": "TemplateMatch",
                    "template": [
                        "fight/JJC/m1.png",
                        "fight/JJC/m2.png",
                        "fight/JJC/m3.png",
                        "fight/JJC/m4.png",
                        "fight/JJC/m5.png",
                    ],
                    "roi": [21, 217, 682, 762],
                    "threshold": 0.7,
                }
            },
        )

        # 对检测到的每个怪物进行攻击
        if checkMonsterDetail:
            for result in checkMonsterDetail.all_results:
                x, y, w, h = result.box
                logger.info(
                    f"检测到第{checkMonsterDetail.all_results.index(result) + 1}个怪物: {x}, {y}, {w}, {h}"
                )
                context.tasker.controller.post_click(x + w // 2, y + h // 2).wait()
                time.sleep(0.1)
                context.tasker.controller.post_click(x + w // 2, y + h // 2).wait()
                time.sleep(0.1)
                context.tasker.controller.post_click(x + w // 2, y + h // 2).wait()
                time.sleep(0.1)
            return True
        else:
            return False

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
                    logger.info(f"检测({r + 1},{c + 1})有怪物: {x}, {y}, {w}, {h}")
                    context.tasker.controller.post_click(x + w // 2, y + h // 2).wait()
                    time.sleep(0.1)
                    context.tasker.controller.post_click(x + w // 2, y + h // 2).wait()
                    time.sleep(0.1)
                    context.tasker.controller.post_click(x + w // 2, y + h // 2).wait()
                    time.sleep(0.1)
        return True

    def CheckClosedDoor(self, context: Context):
        # matrix init
        image = context.tasker.controller.post_screencap().wait().get()
        recoDetail = context.run_recognition("Fight_ClosedDoor", image)
        if recoDetail:
            logger.info("识别到 Fight_ClosedDoor")
            for r in range(rows):
                for c in range(cols):
                    if Utils.is_roi_in_or_mostly_in(recoDetail.box, roi_matrix[r][c]):
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
        FailCheckMonsterCnt = 0
        FailCheckGridCnt = 0
        checkGridCnt = 0
        global visited
        DoorX, DoorY = self.CheckClosedDoor(context)
        visited = [[0] * cols for _ in range(rows)]
        visited[DoorX][DoorY] = 999

        # 开始清理当前层
        cnt = 15
        while cnt > 0:
            if context.tasker.stopping:
                logger.info("JJC_Fight_ClearCurrentLayer 被停止")
                return CustomAction.RunResult(success=False)

            img = context.tasker.controller.post_screencap().wait().get()
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
                    right_context = context.clone()
                    right_reco_detail = right_context.run_recognition(
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
                logger.info("找不到怪物或格子, 提前退出")
                break

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC101_Select")
class JJC101_Select(CustomAction):
    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        logger.info("选择药剂中")
        context.run_task("JJC_SelectDrug")

        logger.info("选择神器中")
        context.run_task("JJC_SelectArtifact")

        # 选择帝释天
        img = context.tasker.controller.post_screencap().wait().get()
        recodetail = context.run_recognition(
            "JJC_Select_Gumball_Check",
            img,
            pipeline_override={
                "JJC_Select_Gumball_Check": {
                    "recognition": "TemplateMatch",
                    "template": ["fight/JJC/帝释天冈布奥_小.png"],
                    "roi": [348, 604, 294, 231],
                },
            },
        )

        if recodetail:
            logger.info("帝释天已检测到")
        else:
            logger.info("帝释天未检测到，自动选择中")
            context.run_task(
                "JJC_Select_Gumball_1",
                pipeline_override={
                    "JJC_Select_Gumball_Next": {
                        "template": "fight/JJC/帝释天冈布奥.png",
                    }
                },
            )

        # 选择夜叉
        img = context.tasker.controller.post_screencap().wait().get()
        recodetail = context.run_recognition(
            "JJC_Select_Gumball_Check",
            img,
            pipeline_override={
                "JJC_Select_Gumball_Check": {
                    "recognition": "TemplateMatch",
                    "template": ["fight/JJC/夜叉冈布奥_小.png"],
                    "roi": [348, 604, 294, 231],
                },
            },
        )
        if recodetail:
            logger.info("夜叉已检测到")
        else:
            logger.info("夜叉未检测到, 自动选择中")
            context.run_task(
                "JJC_Select_Gumball_2",
                pipeline_override={
                    "JJC_Select_Gumball_Next": {
                        "template": "fight/JJC/夜叉冈布奥.png",
                    }
                },
            )

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC101_Title")
class JJC101_Title(CustomAction):

    def Fight_CheckLayer(self, context: Context):
        RunResult = context.run_task("Fight_CheckLayer")
        if RunResult.nodes:
            layers = Utils.extract_numbers(
                RunResult.nodes[0].recognition.best_result.text
            )
            logger.info(f"current layer {layers}")
            return layers
        else:
            return 0

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        # FightUtils.title_learn("战斗", 1, "见习战士", 1, context)
        # FightUtils.title_learn("战斗", 2, "战士", 1, context)
        # FightUtils.title_learn("战斗", 3, "魔战士", 1, context)
        # FightUtils.title_learn("战斗", 4, "炎龙武士", 1, context)
        # FightUtils.title_learn("战斗", 5, "毁灭公爵", 1, context)

        # FightUtils.title_learn_branch("战斗", 5, "生命强化", 3, context)
        # FightUtils.title_learn_branch("战斗", 5, "攻击强化", 3, context)

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("JJC_BagTest")
class JJC_BagTest(CustomAction):

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        # 打开背包
        OpenDetail = context.run_task("Bag_Open")
        if OpenDetail.nodes:
            if not FightUtils.checkEquipment("腰带", 1, "贵族丝带", context):
                FightUtils.findEquipment(1, "贵族丝带", True, context)
            if not FightUtils.checkEquipment("戒指", 2, "礼仪戒指", context):
                FightUtils.findEquipment(2, "礼仪戒指", True, context)
            if not FightUtils.checkEquipment("披风", 3, "天鹅绒斗篷", context):
                FightUtils.findEquipment(3, "天鹅绒斗篷", True, context)
            if not FightUtils.checkEquipment("宝物", 7, "冒险家竖琴", context):
                FightUtils.findEquipment(7, "冒险家竖琴", True, context)
            time.sleep(1)
            context.run_task("BackText")
        else:
            logger.info("背包打开失败")

        return CustomAction.RunResult(success=True)
