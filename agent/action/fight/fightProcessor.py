from maa.context import Context
from utils import logger
from action.fight import fightUtils
from typing import Tuple
from typing import List

import time
import cv2
import numpy as np


class FightProcessor:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    # 执行函数
    def __init__(self):
        if not hasattr(self, "initialized"):
            super().__init__()
            self.cols = 5
            self.rows = 6
            self.roi_matrix = []
            self.visited = []
            self._monster_lower = [190, 35, 35]
            self._monster_upper = [235, 65, 65]
            self._monster_count = 20
            self._grid_lower = [130, 135, 143]
            self._grid_upper = [170, 175, 183]
            self._grid_count = 10
            self._hit_monster_count = 3
            self.max_grid_loop = 20
            self.max_monster_loop_fail = 4
            self.max_grid_loop_fail = 4
            self.isCheckDragon = False
            self.targetWish = "工资"

            # 初始化逻辑
            roi_list = self.generate_floor_roi_grid()
            self.roi_matrix = [
                roi_list[i * self.cols : (i + 1) * self.cols] for i in range(self.rows)
            ]
            self.visited = [[0] * self.cols for _ in range(self.rows)]
            self.initialized = True

    @property
    def monster_lower(self):
        return self._monster_lower

    @monster_lower.setter
    def monster_lower(self, value):
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError("monster_lower must be a list of 3 integers")
        if not all(isinstance(x, int) for x in value):
            raise TypeError("All elements in monster_lower must be integers")
        self._monster_lower = value

    @property
    def monster_upper(self):
        return self._monster_upper

    @monster_upper.setter
    def monster_upper(self, value):
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError("monster_upper must be a list of 3 integers")
        if not all(isinstance(x, int) for x in value):
            raise TypeError("All elements in monster_upper must be integers")
        self._monster_upper = value

    @property
    def monster_count(self):
        return self._monster_count

    @monster_count.setter
    def monster_count(self, value):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("monster_count must be a positive integer")
        self._monster_count = value

    @property
    def grid_lower(self):
        return self._grid_lower

    @grid_lower.setter
    def grid_lower(self, value):
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError("grid_lower must be a list of 3 integers")
        if not all(isinstance(x, int) for x in value):
            raise TypeError("All elements in grid_lower must be integers")
        self._grid_lower = value

    @property
    def grid_upper(self):
        return self._grid_upper

    @grid_upper.setter
    def grid_upper(self, value):
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError("grid_upper must be a list of 3 integers")
        if not all(isinstance(x, int) for x in value):
            raise TypeError("All elements in grid_upper must be integers")
        self._grid_upper = value

    @property
    def grid_count(self):
        return self._grid_count

    @grid_count.setter
    def grid_count(self, value):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("grid_count must be a positive integer")
        self._grid_count = value

    @property
    def hit_monster_count(self):
        return self._hit_monster_count

    @hit_monster_count.setter
    def hit_monster_count(self, value):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("hit_monster_count must be a positive integer")
        self._hit_monster_count = value

    def generate_floor_roi_grid(self) -> List[List[int]]:
        """生成地板网格的ROI区域列表

        根据预设的网格布局参数，计算并返回所有地板格子的ROI坐标
        ROI格式为 [x, y, width, height]

        Returns:
            List[List[int]]: 包含所有地板格子ROI的二维列表
        """
        # 网格布局常量（可考虑移至类属性或配置文件）
        START_X, START_Y = 15, 222
        CELL_WIDTH, CELL_HEIGHT = 138, 126
        GRID_COLS, GRID_ROWS = 5, 6

        return [
            [
                START_X + col * CELL_WIDTH,
                START_Y + row * CELL_HEIGHT,
                CELL_WIDTH,
                CELL_HEIGHT,
            ]
            for row in range(GRID_ROWS)
            for col in range(GRID_COLS)
        ]

    def is_roi_mostly_overlapping(
        self,
        roi1: Tuple[int, int, int, int],
        roi2: Tuple[int, int, int, int],
        threshold: float = 0.5,
    ) -> bool:
        """判断 roi1 是否大部分与 roi2 重叠

        Args:
            roi1: 第一个 ROI,格式为 (x, y, width, height)
            roi2: 第二个 ROI,格式为 (x, y, width, height)
            threshold: 重叠面积阈值，默认为 0.5(即 50%)

        Returns:
            bool: 当 roi1 与 roi2 的交集面积占 roi1 面积的比例大于等于阈值时返回 True

        Raises:
            ValueError: 当 ROI 参数包含非正值时触发
        """
        # 验证 ROI 参数有效性
        if any(v <= 0 for v in roi1[2:] + roi2[2:]):
            raise ValueError("ROI 的宽度和高度必须为正数")

        # 计算交集区域坐标
        inter_x1 = max(roi1[0], roi2[0])
        inter_y1 = max(roi1[1], roi2[1])
        inter_x2 = min(roi1[0] + roi1[2], roi2[0] + roi2[2])
        inter_y2 = min(roi1[1] + roi1[3], roi2[1] + roi2[3])

        # 计算交集面积和 roi1 面积
        if inter_x2 > inter_x1 and inter_y2 > inter_y1:
            intersection_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
            roi1_area = roi1[2] * roi1[3]
            return intersection_area / roi1_area >= threshold
        return False

    def bgrColorMatch(
        self,
        image,
        lower,
        upper,
        count,
        context: Context,
        method="opencv",
    ) -> int:
        """
        RGB颜色空间像素计数
        :param image: BGR格式图像（需转换）
        :type image: numpy.ndarray
        :param lower: RGB下限 [R,G,B] (0-255)
        :param upper: RGB上限 [R,G,B]
        :param count: 15
        :return: 匹配像素数量
        """

        # RGB转BGR
        lower = [lower[2], lower[1], lower[0]]
        upper = [upper[2], upper[1], upper[0]]

        if method == "opencv":
            # 创建三维掩膜
            lower_bound = np.array(lower, dtype=np.uint8)
            upper_bound = np.array(upper, dtype=np.uint8)
            mask = cv2.inRange(image, lower_bound, upper_bound)

            # 统计有效像素数量
            valid_pixel_count = cv2.countNonZero(mask)
            return valid_pixel_count if valid_pixel_count > count else 0

        elif recoDetail := context.run_recognition(
            "GridCheckTemplate",
            image,
            pipeline_override={
                "GridCheckTemplate": {
                    "recognition": "ColorMatch",
                    "method": 4,
                    "lower": lower,
                    "upper": upper,
                    "count": count,
                }
            },
        ):
            if recoDetail:
                valid_pixel_count = recoDetail.best_result.count
                return valid_pixel_count if valid_pixel_count > count else 0
            return 0
        else:
            return 0

    def checkMonster(self, context: Context) -> bool:
        logger.debug(f"{self.visited}")
        img = context.tasker.controller.post_screencap().wait().get()
        monster_count = 0

        # 检测是否有怪物并攻击
        for r in range(self.rows):
            for c in range(self.cols):
                if self.visited[r][c] >= 30:
                    continue

                # 计算 ROI 区域
                x, y, w, h = self.roi_matrix[r][c]
                roi_image = img[y : y + h, x : x + w]
                left_bottom_img = roi_image[0:60, 0:60].copy()

                # 检测左上角区块是否存在血条
                if left_detected := self.bgrColorMatch(
                    left_bottom_img,
                    self.monster_lower,
                    self.monster_upper,
                    self.monster_count,
                    context,
                ):
                    self.visited[r][c] += 1
                    monster_count += 1
                    logger.debug(f"检测({r + 1},{c + 1})有怪物: {x}, {y}, {w}, {h}")
                    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # 四方向
                    for direction in directions:
                        new_r, new_c = r + direction[0], c + direction[1]
                        if 0 <= new_r < self.rows and 0 <= new_c < self.cols:
                            if self.visited[new_r][new_c] == 0:
                                continue
                            else:
                                logger.debug(
                                    f"({new_r + 1},{new_c + 1})已被访问, 可以攻击到({r + 1},{c + 1})的怪物"
                                )
                                for _ in range(self.hit_monster_count):
                                    context.tasker.controller.post_click(
                                        x + w // 2, y + h // 2
                                    ).wait()
                                    time.sleep(0.05)
                                break

        return monster_count > 0

    def checkClosedDoor(self, context: Context) -> tuple[int, int]:
        if recoDetail := context.run_recognition(
            "Fight_ClosedDoor", context.tasker.controller.post_screencap().wait().get()
        ):
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.is_roi_mostly_overlapping(
                        recoDetail.box, self.roi_matrix[r][c]
                    ):
                        # logger.info(f"识别到 ClosedDoor 位于 {r+1},{c+1}")
                        return r, c
        return 0, 0

    def checkOpenedDoor(self, context: Context) -> tuple[int, int]:
        if recoDetail := context.run_recognition(
            "Fight_OpenedDoor", context.tasker.controller.post_screencap().wait().get()
        ):
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.is_roi_mostly_overlapping(
                        recoDetail.box, self.roi_matrix[r][c]
                    ):
                        # logger.info(f"识别到 OpenedDoor 位于 {r+1},{c+1}")
                        return r, c
        return 0, 0

    def checkIsDragonBall(self, context: Context):
        if context.run_recognition(
            "Fight_CheckDragonBall",
            context.tasker.controller.post_screencap().wait().get(),
        ):
            self.isCheckDragon = True
        else:
            self.isCheckDragon = False

    def detect_and_click_grid(self, context: Context, img) -> int:
        """
        检测并点击地板格子
        :param context: 上下文对象
        :param img: 当前截图
        :return: 点击的格子数量
        """
        checkGridCnt = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if self.visited[r][c] >= 5:
                    continue

                x, y, w, h = self.roi_matrix[r][c]
                roi_image = img[y : y + h, x : x + w]
                # 提取左下角和右下角区域
                left_img = roi_image[h - 15 : h, 0:20].copy()
                right_img = roi_image[h - 15 : h, w - 20 : w].copy()

                # 使用实例变量中的颜色阈值
                left_detected = self.bgrColorMatch(
                    left_img, self.grid_lower, self.grid_upper, self.grid_count, context
                )
                right_detected = self.bgrColorMatch(
                    right_img,
                    self.grid_lower,
                    self.grid_upper,
                    self.grid_count,
                    context,
                )

                if left_detected or right_detected:
                    context.tasker.controller.post_click(x + w // 2, y + h // 2).wait()
                    self.visited[r][c] += 1
                    checkGridCnt += 1
                    time.sleep(0.03)
        time.sleep(0.15)
        return checkGridCnt

    def handle_dragon_encounter(self, context: Context, img):
        """处理遇到神龙的逻辑"""
        if self.isCheckDragon and context.run_recognition("Fight_FindDragon", img):
            logger.info("是神龙,俺,俺们有救了！！！")
            fightUtils.dragonwish(self.targetWish, context)
            logger.info("神龙带肥家lo~")
            return True
        return False

    def clearCurrentLayer(self, context: Context, isclearall: bool = False):
        # 初始化
        fail_check_grid_cnt = 0
        fail_check_monster_cnt = 0
        DoorX, DoorY = self.checkClosedDoor(context)
        if DoorX == 0 and DoorY == 0:  # 没检测到关着的门
            DoorX, DoorY = self.checkOpenedDoor(context)  # 那就检测开着的门
        self.visited = [[0] * self.cols for _ in range(self.rows)]
        self.visited[DoorX][DoorY] = 999

        self.checkIsDragonBall(context)

        # 开始清理当前层
        for _ in range(self.max_grid_loop):
            if context.tasker.stopping:
                logger.info("清层任务被停止")
                return False

            # 截图,检测神龙和地板
            img = context.tasker.controller.post_screencap().wait().get()
            if self.handle_dragon_encounter(context, img):
                continue

            # 检测grid还能不能找到, 累计几次找不到则退出
            if not self.detect_and_click_grid(context, img):
                fail_check_grid_cnt += 1
                if fail_check_grid_cnt >= self.max_grid_loop_fail - 3:
                    # 连续多次找不到地板,则全部标记为已访问, 避免死循环
                    for r in range(self.rows):
                        for c in range(self.cols):
                            if self.visited[r][c] == 0:
                                self.visited[r][c] += 2
            else:
                fail_check_grid_cnt = 0

            # 检测怪物并进行攻击
            if not self.checkMonster(context):
                fail_check_monster_cnt += 1
            else:
                fail_check_monster_cnt = 0
            logger.debug(
                f"连续检查不到地板轮次: {fail_check_grid_cnt}, 连续检查不到怪物轮次: {fail_check_monster_cnt}"
            )

            if isclearall:
                # 需要地板怪物全清
                if (
                    fail_check_monster_cnt >= self.max_monster_loop_fail
                    and fail_check_grid_cnt >= self.max_grid_loop_fail
                ):
                    break
            # 如果提前清理完该层，那么不需要继续等待，可以提前退出
            elif (
                fail_check_monster_cnt >= self.max_monster_loop_fail
                or fail_check_grid_cnt >= self.max_grid_loop_fail
            ):
                break
        logger.info("已完成清理当前层~")
        return True
