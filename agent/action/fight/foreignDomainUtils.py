"""外域(时空域 / 秩序域)通用界面操作工具。
"""

from maa.context import Context

from utils import logger

import time

# 四支舰队在舰队面板中的状态区域, 顺序即默认出战顺序
FLEET_ROIS: dict[str, list[int]] = {
    "奥鲁维": [130, 199, 60, 51],
    "卡纳斯": [227, 200, 63, 50],
    "游荡者": [327, 200, 64, 49],
    "深渊": [425, 199, 64, 53],
}

# 各方向地图边界的检测区域
BOUNDARY_ROIS: dict[str, list[int]] = {
    "LeftTop": [12, 268, 137, 147],
    "RightTop": [549, 276, 161, 147],
    "Right": [597, 272, 96, 871],
    "Left": [14, 275, 116, 766],
    "RightBottom": [590, 1052, 117, 102],
    "LeftBottom": [9, 1011, 145, 125],
}

# 横扫方向 -> 对应的地图滑动节点
MAP_SWIPE_TASKS: dict[str, str] = {
    "Left": "FD_SwipeMapToLeft",
    "Right": "FD_SwipeMapToRight",
}

FLEET_RETURN_TIMEOUT = 300  # 等待所有舰队返回的总时长上限(秒)
FLEET_RETURN_ATTEMPTS = 2  # 召回舰队的尝试轮数
MAP_WRAP_STEPS = 4  # 从地图中央滑到右下角所需的滑动次数
# 一次扫描最多走几整圈, 仅作防死循环兜底(正常靠"整圈无进展"结束)
MAX_SWEEP_PASSES = 20
# 允许"整圈无进展"时继续重扫的圈数上限。星球不会消失, 空圈只说明这轮漏识别,
# 应当回到右下角重新扫; 但连续多圈都没有任何进展就说明确实找不到, 需要兜底退出。
MAX_STALLED_PASSES = 3


class foreignDomainUtils:
    fleetRoiList = FLEET_ROIS
    default_fleets = list(FLEET_ROIS)

    def __init__(self) -> None:
        self._passes = 0  # 累计已完整走完的圈数
        self._progress_in_pass = False  # 本圈是否取得了实质进展
        self._stalled_passes = 0  # 连续没找到目标的圈数(仅 expect_target 模式使用)
        self.direction: str = "Left"  # 当前横扫方向
        self._is_up = False  # 本次横扫是否已经上移过一次

    # ---------------- 内部工具 ----------------

    def _aborted(self, context: Context) -> bool:
        """检测到停止请求时返回 True, 并统一打印退出日志。"""
        if context.tasker.stopping:
            logger.info("检测到停止任务, 开始退出agent")
            return True
        return False

    def _screencap(self, context: Context):
        return context.tasker.controller.post_screencap().wait().get()

    # ---------------- 舰队 ----------------

    # 检查舰队状态，统计空闲舰队数量
    def checkAllFleetStatus(self, context: Context) -> int:
        fleetStatus = context.run_recognition(
            "checkAllFleetStatus",
            self._screencap(context),
            pipeline_override={
                "checkAllFleetStatus": {
                    "recognition": "TemplateMatch",
                    "template": "fight/time_space_domain/fleetFree.png",
                    "roi": [109, 182, 397, 95],
                    "threshold": 0.8,
                }
            },
        )
        if fleetStatus is None or not fleetStatus.hit:
            return 0
        return len(fleetStatus.filtered_results)

    def _wait_all_fleets_free(self, context: Context, timeout: float) -> bool:
        """轮询等待所有舰队空闲, 超时或收到停止请求返回 False。"""
        expected = len(FLEET_ROIS)
        deadline = time.monotonic() + timeout
        while self.checkAllFleetStatus(context) < expected:
            if context.tasker.stopping:
                return False
            if time.monotonic() > deadline:
                return False
            time.sleep(1)
        return True


    def _recall_busy_fleets(self, context: Context, foreign: bool) -> None:
        """对仍在出战的舰队逐个执行召回操作。"""
        taskName = "FD_ReturnFleet" if foreign else "TSD_ReturnFleet"
        img = self._screencap(context)
        for key, roi in FLEET_ROIS.items():
            if self._aborted(context):
                return
            status = context.run_recognition(
                "TSD_checkFreeFleet",
                img,
                pipeline_override={"TSD_checkFreeFleet": {"roi": roi}},
            )
            if status is not None and status.hit:
                logger.info(f"{key}舰队已返回,无需操作")
                continue
            logger.info(f"正在返回{key}舰队")
            context.run_task(
                "TSD_ClickFleet",
                pipeline_override={"TSD_ClickFleet": {"target": roi}},
            )
            pipeline_override: dict = {"TSD_checkTargetFleetFree": {"roi": roi}}
            if not foreign:
                pipeline_override["TSD_View"] = {
                    "next": [
                        "TSD_EndExploit",
                        "[JumpBack]TSD_WithdrawFleet",
                        "[JumpBack]TSD_EndExplore",
                        "[JumpBack]BackText",
                    ]
                }
            context.run_task(taskName, pipeline_override=pipeline_override)
            time.sleep(1)  # 等待召回动画结束, 避免下一次截图取到过渡帧
            img = self._screencap(context)  # 界面已变化, 后续舰队需要用新一帧判断

    def returnFleets(self, context: Context, *, foreign: bool = False) -> bool:
        """召回所有出战舰队。

        返回 True 表示四支舰队均已空闲; 收到停止请求或等待超时返回 False。
        """
        waitPerAttempt = FLEET_RETURN_TIMEOUT // FLEET_RETURN_ATTEMPTS
        for attempt in range(1, FLEET_RETURN_ATTEMPTS + 1):
            if self._aborted(context):
                return False
            if attempt > 1:
                logger.warning(f"仍有舰队未返回, 进行第 {attempt} 轮召回")
            self._recall_busy_fleets(context, foreign)
            if self._wait_all_fleets_free(context, waitPerAttempt):
                logger.info("所有舰队已返回")
                return True
            if context.tasker.stopping:
                logger.info("检测到停止任务, 结束等待所有舰队返回")
                return False
        logger.warning("等待所有舰队返回超时, 可能存在识别失败或界面异常")
        return False

    # 返回所有舰队-外域
    def returnFleets_FD(self, context: Context) -> bool:
        return self.returnFleets(context, foreign=True)

    # 关闭联盟聊天窗口, 返回是否真的执行了关闭
    def closeUnionMsgBox(self, context: Context) -> bool:
        opened = context.run_recognition(
            "checkUnionMsgBox",
            self._screencap(context),
            pipeline_override={
                "checkUnionMsgBox": {
                    "recognition": "TemplateMatch",
                    "template": "fight/time_space_domain/unionMsgOpened.png",
                    "roi": [91, 1042, 80, 80],
                    "threshold": 0.8,
                }
            },
        )
        if opened is None or not opened.hit:
            logger.info("联盟聊天窗口未打开")
            return False
        context.run_task("TSD_closeUnionMsgBox")
        logger.info("关闭联盟聊天窗口")
        return True

    # ---------------- 地图移动 ----------------

    # 检查地图边界, 可复用调用方已有的截图
    def checkBoundary(self, context: Context, direction: str, img=None) -> bool:
        if img is None:
            img = self._screencap(context)
        boundaryList = context.run_recognition(
            "GridCheckTargetBoundary",
            img,
            pipeline_override={
                "GridCheckTargetBoundary": {
                    "recognition": "TemplateMatch",
                    "template": f"fight/time_space_domain/boundary{direction}.png",
                    "roi": BOUNDARY_ROIS[direction],
                    "threshold": 0.92,
                }
            },
        )
        return boundaryList is not None and boundaryList.hit

    def swipeMapToBottomRight(self, context: Context) -> bool:
        """把地图滑到右下角, 作为新一轮扫描的起点。"""
        for _ in range(MAP_WRAP_STEPS):
            if self._aborted(context):
                return False
            context.run_task("FD_SwipeMapMiddleToBottomRight")
        self.direction = "Left"
        self._is_up = False
        return True

    def prepare_sweep(self, context: Context) -> bool:
        """把地图定位到右下角并清空扫描状态, 作为一轮扫描的起点。"""
        self.reset_sweep()
        return self.swipeMapToBottomRight(context)

    def mark_progress(self) -> None:
        """记录本圈取得了实质进展(星球已处理、小怪已清理等)。

        注意: 仅仅"看到目标"不算进展 —— 星球图标处理完也不会消失, 会一直被识别到。
        只有目标被真正处理掉时才应调用本方法, 否则扫描永远判定为"有进展"。
        """
        self._progress_in_pass = True

    def reset_sweep(self) -> None:
        """开始一轮新的地图扫描, 清除上一轮残留的扫描状态。"""
        self._passes = 0
        self._progress_in_pass = False
        self._stalled_passes = 0
        self._is_up = False

    def _swipe(self, context: Context) -> None:
        """按当前横扫方向把地图移动一格。"""
        logger.info("地图移动")
        context.run_task(MAP_SWIPE_TASKS[self.direction])
        self._is_up = False

    def swipeMap(self, context: Context, expect_target: bool = False) -> bool:
        """按当前方向把地图移动一次。

        返回 True 表示还可以继续扫描; 返回 False 表示这张地图已经找不到目标了。

        每完整走到一次左上角记为一圈。因为星球图标处理完也不会从地图上消失,
        "还有进展"必须由调用方通过 mark_progress() 显式告知(只有目标真被处理掉
        才算), 而不能靠"又识别到了目标"判断, 否则圈数永远累积不起来。

        expect_target 区分两种地图模型:
        - False(默认): 目标是会消失的小怪/废墟。整圈无进展 => 地图上没有可做的
          事了, 直接返回 False 结束任务。
        - True: 目标(星球)一定存在且不会消失, 走完一圈没找到只是这轮漏识别,
          应当回到右下角重新扫; 只有连续 MAX_STALLED_PASSES 圈都没进展才放弃。
        """
        img = self._screencap(context)
        if not self.checkBoundary(context, self.direction, img):
            # 未达到边界，地图按当前direction继续移动一次
            self._swipe(context)
            return True

        logger.info(f"地图{self.direction}边界")
        if self.checkBoundary(context, "LeftTop", img):
            # 完整走完一圈, 累计圈数并重置本圈进展标记
            self._passes += 1
            progressed = self._progress_in_pass
            self._progress_in_pass = False
            logger.info(
                f"已到达地图边界, 第 {self._passes} 圈完成"
                f"({'有新进展' if progressed else '无新进展'})"
            )

            if progressed:
                self._stalled_passes = 0
            else:
                self._stalled_passes += 1
                if not expect_target:
                    # 整圈下来没有任何实质进展, 再扫一遍也是同样结果
                    logger.info("整圈无新进展, 地图扫描结束")
                    return False
                if self._stalled_passes >= MAX_STALLED_PASSES:
                    logger.warning(
                        f"已连续 {self._stalled_passes} 圈未发现任何目标, 停止扫描"
                    )
                    return False
                logger.info(
                    f"第 {self._stalled_passes} 圈未发现目标, 目标应当仍存在, "
                    f"回到右下角重新扫描"
                )

            if self._passes >= MAX_SWEEP_PASSES:
                logger.warning(
                    f"已连续扫描 {self._passes} 圈, 达到兜底上限, 停止扫描"
                )
                return False

            # 回到右下角再扫一圈继续找
            self.swipeMapToBottomRight(context)
            return True

        if not self._is_up:  # 未达到左上角，地图上移一次
            logger.info("地图上移")
            context.run_task("FD_SwipeMapToUp")
            self.direction = "Left" if self.direction == "Right" else "Right"
            self._is_up = True
            return True

        # 已经上移过一次，按direction移动一次
        self._swipe(context)
        return True
