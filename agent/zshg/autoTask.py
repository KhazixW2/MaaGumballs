import os
import sys
import json

# 获取当前文件路径并设置Python路径
current_file_path = os.path.abspath(__file__)
current_script_dir = os.path.dirname(current_file_path)
agent_dir = os.path.dirname(current_script_dir)

# 将agent目录添加到sys.path，以便导入utils模块
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from utils import logger


class TaskExtractor:
    """
    任务提取器，用于从OCR识别结果中提取任务信息
    参考jjc101.py的面向对象结构设计
    """

    def __init__(self):
        """
        初始化任务提取器
        """
        self.task_names = ["侠盗", "外来者"]
        self.ignore_text = ["奖励：", "接受", "", "三"]
        self.keywords = ["任务时限：", "敌人等级："]
        self.accept_btn_cache = []

    def extract_tasks_from_ocr(self, ocr_data: dict) -> list:
        """
        从OCR数据中提取任务信息（合并版）

        Args:
            ocr_data: OCR识别结果的JSON数据

        Returns:
            提取的任务列表，包含任务详情和接受按钮坐标
        """
        # 按Y坐标排序，还原屏幕视觉上下顺序
        sorted_items = sorted(ocr_data["all"], key=lambda x: x["box"][1])
        tasks = []
        current_task = None
        accept_buttons = []

        # 预提取所有接受按钮的坐标
        for item in sorted_items:
            if item["text"].strip() == "接受":
                accept_buttons.append({"box": item["box"], "y": item["box"][1]})

        for item in sorted_items:
            text = item["text"].strip()
            y = item["box"][1]

            # 跳过无效文本
            if text in self.ignore_text:
                continue

            # 触发新任务
            if text in self.task_names:
                if current_task:
                    tasks.append(current_task)
                # 初始化任务对象
                current_task = {
                    "任务名称": text,
                    "任务描述": "",
                    "敌人等级": "未识别",
                    "任务时限": "未识别",
                    "奖励货币": "未识别",
                    "奖励数值": "未识别",
                    "y_start": y,
                    "接受按钮_box": "未识别",
                    "接受按钮中心坐标": "未识别",
                }
                continue

            if not current_task:
                continue

            # 提取关键字段
            if "敌人等级：" in text:
                current_task["敌人等级"] = text.split("：")[-1]
            elif "任务时限：" in text:
                current_task["任务时限"] = text.split("：")[-1]
            elif text.startswith(("x", "X")):
                current_task["奖励货币"] = text.upper()
            elif text.isdigit() and len(text) in [2, 3]:
                current_task["奖励数值"] = text
            # 提取任务描述
            elif not any(k in text for k in self.keywords) and not text.startswith(
                ("x", "X")
            ):
                current_task["任务描述"] += text

        # 为所有任务匹配接受按钮
        for task in tasks + ([current_task] if current_task else []):
            task_y = task["y_start"]
            matched_btn = None
            min_y_diff = float("inf")

            for btn in accept_buttons:
                y_diff = abs(btn["y"] - task_y)
                if y_diff < min_y_diff:
                    min_y_diff = y_diff
                    matched_btn = btn

            if matched_btn:
                box = matched_btn["box"]
                task["接受按钮_box"] = box
                # 计算中心坐标
                center_x = box[0] + box[2] / 2
                center_y = box[1] + box[3] / 2
                task["接受按钮中心坐标"] = (
                    round(center_x, 1),
                    round(center_y, 1),
                )

        # 追加最后一个任务
        if current_task:
            tasks.append(current_task)

        return tasks

    def print_tasks(self, tasks: list) -> None:
        """
        打印任务信息

        Args:
            tasks: 任务列表
        """
        logger.info("=" * 90)
        logger.info("✅ OCR识别 → 任务结构化数据（含接受按钮中心坐标）")
        logger.info("=" * 90)

        for i, task in enumerate(tasks, 1):
            logger.info(f"\n【任务{i} | {task['任务名称']}】")
            logger.info(f"📝 任务描述：{task['任务描述']}")
            logger.info(f"⚔️  敌人等级：{task['敌人等级']}")
            logger.info(f"⏰ 任务时限：{task['任务时限']}")
            logger.info(f"🎁 任务奖励：{task['奖励货币']} + {task['奖励数值']}")
            logger.info(f"🖱️  接受按钮原始Box：{task['接受按钮_box']}")
            logger.info(f"🎯 接受按钮中心坐标：{task['接受按钮中心坐标']}")

        logger.info("\n" + "=" * 90)


# 示例用法
if __name__ == "__main__":
    # 示例OCR JSON数据
    ocr_json = {
        "all": [
            {"box": [57, 666, 61, 26], "score": 0.990639, "text": "奖励："},
            {"box": [57, 1088, 62, 25], "score": 0.995193, "text": "奖励："},
            {"box": [116, 836, 79, 32], "score": 0.996939, "text": "外来者"},
            {"box": [117, 413, 54, 34], "score": 0.983551, "text": "侠盗"},
            {"box": [117, 979, 133, 26], "score": 0.995897, "text": "不让他们逃了。"},
            {
                "box": [119, 530, 552, 23],
                "score": 0.967894,
                "text": "有一名从军中逃出去的弓箭手落草为寇，四处掠夺贵族的财物，",
            },
            {
                "box": [119, 952, 560, 20],
                "score": 0.983901,
                "text": "一支从别国潜入过来的极端组织，委托佣兵尽快抓到他们，绝对",
            },
            {"box": [119, 1048, 155, 27], "score": 0.996922, "text": "任务时限：9个月"},
            {
                "box": [120, 562, 473, 20],
                "score": 0.976211,
                "text": "还声称是劫富济贫，拉拢了不少同伙，必须将他抓住！",
            },
            {"box": [120, 629, 152, 23], "score": 0.997093, "text": "任务时限：9个月"},
            {"box": [129, 1165, 66, 27], "score": 0.885779, "text": "X236"},
            {"box": [131, 747, 63, 22], "score": 0.900541, "text": "x328"},
            {"box": [222, 1168, 48, 23], "score": 0.999531, "text": "240"},
            {"box": [223, 746, 47, 23], "score": 0.999426, "text": "400"},
            {"box": [224, 1145, 45, 18], "score": 0.190406, "text": "三"},
            {"box": [227, 727, 39, 10], "score": 0, "text": ""},
            {"box": [573, 682, 68, 41], "score": 0.98767, "text": "接受"},
            {"box": [574, 1105, 66, 38], "score": 0.988171, "text": "接受"},
            {"box": [585, 462, 116, 21], "score": 0.994831, "text": "敌人等级：85"},
            {"box": [585, 884, 116, 21], "score": 0.994882, "text": "敌人等级：65"},
        ],
        "best": None,
        "filtered": [],
    }

    # 创建任务提取器实例
    task_extractor = TaskExtractor()

    # 提取任务
    task_list = task_extractor.extract_tasks_from_ocr(ocr_json)

    # 打印结果
    task_extractor.print_tasks(task_list)
