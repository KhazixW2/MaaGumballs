import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger

MAX_RETRY_ATTEMPTS = 3  # 定义最大重试次数


@AgentServer.custom_action("AutoSky")
class AutoSky(CustomAction):
    _current_round: int
    _encountered_unbeatable: bool  # 记录是否遇到打不过的敌人
    _troopLoss: bool  # 记录是否出现克隆体战损
    _target_round: int
    _clone_enabled: bool  # 记录克隆体是否启用

    def __init__(self):
        super().__init__()
        self.resetParam()
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
        ):
            logger.error("任务开始后未能识别到探索信息界面,AutoSky 任务终止。")
            return CustomAction.RunResult(success=False)

        logger.info("已成功进入天空探索雷达界面。")

        # 1.1 进入克隆体界面, 默认关闭克隆体
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
                try:
                    parsed_num = int(target_num_reco.best_result.text)
                    max_manual_attempts = parsed_num + 1
                    logger.info(
                        f"识别到当前目标数: {parsed_num}，本轮手动探索最多尝试 {max_manual_attempts} 次。"
                    )
                except ValueError:
                    logger.warning("未能解析目标数，本轮手动探索使用默认尝试次数 7。")
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

                # 检查是否为裂隙
                if context.run_recognition(
                    "AutoSky_RiftDetection",
                    context.tasker.controller.post_screencap().wait().get(),
                ):
                    logger.info(
                        f"当前目标为时空裂痕，继续切换 ({manual_attempts_done}/{max_manual_attempts} 次尝试)。"
                    )
                else:
                    logger.info(f"发现战斗目标~~")
                    context.run_task("AutoSky_EventDetection")  # 会自动完成战斗或探索

                    current_img = (
                        context.tasker.controller.post_screencap().wait().get()
                    )
                    if context.run_recognition("AutoSky_Lost", current_img):
                        logger.warning("遇到打不过的敌人，本轮探索结束")
                        time.sleep(2)
                        context.run_task("BackText_500ms")
                        self._encountered_unbeatable = True
                        break

                    # 只有在克隆体启用时才检查克隆体阵亡
                    if self._clone_enabled:
                        if context.run_recognition("AutoSky_TroopLoss", current_img):
                            logger.warning("识别到克隆体战损，本轮探索结束。")
                            time.sleep(2)
                            context.run_task("AutoSky_TroopLoss_Backtext")
                            self._troopLoss = True
                            break

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
                    ):
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
            ):
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
