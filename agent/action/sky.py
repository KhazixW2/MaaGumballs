import difflib
import json
import time
from pathlib import Path

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger

MAX_RETRY_ATTEMPTS = 3  # 定义最大重试次数

# 事件库 JSON 路径（相对项目根）
SKY_EVENTS_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "intelligence_data"
    / "sky_events.json"
)

# 时空裂痕边框颜色 → 阵营映射
# 青色 = 启示, 黄色 = 游荡, 红色 = 深渊, 蓝色 = 刃
RIFT_COLOR_TO_FACTION: dict[str, str] = {
    "青": "启示",
    "黄": "游荡",
    "红": "深渊",
    "蓝": "刃",
}


@AgentServer.custom_action("AutoSky")
class AutoSky(CustomAction):
    _current_round: int
    _encountered_unbeatable: bool  # 记录是否遇到打不过的敌人
    _troopLoss: bool  # 记录是否出现克隆体战损
    _target_round: int
    _clone_enabled: bool  # 记录克隆体是否启用
    _sky_events_index: dict  # name -> event，__init__ 时预加载

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

    # ------------------------------------------------------------------
    # 事件库：构造时预加载 + 检索
    # ------------------------------------------------------------------

    def _ensure_sky_events_loaded(self) -> dict:
        """加载 sky_events.json 并构建 name -> event 索引。

        首次在 ``__init__`` 调用，之后保持缓存。文件不存在时返回空字典。

        Returns:
            dict: 事件名 -> 事件原始数据。
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
            for ev in cat.get("events", []):
                name = ev.get("name")
                if name:
                    index[name] = ev
        self._sky_events_index = index
        logger.info(f"事件库预加载完成: {len(index)} 个事件")
        return self._sky_events_index

    def _find_event_by_title(self, title: str) -> dict | None:
        """根据 OCR 出的事件标题在事件库中查找。

        三档匹配:
          1. 精确匹配
          2. 子串匹配（OCR 漏字或夹塞字也能命中）
          3. 相似度匹配（SequenceMatcher，处理 OCR 错字）
        """
        if not title:
            return None
        index = self._ensure_sky_events_loaded()

        # 1. 精确匹配
        if title in index:
            return index[title]

        # 2. 子串匹配（OCR 文本可能在标题前/中/后夹塞字）
        for name, ev in index.items():
            if title in name or name in title:
                logger.info(f"事件标题子串匹配: OCR='{title}' → 库='{name}'")
                return ev

        # 3. 相似度匹配（兜底，处理 OCR 错字如 "垃圾烧炉" vs "垃圾焚烧炉"）
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

    def _handle_random_event(self, context: Context, img, title: str) -> bool:
        """处理非战斗类随机事件：OCR 标题 → 查库 → 点击推荐选项 → 等待完成。

        Args:
            context: MaaFramework 上下文。
            img: 当前截图（numpy ndarray）。

        Returns:
            bool: True 表示事件已完成并返回雷达界面；False 表示标题未识别/库中无此事件/超时。
        """

        selected = None
        if event:= self._find_event_by_title(title):
            selected = self._get_recommended_option(event,title)

        if not selected:
            logger.warning(f"事件 '{title}' 未在事件库中找到,跳过智能选择")
            return False

        option_name = selected["name"]
        # 去掉括号注释（如 "(需海怪船长/鱼人/...之一)"）再用于 OCR 匹配按钮
        ocr_target = option_name.split("(", 1)[0].strip()
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
        confirm_attempts = 0
        max_confirm_attempts = 5  # 防止误识别后无限点

        time.sleep(1)  # 初始等待，让点击效果生效

        while time.time() < deadline:
            if context.tasker.stopping:
                logger.info(f"检测到停止任务请求,事件 '{title}' 等待终止")
                return False

            current_img = context.tasker.controller.post_screencap().wait().get()

            # 1. 已返回雷达界面 → 事件完成
            if context.run_recognition(
                "AutoSky_CheckExplorationInfo", current_img
            ).hit:
                logger.info(f"事件 '{title}' 已完成,返回雷达界面")
                return True

            # 2. 检测到确认对话框 → 自动点击
            if confirm_attempts < max_confirm_attempts:
                confirm_reco = context.run_recognition(
                    "AutoSky_ClickOptionByName",
                    current_img,
                    pipeline_override={
                        "AutoSky_ClickOptionByName": {
                            "recognition": "OCR",
                            "expected": ["确定", "确认"],
                            "action": "DoNothing",
                            "post_delay": 0,
                            "timeout": 1000,
                        }
                    },
                )
                if confirm_reco and confirm_reco.hit:
                    confirm_text = confirm_reco.best_result.text
                    logger.info(
                        f"事件 '{title}' 出现确认按钮 '{confirm_text}',代为点击"
                    )
                    context.run_task(
                        "AutoSky_ClickOptionByName",
                        pipeline_override={
                            "AutoSky_ClickOptionByName": {
                                "recognition": "OCR",
                                "expected": ["确定", "确认"],
                            }
                        },
                    )
                    confirm_attempts += 1
                    time.sleep(1)
                    continue

            time.sleep(2)

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

        1. OCR 裂痕边框颜色(青/黄/红/蓝)
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
        color_char = next((c for c in ("青", "黄", "红", "蓝") if c in color), color)
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
        if not (result and result.nodes):
            logger.warning(f"攻击裂痕失败")

        # 切回默认主分队
        logger.info("切回默认主分队...")
        self.switch_main_fleet(context)

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

        logger.info("已成功进入天空探索雷达界面。")

        # 1.1 切换主分队为用户在 UI 中选择的分队（默认深渊）
        self.switch_main_fleet(context)

        # 1.2 进入克隆体界面, 默认关闭克隆体
        context.run_task("AutoSky_Enter_Clone")
        self._clone_enabled = False  # 进入克隆体界面说明克隆体被禁用

        # 2. 探索目标轮数, 这个是外层的while 用于控制探索轮次（进雷达界面扫一圈+自动探索=完整的一轮）
        while (
            not self._encountered_unbeatable
            and not self._troopLoss
            and self._current_round < self._target_round
        ):
            if context.tasker.stopping:
                logger.info("检测到停止任务请求, AutoSky 任务终止。")
                return CustomAction.RunResult(success=False)

            # 开始探索
            self._current_round += 1
            logger.info(f"开始第 {self._current_round}/ {self._target_round} 轮探索")

            # 2.1 获取当前目标数，确定本次手动探索的次数，默认尝试7次 为什么是7呢，因为ocr容易把7识别成门
            max_manual_attempts = 7
            if target_num_reco := context.run_recognition(
                "AutoSky_CheckTargetNum",
                context.tasker.controller.post_screencap().wait().get(),
            ):
                if target_num_reco.hit:
                    try:
                        parsed_num = int(target_num_reco.best_result.text)
                        max_manual_attempts = parsed_num + 1
                        logger.info(
                            f"识别到当前目标数: {parsed_num}，本轮手动探索最多尝试 {max_manual_attempts} 次。"
                        )
                    except ValueError:
                        logger.warning(
                            "未能解析目标数，本轮手动探索使用默认尝试次数 7。"
                        )
                else:
                    logger.warning("未能识别到目标数，本轮手动探索使用默认尝试次数 7。")
            else:
                logger.warning("未能识别到目标数，本轮手动探索使用默认尝试次数 7。")

            # 2.2 循环进行“手动目标探索”
            logger.info(f"开始本轮手动探索 ({max_manual_attempts} 次尝试)。")
            manual_attempts_done = 0
            while manual_attempts_done < max_manual_attempts:
                if context.tasker.stopping:
                    logger.info("检测到停止任务请求, 手动探索任务终止。")
                    return CustomAction.RunResult(success=False)

                context.run_task("AutoSky_ChangeTarget")  # 切换目标
                manual_attempts_done += 1

                # 检查是否为裂痕
                if context.run_recognition(
                    "AutoSky_RiftDetection",
                    context.tasker.controller.post_screencap().wait().get(),
                ).hit:
                    # if context.run_recognition(
                    #     "AutoSky_CombatEventDestory",
                    #     context.tasker.controller.post_screencap().wait().get(),
                    # ).hit:
                    #     logger.info("识别到裂痕可以直接摧毁，摧毁！！")
                    #     context.run_task("AutoSky_CombatEventDestory")
                    # else:
                        # 无法直接摧毁 → 识别颜色 → 切到对应阵营后攻击
                    self._handle_rift_by_color(context)
                        


                    logger.info(
                        f"当前目标为时空裂痕，继续切换 ({manual_attempts_done}/{max_manual_attempts} 次尝试)。"
                    )
                # 探索类事件处理
                elif context.run_recognition(
                        "AutoSky_ExploreRandomEvent",
                        context.tasker.controller.post_screencap().wait().get(),
                    ).hit:
                    # 非战斗事件处理：先点"调查"进入事件详情页（如果还没进），
                    # 再 OCR 事件标题查库 + 智能点选项。对战斗/神殿事件静默跳过。
                    reco = context.run_recognition(
                        "AutoSky_CheckRandomEvent",
                        context.tasker.controller.post_screencap().wait().get()
                    )
                    if not reco or not reco.hit:
                        logger.warning("未能 OCR 识别随机事件标题")
                        continue
                    context.run_task("AutoSky_ExploreRandomEvent")
                    time.sleep(1)  # 等待事件详情页加载
                    current_img = (
                        context.tasker.controller.post_screencap().wait().get()
                    )
                    self._handle_random_event(context, current_img, reco.best_result.text)
                
                # 战斗事件处理
                elif context.run_recognition(
                        "AutoSky_EventDetection",
                        context.tasker.controller.post_screencap().wait().get(),
                    ).hit:
                    # 处理战斗事件
                    logger.info(f"发现战斗目标~~")
                    context.run_task("AutoSky_EventDetection")  # 会自动完成战斗或探索

                    current_img = (
                        context.tasker.controller.post_screencap().wait().get()
                    )

                    # 遇到打不过的敌人跑路
                    if context.run_recognition("AutoSky_Lost", current_img).hit:
                        logger.warning("遇到打不过的敌人，本轮探索结束")
                        time.sleep(2)
                        context.run_task("BackText_500ms")
                        self._encountered_unbeatable = True
                        break

                    # 只有在克隆体启用时才检查克隆体阵亡
                    if self._clone_enabled:
                        if context.run_recognition(
                            "AutoSky_TroopLoss", current_img
                        ).hit:
                            logger.warning("识别到克隆体战损，本轮探索结束。")
                            time.sleep(2)
                            context.run_task("AutoSky_TroopLoss_Backtext")
                            self._troopLoss = True
                            break
                # 无法识别的类型
                else :
                    logger.error("无法识别的数据类型")


            # 2.3 自动探索
            logger.info("开始本轮的自动探索环节。")

            # --- 为提高稳定性，确保顺利离开雷达界面并完成自动探索，添加重试功能 ---
            hasLeftRadar = False
            auto_explore_successful = False

            for retry_count in range(MAX_RETRY_ATTEMPTS):
                if context.tasker.stopping:
                    logger.info(
                        f"检测到停止任务请求（自动探索重试 {retry_count+1} 中), AutoSky 任务终止。"
                    )
                    return CustomAction.RunResult(success=False)

                # 确保在雷达界面，如果不是，说明出现了异常情况
                if hasLeftRadar == False and context.run_recognition(
                    "AutoSky_CheckExplorationInfo",
                    context.tasker.controller.post_screencap().wait().get(),
                ):
                    logger.info(f"确认目前处于雷达界面")
                    context.run_task("AutoSky_Exit_Radar_Interface")
                    if context.run_recognition(
                        "AutoSky_CheckExplorationInfo",
                        context.tasker.controller.post_screencap().wait().get(),
                    ).hit:
                        logger.warning("未能成功离开雷达界面，重新尝试。")
                        time.sleep(2)
                        continue  # 继续下一次重试
                    else:
                        hasLeftRadar = True
                        time.sleep(1)
                else:
                    logger.warning(f"不在雷达界面，属于异常情况，自动退出")
                    return CustomAction.RunResult(success=False)

                # 2.4 开始自动探索
                sky_explore_start_result = context.run_task("AutoSky_SkyExplore_Start")
                if sky_explore_start_result.nodes:
                    logger.info("成功触发自动探索。")
                    auto_explore_successful = True
                    break
                else:
                    logger.warning("未能成功触发自动探索，重新尝试。")
                    time.sleep(2)  # 失败后等待一下

            if not auto_explore_successful:
                logger.error(
                    f"达到最大重试次数 ({MAX_RETRY_ATTEMPTS})，未能成功触发自动探索。AutoSky 任务终止。"
                )
                return CustomAction.RunResult(success=False)

            time.sleep(2)  # 给自动探索一些时间让其执行

            # 检查自动探索结果
            if not context.run_recognition(
                "AutoSky_SkyExplore_Confirm_Finish",
                context.tasker.controller.post_screencap().wait().get(),
            ).hit:
                logger.info("未成功消耗能量，可能没能量或者雷达满了，任务结束。")
                self._current_round = self._target_round
                break
            else:
                logger.info("自动探索成功，消耗了能量。")
                context.run_task("AutoSky_SkyExplore_Confirm_Finish")

        # 主循环结束后的最终处理
        result_message = ""
        success_status = False
        need_return_to_map = True

        if self._encountered_unbeatable:
            result_message = "AutoSky 任务因遇到打不过的敌人而终止"
        elif self._troopLoss:
            result_message = "AutoSky 任务因遇到克隆体战损而终止"
        elif self._current_round >= self._target_round:
            result_message = f"AutoSky 任务已成功完成全部 {self._target_round} 轮探索"
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
