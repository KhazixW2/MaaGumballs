from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from loguru import logger

from action import utils
from action.Fight import fightUtils

import time

cols, rows = 5, 6
roi_list = utils.calRoiList()
roi_matrix = [roi_list[i * cols : (i + 1) * cols] for i in range(rows)]
visited = [[0] * cols for _ in range(rows)]


# 等待测试
@AgentServer.custom_action("Fight_ClearCurrentLayerTimeStop")
class Fight_ClearCurrentLayerTimeStop(CustomAction):

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
                # 提取右下角 30x30 区域

                right_bottom_roi = roi_image[-30:, -30:].copy()  # 提取右下角 30x30 区域
                right_reco_detail = context.run_recognition(
                    "GridMonsterCheckTemplate",
                    right_bottom_roi,
                    pipeline_override={
                        "GridMonsterCheckTemplate": {
                            "recognition": "ColorMatch",
                            "method": 4,
                            "lower": [175, 175, 175],
                            "upper": [193, 193, 193],
                            "count": 20,
                        }
                    },
                )

                if right_reco_detail:
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
                    if utils.is_roi_in_or_mostly_in(recoDetail.box, roi_matrix[r][c]):
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
                                "lower": [125, 125, 125],
                                "upper": [230, 230, 230],
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
