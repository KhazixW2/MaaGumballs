import difflib
import json
import re
import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger
from utils.table_loader import get_table_path

MAX_RETRY_ATTEMPTS = 3  # 定义最大重试次数
BATTERY_PER_USE = 5      # AutoSky_Bag_UseBattery 单次调用使用的电池数(沿用 OCR '5个')
BATTERY_BATCH_SIZE = 25  # 每次"补能阶段"的最大批次数(25 电池 ≈ 125 能量)
MAX_ITERATIONS = 50      # 主循环硬性迭代上限(防止意外无限循环)
MAX_COMBAT_FAIL_COUNT = 3  # 连续战斗失败次数达到该值后判定打不过
MAX_SKY_LEVEL_STAGNANT_ROUNDS = 2  # 连续天空等级未变化次数达到该值后判定无进展

# 事件库 JSON 路径(用统一 helper,见 utils.table_loader)
SKY_EVENTS_FILE = get_table_path("sky_events.json")

# 时空裂痕边框颜色 → 阵营映射
# 青色 = 启示, 黄色 = 游荡, 赤色 = 深渊, 蓝色 = 刃
RIFT_COLOR_TO_FACTION: dict[str, str] = {
    "青": "启示",
    "黄": "游荡",
    "赤": "深渊",
    "蓝": "刃",
}


@AgentServer.custom_action("AutoSky")
class AutoSky(CustomAction):
    _current_round: int
    _encountered_unbeatable: bool  # 记录是否遇到打不过的敌人
    _troopLoss: bool  # 记录是否出现克隆体战损
    _target_round: int
    _clone_enabled: bool  # 记录克隆体是否启用
    _temple_enabled: bool  # 记录神殿是否启用(start 时由 pipeline 节点读取)
    _sky_events_index: dict  # name -> event，__init__ 时预加载
    _used_battery: int  # 累计已使用电池数
    _iteration: int  # 主循环当前迭代数
    _last_progress: bool  # 上一轮是否有进展(用于无进展检测)
    _combat_fail_count: int  # 连续命中 AutoSky_SkipDetection_Fail 的次数
    _last_sky_level: int | None  # 上一次识别到的天空探索等级
    _sky_level_stagnant_rounds: int  # 连续天空等级未变化次数
    _sky_level_stalled: bool  # 天空等级连续未变化,判定探索不再推进

    def __init__(self):
        super().__init__()
        self.resetParam()
        # 先置 None 防止 _ensure_sky_events_loaded 里的 is-not-None 检查触发 AttributeError
        self._sky_events_index = None
        # 启动时立即预加载事件库（避免第一次遇到事件时才加载导致的延迟）
        self._sky_events_index = self._ensure_sky_events_loaded()
        logger.debug("AutoSky 实例已创建并初始化默认参数。")

    def resetParam(self):
        """
        重置所有任务相关的参数到初始状态。
        """
        self._current_round = 0
        self._encountered_unbeatable = False
        self._troopLoss = False
        self._target_round = 5
        self._clone_enabled = True  # 默认启用克隆体检查
        self._temple_enabled = True  # 默认启用神殿(start 时会被 pipeline 覆盖)
        self._used_battery = 0  # 累计已用电池数
        self._iteration = 0  # 主循环迭代数
        self._last_progress = True  # 默认认为有进展(避免首次就退出)
        self._combat_fail_count = 0
        self._last_sky_level = None
        self._sky_level_stagnant_rounds = 0
        self._sky_level_stalled = False

    # ------------------------------------------------------------------
    # 事件库：构造时预加载 + 检索
    # ------------------------------------------------------------------

    def _ensure_sky_events_loaded(self) -> dict:
        """加载 sky_events.json 并构建 name -> event 索引。

        索引两种条目:
          - event name → event 自身(精确匹配)
          - category name → 该 category 的元信息字典
            (用于 OCR 检测到 category 标题时,返回第一个 sub-event 的处理)

        首次在 ``__init__`` 调用，之后保持缓存。文件不存在时返回空字典。

        Returns:
            dict: 名称 -> event 或 category 元信息
        """
        if self._sky_events_index is not None:
            return self._sky_events_index

        if not SKY_EVENTS_FILE.exists():
            logger.warning(f"事件库文件不存在: {SKY_EVENTS_FILE}")
            self._sky_events_index = {}
            return self._sky_events_index

        with open(SKY_EVENTS_FILE, encoding="utf-8") as f:
            data = json.load(f)

        index: dict = {}
        for cat in data.get("categories", []):
            cat_name = cat.get("name")
            events = cat.get("events", [])
            # 1. 索引每个 event 名字
            for ev in events:
                name = ev.get("name")
                if name:
                    index[name] = ev
            # 2. 索引 category 名字 → 存 category 引用
            #    让 _find_event_by_title 在 OCR 检测到 category 标题时
            #    能匹配上(返回第一个 sub-event 作默认处理)
            if cat_name and events:
                index[cat_name] = {
                    "__category__": True,
                    "events": events,
                }
        self._sky_events_index = index
        logger.info(f"事件库预加载完成: {len(index)} 个条目(含 category 别名)")
        return self._sky_events_index

    def _find_event_by_title(self, title: str) -> dict | None:
        """根据 OCR 出的事件标题在事件库中查找。

        四档匹配:
          1. 精确匹配 event 名字
          2. 精确匹配 category 名字(返回该 category 第一个 sub-event 作默认)
          3. 子串匹配(OCR 漏字或夹塞字)
          4. 相似度匹配(SequenceMatcher,处理 OCR 错字)
        """
        if not title:
            return None
        index = self._ensure_sky_events_loaded()

        # 1. 精确匹配 event 名
        if title in index:
            ev = index[title]
            if ev.get("__category__"):
                # 命中 category 别名 → 返回第一个 sub-event 作默认处理
                first_event = ev["events"][0]
                logger.info(
                    f"事件标题 category 别名匹配: OCR='{title}' → "
                    f"子事件 '{first_event.get('name')}'"
                )
                return first_event
            return ev

        # 3. 子串匹配(OCR 文本可能在标题前/中/后夹塞字)
        for name, ev in index.items():
            if title in name or name in title:
                if ev.get("__category__"):
                    first_event = ev["events"][0]
                    logger.info(
                        f"事件标题子串匹配(category): OCR='{title}' → 库='{name}' → "
                        f"子事件 '{first_event.get('name')}'"
                    )
                    return first_event
                logger.info(f"事件标题子串匹配: OCR='{title}' → 库='{name}'")
                return ev

        # 4. 相似度匹配(兜底,处理 OCR 错字如 "垃圾烧炉" vs "垃圾焚烧炉")
        best_match = None
        best_name = None
        best_ratio = 0.6  # 相似度阈值
        for name, ev in index.items():
            ratio = difflib.SequenceMatcher(None, title, name).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = ev
                best_name = name
        if best_match is not None:
            if best_match.get("__category__"):
                first_event = best_match["events"][0]
                logger.info(
                    f"事件标题相似度匹配(category): OCR='{title}' → 库='{best_name}' "
                    f"(ratio={best_ratio:.2f}) → 子事件 '{first_event.get('name')}'"
                )
                return first_event
            logger.info(
                f"事件标题相似度匹配: OCR='{title}' → 库='{best_name}' (ratio={best_ratio:.2f})"
            )
            return best_match

        return None

    @staticmethod
    def _get_recommended_option(event: dict, title: str) -> dict | None:
        """根据事件库标记取推荐选项。

        优先级:
          1. 分支结构（branches）: 用 selected_branch → 选该分支的 selected 选项
          2. 普通 options: 选 selected=true 的选项
        """
        # 1. 分支结构（如 分岔的洞窟）
        branches = event.get("branches", [])
        if branches:
            target_id = event.get("selected_branch") or "left"
            target_branch = next(
                (b for b in branches if b.get("branch_id") == target_id),
                None,
            )
            if target_branch:
                for opt in target_branch.get("options", []):
                    if opt.get("selected"):
                        return opt

        # 2. 普通 options
        for opt in event.get("options", []):
            if opt.get("selected"):
                return opt
        return None

    @staticmethod
    def _get_selected_option(event: dict) -> dict | None:
        """从事件记录中取 selected=true 的选项（事件库已预先标记推荐选项）。"""
        for opt in event.get("options", []):
            if opt.get("selected"):
                return opt
        return None

    @staticmethod
    def _normalize_option_name_for_ocr(option_name: str) -> str:
        """把事件库选项名清洗成游戏按钮上的短文本。"""
        ocr_target = option_name.strip()
        ocr_target = re.split(r"[（(【\[]", ocr_target, maxsplit=1)[0].strip()
        if ":" in ocr_target:
            ocr_target = ocr_target.split(":", 1)[1].strip()
        if "：" in ocr_target:
            ocr_target = ocr_target.split("：", 1)[1].strip()
        return ocr_target

    def _handle_unknown_wreckage_event(self, context: Context, title: str) -> bool:
        """处理未入库的残骸事件。

        外层 ``AutoSky_ExploreRandomEvent`` 已经点击过"调查"按钮:
          - 尸体类: 调查后新弹窗含"翻找"/"埋葬",需要再点翻找
          - 飞艇类: 调查后事件直接结束,无需二次操作

        通过 OCR 是否能找到"翻找"按钮来区分两类。
        """
        logger.info(
            f"事件 '{title}' 命中残骸兜底: 未在事件库中精确配置，尝试通用处理"
        )

        # 尸体类: 调查后再点翻找
        current_img = context.tasker.controller.post_screencap().wait().get()
        search_reco = context.run_recognition(
            "AutoSky_ClickOptionByName",
            current_img,
            pipeline_override={
                "AutoSky_ClickOptionByName": {
                    "recognition": "OCR",
                    "expected": ["翻找"],
                    "action": "DoNothing",
                    "post_delay": 0,
                    "timeout": 2000,
                }
            },
        )
        if search_reco and search_reco.hit:
            logger.info(f"事件 '{title}' 残骸兜底 → 点击 '翻找' (尸体类)")
            result = context.run_task(
                "AutoSky_ClickOptionByName",
                pipeline_override={
                    "AutoSky_ClickOptionByName": {
                        "recognition": "OCR",
                        "expected": ["翻找"],
                    }
                },
            )
            if result and result.nodes:
                return self._wait_for_event_completion(context, title)

        # 飞艇类 / 其他: 调查已点完,事件结束,等待回到雷达界面
        logger.info(
            f"事件 '{title}' 残骸兜底未发现翻找按钮,"
            f"按飞艇类/单步事件处理(已点过调查,等待完成)"
        )
        return self._wait_for_event_completion(context, title, timeout=15)

    def _handle_random_event(self, context: Context, img, title: str) -> bool:
        """处理非战斗类随机事件：OCR 标题 → 查库 → 点击推荐选项 → 等待完成。

        Args:
            context: MaaFramework 上下文。
            img: 当前截图（numpy ndarray）。

        Returns:
            bool: True 表示事件已完成并返回雷达界面；False 表示标题未识别/库中无此事件/超时。
        """

        selected = None
        event = self._find_event_by_title(title)
        if event:
            selected = self._get_recommended_option(event, title)
            if not selected:
                if "残骸" in title:
                    return self._handle_unknown_wreckage_event(context, title)
                # 事件在库中但没 selected 选项(占位事件/待补全)→ 静默跳过
                logger.info(f"事件 '{title}' 库中无 selected 选项(占位/未配置),跳过")
                return False

        if not selected:
            if "残骸" in title:
                return self._handle_unknown_wreckage_event(context, title)
            logger.warning(f"事件 '{title}' 未在事件库中找到,跳过智能选择并返回上一级UI")
            context.run_task("BackText_500ms")
            return False

        option_name = selected["name"]
        ocr_target = self._normalize_option_name_for_ocr(option_name)
        reason = selected.get("reason", "")
        logger.info(
            f"事件 '{title}' → 点击 '{ocr_target}'"
            + (f" (源: '{option_name}')" if ocr_target != option_name else "")
            + (f" (原因: {reason})" if reason else "")
        )

        result = context.run_task(
            "AutoSky_ClickOptionByName",
            pipeline_override={
                "AutoSky_ClickOptionByName": {
                    "recognition": "OCR",
                    "expected": [ocr_target],
                }
            },
        )
        if not (result and result.nodes):
            logger.warning(f"点击选项 '{ocr_target}' 失败")
            return False

        # 点击后等待事件完成（游戏可能进入战斗动画 / 奖励弹窗 / 确认对话框，
        # 最终应返回雷达界面）。中途如果出现"确定/确认"按钮则代为点击。
        return self._wait_for_event_completion(context, title)

    def _wait_for_event_completion(
        self,
        context: Context,
        title: str,
        timeout: int = 45,
    ) -> bool:
        """轮询直到事件结束（返回雷达界面），中途出现的确认对话框自动点掉。

        Args:
            context: MaaFramework 上下文。
            title: 事件标题（用于日志）。
            timeout: 最大等待秒数。

        Returns:
            bool: True 表示已返回雷达界面；False 表示超时。
        """
        deadline = time.time() + timeout
        battle_attempts = 0
        max_battle_attempts = 3  # 防止误识别后无限点

        time.sleep(1)  # 初始等待，让点击效果生效

        while time.time() < deadline:
            if context.tasker.stopping:
                logger.info(f"检测到停止任务请求,事件 '{title}' 等待终止")
                return False

            current_img = context.tasker.controller.post_screencap().wait().get()

            # 1. 检测到"进入战斗"按钮(如走私者营地 勒索后)
            #    点进入战斗 → 链 AutoSky_SkipDetection → 自动跳过战斗 → 回雷达
            if battle_attempts < max_battle_attempts:
                if context.run_recognition(
                    "AutoSky_RobberyBattleEntry",
                    current_img
                ).hit:
                    logger.info(
                        f"事件 '{title}' 出现'进入战斗'按钮,点击进入战斗"
                    )
                    result = context.run_task("AutoSky_RobberyBattleEntry")
                    self._handle_battle_result(result)
                    if self._encountered_unbeatable:
                        return True
                    battle_attempts += 1
                    continue

            # 2. 检测到确认对话框 → 自动点击
            if context.run_recognition("ConfirmButton", current_img).hit:
                context.run_task("ConfirmButton")
                continue

            # 3. 已返回雷达界面 → 事件完成
            if context.run_recognition(
                "AutoSky_CheckExplorationInfo", current_img
            ).hit:
                logger.info(f"事件 '{title}' 已完成,返回雷达界面")
                return True


        logger.warning(f"事件 '{title}' 等待完成超时 ({timeout}s)")
        return False

    def switch_main_fleet(self, context: Context) -> bool:
        """
        在雷达界面将主分队切换为用户在 UI 选项中选择的分队。

        该方法依赖 ``AutoSky_Switch_Fleet`` 任务链,后者会:
          1. 点击冈布奥图标打开分队列表
          2. 通过 OCR 识别用户选定的分队名(由主分队选项注入 ``expected``)
          3. 若未找到则向右滑动并重试
          4. 找到后点击"出战"确认

        Returns:
            bool: True 表示成功切换或当前已是目标分队;False 表示执行失败。
        """
        logger.info("开始切换主分队...")
        result = context.run_task("AutoSky_Switch_Fleet")
        if result.nodes:
            logger.info("主分队切换成功。")
            context.run_task("AutoSky_ReturnSkyMap")
            return True
        logger.warning("主分队切换失败,可能当前已是目标分队或识别失败,继续执行。")
        context.run_task("AutoSky_ReturnSkyMap")

        return False

    def _switch_fleet_to_faction(self, context: Context, faction_name: str) -> bool:
        """把主分队切换到指定阵营对应的默认舰队。

        Args:
            context: MaaFramework 上下文。
            faction_name: 阵营名(启示/游荡/深渊/刃),对应游戏内的默认舰队名。

        Returns:
            bool: True 表示切换成功。
        """
        logger.info(f"切换主分队到 {faction_name} 阵营...")
        result = context.run_task(
            "AutoSky_Switch_Fleet",
            pipeline_override={
                "AutoSky_ComfirmFleet": {
                    "expected": [faction_name],
                }
            },
        )
        if result and result.nodes:
            logger.info(f"主分队已切换到 {faction_name}")
            context.run_task("AutoSky_ReturnSkyMap")
            return True
        logger.warning(f"主分队切换到 {faction_name} 失败,继续执行。")
        context.run_task("AutoSky_ReturnSkyMap")
        return False

    def _handle_rift_by_color(self, context: Context) -> None:
        """时空裂痕无法直接摧毁时的处理:

        1. OCR 裂痕边框颜色(青/黄/赤/蓝)
        2. 颜色 → 阵营 映射(RIFT_COLOR_TO_FACTION)
        3. 切换主分队到对应阵营
        4. 攻击裂痕
        5. 切回默认主分队
        """
        img = context.tasker.controller.post_screencap().wait().get()
        color_reco = context.run_recognition("AutoSky_RiftColor", img)
        if not color_reco or not color_reco.hit:
            logger.warning("无法 OCR 识别裂痕颜色,跳过攻击")
            return

        color = color_reco.best_result.text
        # OCR 可能返回 "时空裂痕·黄" 等带前缀的字符串,提取纯色字
        color_char = next((c for c in ("青", "黄", "赤", "蓝") if c in color), color)
        target_faction = RIFT_COLOR_TO_FACTION.get(color_char)
        if not target_faction:
            logger.warning(f"未识别的裂痕颜色 '{color_char}' (源文本='{color}'),跳过攻击")
            return

        logger.info(
            f"裂痕颜色={color} → 目标阵营={target_faction},切换主分队..."
        )
        if not self._switch_fleet_to_faction(context, target_faction):
            logger.warning(f"切换主分队到 {target_faction} 失败,放弃本次裂痕")
            return

        # 攻击裂痕(点击袭击按钮)
        logger.info(f"用 {target_faction} 阵营攻击裂痕")
        result = context.run_task("AutoSky_CombatEventDetection")
        self._handle_battle_result(result)
        if not (result and result.nodes):
            logger.warning(f"攻击裂痕失败")

        # 切回默认主分队
        logger.info("切回默认主分队...")
        self.switch_main_fleet(context)

    # ------------------------------------------------------------------
    # 主循环 helper: 读配置 / 自动探索 / 手动探索 / 使用能量包
    # ------------------------------------------------------------------

    def _read_battery_config(self, context: Context) -> tuple[int, bool]:
        """读取用户在 UI 中选择的能量包配置。

        通过 ``context.get_node_data("AutoSky_BagConfig")`` 读取
        pipeline_override 注入的 ``recognition.param.expected`` 第一个元素
        (字符串数字,parse 为 int)。

        Returns:
            (target_count, use_battery)
            - target_count: 用户设定的电池数上限;0 表示不使用
            - use_battery: target_count > 0 的便捷布尔
        """
        node = context.get_node_data("AutoSky_BagConfig")
        target = 0
        if node:
            expected = (
                node.get("recognition", {})
                .get("param", {})
                .get("expected", ["0"])
            )
            if expected:
                try:
                    target = int(expected[0])
                except (TypeError, ValueError):
                    target = 0
        return target, target > 0


    @staticmethod
    def _node_enabled(context: Context, node_name: str) -> bool:
        """读取 pipeline 节点是否启用，兼容 enable / enabled 两种字段。"""
        node = context.get_node_data(node_name)
        if not node:
            return True
        return bool(node.get("enable", node.get("enabled", True)))

    @staticmethod
    def _task_result_node_hit(node) -> bool:
        if getattr(node, "completed", False):
            return True

        recognition = getattr(node, "recognition", None)
        return bool(recognition and getattr(recognition, "hit", False))

    def _task_result_has_node(self, result, node_names: set[str]) -> bool:
        if not result or not result.nodes:
            return False
        return any(
            getattr(node, "name", None) in node_names
            and self._task_result_node_hit(node)
            for node in result.nodes
        )

    def _handle_battle_result(self, result) -> bool:
        """根据跳过战斗后的胜负节点更新连续失败计数。

        Returns:
            bool: True 表示本次任务结果里已经识别到战斗胜/负结算节点。
        """
        if self._task_result_has_node(result, {"AutoSky_SkipDetection_Win"}):
            if self._combat_fail_count > 0:
                logger.info("战斗胜利，连续失败计数清零")
            self._combat_fail_count = 0
            return True

        if self._task_result_has_node(result, {"AutoSky_SkipDetection_Fail"}):
            self._combat_fail_count += 1
            logger.warning(
                f"战斗失败，连续失败 {self._combat_fail_count}/{MAX_COMBAT_FAIL_COUNT}"
            )
            if self._combat_fail_count >= MAX_COMBAT_FAIL_COUNT:
                logger.error(
                    f"连续 {MAX_COMBAT_FAIL_COUNT} 次战斗失败，判定为打不过敌人，AutoSky 将终止"
                )
                self._encountered_unbeatable = True
            return True

        return False

    @staticmethod
    def _first_int_from_text(raw_text: str | None) -> int | None:
        match = re.search(r"\d+", raw_text or "")
        return int(match.group(0)) if match else None

    @staticmethod
    def _recognition_best_text(context: Context, node_name: str) -> str | None:
        img = context.tasker.controller.post_screencap().wait().get()
        reco = context.run_recognition(node_name, img)
        if not (reco and reco.hit and reco.best_result):
            return None
        return reco.best_result.text

    def _read_sky_level(self, context: Context) -> int | None:
        """打开探索信息并读取天空探索等级。"""
        opened = context.run_task("AutoSky_CheckSkyLevel_Click")
        if not self._task_result_has_node(opened, {"AutoSky_CheckSkyLevel_Click"}):
            logger.warning("打开探索信息失败，跳过天空等级检测")
            return None

        try:
            raw_text = self._recognition_best_text(context, "AutoSky_CheckSkyLevel_Check")
            sky_level = self._first_int_from_text(raw_text)
            if sky_level is None:
                logger.warning(f"未能识别天空探索等级(原始='{raw_text}')")
                return None

            logger.info(f"识别到天空探索等级: {sky_level} (原始='{raw_text}')")
            return sky_level
        finally:
            context.run_task("BackText_500ms")

    def _update_sky_level_stagnation(self, context: Context) -> bool:
        """更新天空等级停滞计数；连续不变达到阈值时返回 True。"""
        sky_level = self._read_sky_level(context)
        if sky_level is None:
            return False

        if self._last_sky_level is None:
            self._last_sky_level = sky_level
            logger.info(f"记录天空探索等级基线: {sky_level}")
            return False

        if sky_level != self._last_sky_level:
            logger.info(
                f"天空探索等级变化: {self._last_sky_level} → {sky_level}，"
                "连续未变化计数清零"
            )
            self._last_sky_level = sky_level
            self._sky_level_stagnant_rounds = 0
            return False

        self._sky_level_stagnant_rounds += 1
        logger.warning(
            f"天空探索等级连续 {self._sky_level_stagnant_rounds}/"
            f"{MAX_SKY_LEVEL_STAGNANT_ROUNDS} 轮未变化(当前 {sky_level})"
        )
        self._sky_level_stalled = (
            self._sky_level_stagnant_rounds >= MAX_SKY_LEVEL_STAGNANT_ROUNDS
        )
        if self._sky_level_stalled:
            self._last_progress = False
            logger.info("连续两轮天空探索等级未变化，判定当前已探索不动")
        return self._sky_level_stalled

    def _is_radar_empty(self, context: Context) -> bool:
        """检查雷达上是否已无可探索节点(右下角 00/23 → 0 命中)。

        Returns:
            bool: True 表示雷达已无可探索节点。
        """
        img = context.tasker.controller.post_screencap().wait().get()
        return context.run_recognition("AutoSky_CheckNodeCountZero", img).hit

    def _is_energy_zero(self, context: Context) -> bool:
        """检查能量是否为 0(右上角 0/31 → "0/" 前缀命中)。

        Returns:
            bool: True 表示能量为 0。
        """
        img = context.tasker.controller.post_screencap().wait().get()
        return context.run_recognition("AutoSky_CheckEnergyZero", img).hit

    @staticmethod
    def _parse_target_count(raw_text: str) -> int | None:
        """从 OCR 文本里解析右下角目标数。

        OCR 常见结果有 ``05/18``、``：05/18``、``05 / 18``。这里取斜杠
        左侧数字作为当前可切换目标数；如果没有斜杠，则退化为取第一个数字。
        """
        if not raw_text:
            return None

        fraction_match = re.search(r"(\d+)\s*/\s*(\d+)", raw_text)
        if fraction_match:
            current_text = fraction_match.group(1)
            current = int(current_text)
            total = int(fraction_match.group(2))
            if total > 0 and current > total:
                for start in range(1, len(current_text)):
                    candidate = int(current_text[start:])
                    if candidate <= total:
                        return candidate
                return None
            return current

        number_match = re.search(r"\d+", raw_text)
        if number_match:
            return int(number_match.group(0))

        return None

    def _try_auto_explore(self, context: Context) -> bool:
        """尝试触发一次自动探索,直到无法继续自动探索时返回雷达界面(消耗能量)。

        流程:确认在雷达→离开雷达→触发自动探索→等待并确认消耗→**显式回到雷达**。

        关键:无论自动探索成功或失败,return 前都要 ``_back_to_radar()``,
        否则下一轮可能因为 UI 不在雷达而失败。

        Args:
            context: MaaFramework 上下文。

        Returns:
            bool: True 表示成功消耗了能量;False 表示无法触达消耗
            (能量耗尽 / 雷达满 / UI 异常 / 重试用尽)。
        """
        logger.info("尝试自动探索...")

        auto_explore_successful = False

        for retry_count in range(MAX_RETRY_ATTEMPTS):
            if context.tasker.stopping:
                return False

            # 1. 离开雷达界面,如果在雷达界面的话
            if context.run_recognition("AutoSky_CheckExplorationInfo",
                context.tasker.controller.post_screencap().wait().get()).hit:
                context.run_task("AutoSky_CheckExplorationInfo")
                context.run_task("AutoSky_Exit_Radar_Interface")

            # 2. 触发自动探索
            sky_explore_start_result = context.run_task("AutoSky_SkyExplore_Start")
            if not sky_explore_start_result.nodes:
                logger.warning(
                    f"未能触发自动探索,重试 ({retry_count+1}/{MAX_RETRY_ATTEMPTS})"
                )
                time.sleep(2)
                continue
            auto_explore_successful = True
            break

        if not auto_explore_successful:
            logger.error(f"达到最大重试次数,自动探索失败")
            self._back_to_radar(context)
            return False

        # 3. 等待并确认消耗
        time.sleep(2)
        if not context.run_recognition(
            "AutoSky_SkyExplore_Confirm_Finish",
            context.tasker.controller.post_screencap().wait().get(),
        ).hit:
            # 未成功消耗能量(可能没能量/雷达满)→ 显式回雷达后让外层循环接手
            logger.info("未成功消耗能量,尝试返回雷达界面")
            context.run_task("AutoSky_Enter_Radar_Interface")
            return False

        logger.info("自动探索成功,消耗了能量")
        context.run_task("AutoSky_SkyExplore_Confirm_Finish")
        return True

    def _do_manual_exploration(self, context: Context) -> bool:
        """在雷达界面手动扫描可见目标并处理各类事件。

        处理的事件类型:时空裂痕(切阵营攻击)、探索类事件(查库点选项)、
        交谈类事件(跳过)、战斗事件(进战斗/跳过/检测战损)。

        Args:
            context: MaaFramework 上下文。

        Returns:
            bool: True 表示本轮至少处理过一个目标;False 表示无可处理目标
            (雷达空 或 全部事件被跳过)。
        """
        logger.info("开始手动探索...")

        # 0. 快速检查:雷达上是否还有可探索节点(避免节点为 0 时白跑 7 次 ChangeTarget)
        if self._is_radar_empty(context):
            logger.info("雷达上已无可探索节点(00/23),跳过手动扫描")
            return False

        # 1. 获取目标数
        max_manual_attempts = 7  # OCR 容易把 7 识别成门,留余量
        target_num_reco = context.run_recognition(
            "AutoSky_CheckTargetNum",
            context.tasker.controller.post_screencap().wait().get(),
        )
        if target_num_reco and target_num_reco.hit:
            raw_text = target_num_reco.best_result.text
            parsed_num = self._parse_target_count(raw_text)
            if parsed_num is not None:
                max_manual_attempts = parsed_num + 1
                logger.info(
                    f"识别到当前目标数: {parsed_num} (原始='{raw_text}'),"
                    f"本轮手动探索最多尝试 {max_manual_attempts} 次。"
                )
            else:
                logger.warning(
                    f"未能解析目标数(原始='{raw_text}'),使用默认 7。"
                )
        else:
            logger.warning("未能识别目标数,使用默认 7。")

        # 2. 循环切换目标并处理
        processed_any = False
        manual_attempts_done = 0
        # 卡住检测: 连续 2 次同一目标说明按钮无反应(条件不满足/RepeatTargeted),跳过
        last_event_title = ""
        consecutive_same_title = 0
        MAX_SAME_TITLE = 2  # 连续 2 次同一目标就跳过
        logger.info(f"开始本轮手动探索 ({max_manual_attempts} 次尝试)")
        while manual_attempts_done < max_manual_attempts:
            if context.tasker.stopping:
                return processed_any

            context.run_task("AutoSky_ChangeTarget")
            manual_attempts_done += 1
            current_img = context.tasker.controller.post_screencap().wait().get()

            # 2.1 时空裂痕(切阵营攻击)
            if context.run_recognition(
                "AutoSky_RiftDetection", current_img
            ).hit:
                self._handle_rift_by_color(context)
                processed_any = True
                # 重置卡住计数(已成功处理)
                last_event_title = ""
                consecutive_same_title = 0
                logger.info(
                    f"当前目标为时空裂痕,继续切换 ({manual_attempts_done}/{max_manual_attempts})"
                )
                continue

            # 2.2 探索类事件(查库点选项)
            if context.run_recognition(
                "AutoSky_ExploreRandomEvent", current_img
            ).hit:
                reco = context.run_recognition(
                    "AutoSky_CheckRandomEvent", current_img
                )
                if not reco or not reco.hit:
                    logger.warning("未能 OCR 识别随机事件标题")
                    continue
                current_title = reco.best_result.text

                # 卡住检测: 连续同一目标多次说明按钮无反应(300层条件等)
                if current_title == last_event_title:
                    consecutive_same_title += 1
                else:
                    consecutive_same_title = 1
                    last_event_title = current_title

                if consecutive_same_title >= MAX_SAME_TITLE:
                    logger.warning(
                        f"连续 {consecutive_same_title} 次目标 '{current_title}' 未变化,"
                        f"可能条件不满足(层数/机器人限制等),跳过此目标"
                    )
                    # 不 _handle_random_event,直接下一轮让 ChangeTarget 切下一个
                    # 但因为 ChangeTarget 也没切走(雷达可能只剩这节点),
                    # _do_manual_exploration 返回 False → main loop 退出
                    processed_any = False
                    break

                context.run_task("AutoSky_ExploreRandomEvent")
                time.sleep(1)
                current_img = context.tasker.controller.post_screencap().wait().get()
                self._handle_random_event(context, current_img, current_title)
                processed_any = True
                continue

            # 2.3 交谈类事件(暂不处理,跳过)
            if context.run_recognition(
                "AutoSky_TalkEvent", current_img
            ).hit:
                logger.info("检测到交谈类事件,暂不处理,跳过")
                continue

            # 2.4 神殿解除封印是非战斗事件,不能进入克隆体战损检测链路
            # 神殿禁用时(start 时已缓存到 _temple_enabled)整段跳过,
            # 避免每轮无谓的 OCR 调用;启用时再识别+处理
            if self._temple_enabled:
                temple_reco = context.run_recognition(
                    "AutoSky_ActivateTemple", current_img
                )
                if temple_reco and temple_reco.hit:
                    logger.info("检测到神殿解除封印,作为非战斗事件处理")
                    context.run_task("AutoSky_ActivateTemple")
                    processed_any = True
                    last_event_title = ""
                    consecutive_same_title = 0
                    continue

            # 2.5 可摧毁事件(炮轰，不进入战斗)
            if context.run_recognition(
                "AutoSky_CombatEventDestory", current_img
            ).hit:
                logger.info("检测到可摧毁事件，执行摧毁")
                context.run_task("AutoSky_CombatEventDestory")
                processed_any = True
                last_event_title = ""
                consecutive_same_title = 0
                continue

            # 2.6 袭击战斗事件：只有这里进入克隆体战损检测
            if context.run_recognition(
                "AutoSky_CombatEventDetection", current_img
            ).hit:
                logger.info("发现战斗目标~~")
                result = context.run_task("AutoSky_EventDetection")
                self._handle_battle_result(result)
                processed_any = True
                if self._encountered_unbeatable:
                    return True

                current_img = context.tasker.controller.post_screencap().wait().get()

                continue

            # 2.7 普通调查/探索按钮(非事件库标题类)
            if context.run_recognition(
                "AutoSky_ExploreEventDetection", current_img
            ).hit:
                logger.info("检测到调查/探索类事件，执行点击")
                context.run_task("AutoSky_ExploreEventDetection")
                processed_any = True
                last_event_title = ""
                consecutive_same_title = 0
                continue

            # 2.8 无法识别:Debug OCR dump
            debug_img = context.tasker.controller.post_screencap().wait().get()
            debug_reco = context.run_recognition(
                "AutoSky_EventDetection",
                debug_img,
                pipeline_override={
                    "AutoSky_EventDetection": {
                        "action": "DoNothing",
                        "post_delay": 0,
                        "timeout": 1000,
                    }
                },
            )
            if debug_reco and debug_reco.all_results:
                texts = [r.text for r in debug_reco.all_results[:8]]
                logger.error(f"无法识别的数据类型,屏幕 OCR 文本: {texts}")
            else:
                logger.error("无法识别的数据类型,且 OCR 无结果")

        return processed_any

    def _use_battery_pack(
        self,
        context: Context,
        max_per_batch: int = BATTERY_BATCH_SIZE,
    ) -> int:
        """在雷达界面使用能量包,本次最多 ``max_per_batch`` 个电池。

        每次 ``context.run_task("AutoSky_Bag_UseBattery")`` 调用使用 5 个电池
        (沿用 OCR "5个" 的语义),本次最多连续调用 ``max_per_batch // 5`` 次。

        用完后会**主动关闭可能残留的弹框**(背包/补充能量对话框),确保外层
        主循环下一次进入 ``_try_auto_explore`` / ``_do_manual_exploration`` 时
        处于干净雷达界面,避免 ``AutoSky_Exit_Radar_Interface`` 因弹框遮挡
        TemplateMatch 失败导致任务立即结束。

        Args:
            context: MaaFramework 上下文。
            max_per_batch: 本次最多使用的电池数(默认 ``BATTERY_BATCH_SIZE``=25)。

        Returns:
            int: 实际使用的电池数(失败时可能小于 ``max_per_batch``;0 表示完全失败)。
        """
        logger.info(f"开始使用能量包,本次上限 {max_per_batch} 个")
        used = 0
        max_clicks = max_per_batch // BATTERY_PER_USE
        for _ in range(max_clicks):
            if context.tasker.stopping:
                break
            result = context.run_task("AutoSky_Bag_UseBattery")
            if not result or not result.nodes:
                logger.warning(f"单次使用能量包失败,已在 {used} 个处停止")
                break
            used += BATTERY_PER_USE

        if used > 0:
            logger.info(f"本批使用了 {used} 个能量包")

        # 关闭残留弹框(最多 2 次返回,把可能的"补充能量" + "天空物资"两层关掉)
        # 不强制成功:如果 BackText 在不同 UI 层有副作用,这里是兜底
        for _ in range(2):
            if context.tasker.stopping:
                break
            current_img = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition(
                "AutoSky_CheckExplorationInfo", current_img
            ).hit:
                break
            context.run_task("BackText_500ms")
            time.sleep(1)

        return used

    def _back_to_radar(self, context: Context) -> bool:
        """确保当前 UI 已经回到雷达界面。每步只做一次导航,不盲目 BackText。

        状态识别 + 一步导航(避免跳出天空流程):

          1. **雷达**:OCR ``探索信息`` 命中 → 直接返回
          2. **SkyExplore 页**(显示"自动探索"按钮):
             ``AutoSky_Enter_Radar_Interface`` (template + click,
             next 链自动 OCR ``探索信息`` 验证)
          3. **结算页 / 战术大厅**(能看到飞艇图标):
             ``AutoSky_SkyExplore`` (template + click,
             next 链自动跳到 SkyExplore 再到雷达)
          4. **其他**(例如已经跳出到大地图):
             不再做导航 — 让调用方终止任务,避免越按 BackText 越退越远。

        Args:
            context: MaaFramework 上下文。

        Returns:
            bool: True 表示已确认在雷达界面;False 表示已跳出天空流程,应中止。
        """
        # 探测当前状态
        current_img = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition(
            "AutoSky_CheckExplorationInfo", current_img
        ).hit:
            return True  # 已在雷达,直接返回

        logger.info("不在雷达,识别当前位置以做精确回退...")

        # 状态 3: 在 SkyExplore 附近(看到飞艇图标)→ 进入 SkyExplore 后再进雷达
        if context.run_recognition("AutoSky_SkyExplore", current_img).hit:
            logger.info("检测到 SkyExplore 按钮,从当前页导航到 SkyExplore 页...")
            context.run_task("AutoSky_SkyExplore")
            time.sleep(1)
            current_img = context.tasker.controller.post_screencap().wait().get()
            # SkyExplore 的 next 链会自动跳到 AutoSky_Enter_Radar_Interface
            return context.run_recognition(
                "AutoSky_CheckExplorationInfo", current_img
            ).hit

        # 状态 2: 已在 SkyExplore 页(看到"自动探索"按钮/雷达能量等)
        # 但 template 没找到 SkyExplore(可能我们实际上在结算页)
        # 尝试 Enter_Radar(如果在 SkyExplore 会命中,在结算页则不会)
        if context.run_recognition(
            "AutoSky_Enter_Radar_Interface", current_img
        ).hit:
            logger.info("检测到雷达入口按钮,直接进入雷达...")
            context.run_task("AutoSky_Enter_Radar_Interface")
            time.sleep(1)
            current_img = context.tasker.controller.post_screencap().wait().get()
            return context.run_recognition(
                "AutoSky_CheckExplorationInfo", current_img
            ).hit

        # 其他:跳过了战术大厅、大地图、或者其他无法识别的状态
        # 不再做 BackText(避免越按越远跳出天空流程)
        logger.warning(
            "无法识别当前位置以回到雷达"
            "(可能已跳出天空流程到大地图或异常页面),中止导航"
        )
        return False

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        # 0. 重置参数
        self.resetParam()
        logger.info(f"AutoSky 自定义动作开始执行，目标探索轮次: {self._target_round}。")

        # 1. 进入天空界面
        logger.info("尝试进入天空探索雷达界面...")
        context.run_task("AutoSky_Start")

        if not context.run_recognition(
            "AutoSky_CheckExplorationInfo",
            context.tasker.controller.post_screencap().wait().get(),
        ).hit:
            logger.error("任务开始后未能识别到探索信息界面,AutoSky 任务终止。")
            return CustomAction.RunResult(success=False)


        # 1.1 切换主分队为用户在 UI 中选择的分队（默认深渊）
        self.switch_main_fleet(context)

        # 1.2 根据用户选项设置克隆体。不开启时沿用原行为:关闭克隆体。
        self._clone_enabled = self._node_enabled(context, "AutoSky_CloneConfig")
        # 1.2.1 缓存神殿启用状态,避免每轮 OCR 探测(神殿禁用时直接跳过整个 2.4 分支)
        self._temple_enabled = self._node_enabled(context, "AutoSky_ActivateTemple")
        if self._clone_enabled:
            logger.info("已启用克隆体，尝试开启克隆体并启用战损检测")
            context.run_task("AutoSky_Enable_Clone")
        else:
            logger.info("未启用克隆体，尝试关闭克隆体并跳过战损检测")
            context.run_task("AutoSky_Disable_Clone")

        # 1.3 读能量包配置(目标数 + 是否启用)
        target_battery, use_battery = self._read_battery_config(context)
        if use_battery:
            logger.info(
                f"启用能量包补充,目标 {target_battery} 个(每批 ≤ {BATTERY_BATCH_SIZE})"
            )
        else:
            logger.info("未启用能量包,尽量探索直到无进展为止")

        # 2. 主循环: 能量包计数驱动
        # 每轮: 先尝试自动探索 → 失败时手动处理 → 用电池(若启用且未满)
        # 关键: 用完电池不立即退出,等下一轮 _try_auto_explore 用掉新能量
        while True:
            # --- 终止条件 ---
            if self._encountered_unbeatable or self._troopLoss:
                break
            if context.tasker.stopping:
                logger.info("检测到停止任务请求,AutoSky 任务终止")
                return CustomAction.RunResult(success=False)
            self._iteration += 1
            self._current_round = self._iteration  # 保留供日志/上报
            if self._iteration > MAX_ITERATIONS:
                logger.error(f"达到最大迭代次数 {MAX_ITERATIONS},任务强制终止")
                break
            if not self._last_progress:
                logger.info("连续无进展,任务自然结束")
                break

            self._last_progress = False  # 本轮有动作再置 True
            logger.info(f"开始第 {self._iteration} 轮探索")

            # --- 1) 自动探索(消耗能量,优先)---
            if self._try_auto_explore(context):
                self._last_progress = True
                # auto-explore 不保证回雷达 → 不在此处检测等级,留到手动探索分支
            else:
                # _try_auto_explore 已经尝试回雷达;
                # 若仍不在雷达(返回 False 且不在雷达),跳过本轮手动探索
                radar_img = context.tasker.controller.post_screencap().wait().get()
                in_radar_now = context.run_recognition(
                    "AutoSky_CheckExplorationInfo", radar_img
                ).hit
                if in_radar_now:
                    # 等级检测必须在雷达界面 → 放在手动探索之前
                    # 此点已通过 in_radar_now 验证,而 _try_auto_explore
                    # 完成后不一定回到雷达界面(用户反馈)
                    if self._update_sky_level_stagnation(context):
                        break
                    # --- 检查雷达是否还有可探索节点 ---
                    # 雷达空(0/0)说明本次探索已无目标,直接用电池补充
                    if self._is_radar_empty(context):
                        # 雷达空 + 自动失败 = 没能量 + 没目标
                        if use_battery and self._used_battery < target_battery:
                            # 还有能量包预算 → 用电池补充
                            remaining = target_battery - self._used_battery
                            batch = min(BATTERY_BATCH_SIZE, remaining)
                            used_now = self._use_battery_pack(
                                context, max_per_batch=batch
                            )
                            if used_now > 0:
                                self._used_battery += used_now
                                self._last_progress = True
                                logger.info(
                                    f"雷达无目标,使用 {used_now} 个能量包,"
                                    f"累计 {self._used_battery}/{target_battery}"
                                )
                            # 下一轮 _try_auto_explore 会用上新能量
                        else:
                            # 电池用完或未启用 → 任务完成
                            logger.info(
                                "雷达无目标且无可用能量包,任务完成"
                            )
                            self._last_progress = False
                    else:
                        # 雷达还有节点 → 手动探索
                        # --- 2) 自动失败但雷达有目标 → 手动探索 ---
                        processed_any = self._do_manual_exploration(context)
                        if processed_any:
                            self._last_progress = True

                        # --- 3) 补能量包(若启用且未用满)---
                        if use_battery and self._used_battery < target_battery:
                            remaining = target_battery - self._used_battery
                            batch = min(BATTERY_BATCH_SIZE, remaining)  # 末批 < 25 时一次性用完
                            used_now = self._use_battery_pack(
                                context, max_per_batch=batch
                            )
                            if used_now > 0:
                                self._used_battery += used_now
                                self._last_progress = True
                                logger.info(
                                    f"本轮使用 {used_now} 个能量包,"
                                    f"累计 {self._used_battery}/{target_battery}"
                                )
                else:
                    # UI 不在雷达(可能跳出天空流程到大地图)→
                    # 不进入手动探索(否则会乱点乱识别),
                    # 置 _last_progress=False 让下一轮"连续无进展"检测触发
                    logger.warning(
                        "自动探索后 UI 不在雷达界面,跳过本轮手动,"
                        "下一轮将因'连续无进展'退出任务"
                    )
                    self._last_progress = False

        # 主循环结束后的最终处理
        result_message = ""
        success_status = False
        need_return_to_map = True

        if self._encountered_unbeatable:
            result_message = "AutoSky 任务因遇到打不过的敌人而终止"
        elif self._troopLoss:
            result_message = "AutoSky 任务因遇到克隆体战损而终止"
        elif self._iteration > MAX_ITERATIONS:
            result_message = (
                f"AutoSky 任务达到最大迭代次数 {MAX_ITERATIONS},强制终止"
            )
        elif self._sky_level_stalled:
            result_message = (
                f"AutoSky 任务已连续 {MAX_SKY_LEVEL_STAGNANT_ROUNDS} 轮天空探索等级未变化,"
                "判定当前已无可推进目标"
            )
            success_status = True
        elif use_battery and self._used_battery >= target_battery:
            result_message = (
                f"AutoSky 任务已完成 {self._used_battery} 个能量包的使用,任务结束"
            )
            success_status = True
        elif not self._last_progress:
            result_message = "AutoSky 任务已完成全部天空探索(无可进展目标)"
            success_status = True
        else:
            result_message = "AutoSky 任务意外退出"
            need_return_to_map = False
            logger.error(result_message)
            return CustomAction.RunResult(success=False)

        # 记录日志并返回大地图
        logger.info(f"{result_message}。自动回到大地图")
        if need_return_to_map:
            context.run_task("AutoSky_ReturnBigMap")

        return CustomAction.RunResult(success=success_status)
