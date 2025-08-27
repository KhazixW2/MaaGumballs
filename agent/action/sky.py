import time
import numpy  # 用于处理截图
from typing import Optional, Dict

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger, send_message  # False设这些已定义

# 定义目标探索轮次，先内置为5 因为我还没学会怎么从interface修改
TARGET_EXPLORATION_ROUNDS = 5
MAX_RETRY_ATTEMPTS = 3  # 定义最大重试次数


@AgentServer.custom_action("Autosky")
class Autosky(CustomAction):
    _completed_exploration_rounds: int
    _encountered_unbeatable: bool  #
    _TroopLoss: bool  # 记录是否出现克隆体战损
    _target_exploration_rounds: int

    def __init__(self):
        super().__init__()

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        self._completed_exploration_rounds = 0
        self._encountered_unbeatable = False
        self._TroopLoss = False
        self._target_exploration_rounds = TARGET_EXPLORATION_ROUNDS
        logger.info(
            f"Autosky 自定义动作初始化完成，目标探索轮次: {self._target_exploration_rounds}。"
        )

        # 1. 任务起始：尝试进入伊甸并到达天空探索雷达界面
        logger.info("尝试进入天空探索雷达界面...")
        initial_entry_result = context.run_task("Autosky_Start")
        if not initial_entry_result:
            logger.error("未能成功进入天空探索雷达界面，Autosky 任务终止。")
            send_message("MaaGB", "天空探索：未能进入雷达界面，任务终止。")
            return CustomAction.RunResult(success=False)

        # 验证是否真的在探索界面
        current_img = context.tasker.controller.post_screencap().wait().get()
        if not context.run_recognition("Autosky_CheckExplorationInfo", current_img):
            logger.error("任务开始后未能识别到探索信息界面，Autosky 任务终止。")
            send_message("MaaGB", "天空探索：未能在探索界面启动，任务终止。")
            return CustomAction.RunResult(success=False)
        logger.info("已成功进入天空探索雷达界面。")

        # 主循环：执行每一轮完整的探索逻辑
        while (
            not self._encountered_unbeatable
            and not self._TroopLoss
            and self._completed_exploration_rounds < self._target_exploration_rounds
        ):  # 这个是外层的while 用于控制探索轮次（进雷达界面扫一圈+自动探索=完整的一轮）

            # 2. 定期检查停止请求 (在每轮开始和内部操作前检查)
            if context.tasker.stopping:
                logger.info("检测到停止任务请求，Autosky 任务终止。")
                send_message("MaaGB", "天空探索：任务被用户停止。")
                return CustomAction.RunResult(success=False)

            # --- 开始一轮完整的探索 ---
            self._completed_exploration_rounds += 1  # 提前递增轮次，表示即将开始第 X 轮
            logger.info(f"--- 开始第 {self._completed_exploration_rounds} 轮探索 ---")

            # 3. 获取当前目标数，确定本次手动探索的上限
            current_img = context.tasker.controller.post_screencap().wait().get()
            target_num_reco = context.run_recognition(
                "Autosky_CheckTargetNum", current_img
            )

            max_manual_attempts = 7  # 默认尝试7次 为什么是7呢，因为ocr容易把7识别成门
            if (
                target_num_reco
                and target_num_reco.best_result
                and target_num_reco.best_result.text
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

            # 4. 循环进行“手动目标探索”
            logger.info(f"开始本轮手动探索 ({max_manual_attempts} 次尝试)。")
            manual_attempts_done = 0

            while (
                manual_attempts_done < max_manual_attempts
            ):  # 这个是内层的while 用于控制雷达界面的探索次数
                # 检查停止请求 (循环内部的快速退出)
                if context.tasker.stopping:
                    logger.info("检测到停止任务请求（手动探索中），Autosky 任务终止。")
                    send_message("MaaGB", "天空探索：任务被用户停止（手动探索）。")
                    return CustomAction.RunResult(success=False)

                context.run_action("Autosky_ChangeTarget")  # 切换目标
                manual_attempts_done += 1
                time.sleep(0.5)  # 延迟0.5秒后，重复第二步

                current_img = context.tasker.controller.post_screencap().wait().get()
                is_rift = context.run_recognition(
                    "Autosky_RiftDetection", current_img
                )  # 检查是否为裂隙

                if not is_rift:
                    logger.info(
                        f"在第 {manual_attempts_done} 次尝试中找到非裂隙目标，执行事件。"
                    )
                    context.run_task("Autosky_EventDetection")  # 会自动完成战斗或探索

                    # 检查是否打不过 是否出现克隆体战损
                    current_img = (
                        context.tasker.controller.post_screencap().wait().get()
                    )
                    lost_result = context.run_recognition("Autosky_Lost", current_img)
                    trooploss_result = context.run_recognition(
                        "Autosky_TroopLoss", current_img
                    )
                    if lost_result:
                        logger.warning(
                            "识别到 '继续袭击' 界面，判断为遇到打不过的敌人，本轮手动探索中断。"
                        )
                        context.run_task("BackText_500ms")  # 离开继续袭击界面
                        self._encountered_unbeatable = True  # 设置标志位

                        break  # 立即中断雷达探索部分
                    elif trooploss_result:
                        logger.warning(
                            "识别到克隆体战损，判断为遇到打不过的敌人，本轮手动探索中断。"
                        )
                        context.run_task(
                            "Autosky_TroopLoss_Backtext"
                        )  # 离开克隆体战损界面
                        self._TroopLoss = True  # 设置标志位
                        break  # 立即中断雷达探索部分

                    else:
                        logger.info(
                            "事件处理完成，未遇到打不过的敌人。将继续在当前雷达界面寻找下一个目标。"
                        )
                        # 此时已在雷达界面，直接让外层循环进入下一次手动尝试
                else:
                    logger.debug(
                        f"当前目标为时空裂痕，继续切换 ({manual_attempts_done}/{max_manual_attempts} 次尝试)。"
                    )

            logger.info("完成手动探索尝试，开始本轮的自动探索环节。")

            # --- 为提高稳定性，确保顺利离开雷达界面并完成自动探索，添加重试功能 ---
            hasLeftRadar = False
            auto_explore_successful = False

            auto_explore_successful = False
            for retry_count in range(MAX_RETRY_ATTEMPTS):
                if context.tasker.stopping:  # 重试前再次检查停止请求
                    logger.info(
                        f"检测到停止任务请求（自动探索重试 {retry_count+1} 中），Autosky 任务终止。"
                    )
                    send_message("MaaGB", "天空探索：任务被用户停止（自动探索重试）。")
                    return CustomAction.RunResult(success=False)

                # 确保在雷达界面，如果不是，说明出现了异常情况
                if hasLeftRadar == False:
                    current_img = (
                        context.tasker.controller.post_screencap().wait().get()
                    )
                    if context.run_recognition(
                        "Autosky_CheckExplorationInfo", current_img
                    ):
                        logger.info(f"确认目前处于雷达界面")

                    else:
                        logger.warning(f"不在雷达界面，属于异常情况，自动退出")
                        return CustomAction.RunResult(success=False)

                # 尝试离开雷达界面
                if hasLeftRadar == False:
                    context.run_task("Autosky_Exit_Radar_Interface")  # 离开雷达界面

                # 检查是否成功离开了雷达界面 (例如，雷达界面图标消失)
                current_img = context.tasker.controller.post_screencap().wait().get()
                if context.run_recognition(
                    "Autosky_CheckExplorationInfo", current_img
                ):  # 如果还识别到探索信息，说明没离开成功
                    logger.warning("未能成功离开雷达界面，重新尝试。")
                    time.sleep(2)  # 失败后等待一下
                    continue  # 继续下一次重试
                else:
                    hasLeftRadar = True
                    time.sleep(1)
                sky_explore_start_result = context.run_task(
                    "Autosky_SkyExplore_Start"
                )  # 开始自动探索

                if sky_explore_start_result:  # 如果任务流成功触发（不代表探索完成）
                    logger.info("成功触发自动探索。")
                    auto_explore_successful = True
                    break  # 成功触发，跳出重试循环
                else:
                    logger.warning("未能成功触发自动探索，重新尝试。")
                    time.sleep(2)  # 失败后等待一下

            if not auto_explore_successful:
                logger.error(
                    f"达到最大重试次数 ({MAX_RETRY_ATTEMPTS})，未能成功触发自动探索。Autosky 任务终止。"
                )
                send_message("MaaGB", "天空探索：自动探索启动失败，任务终止。")
                return CustomAction.RunResult(success=False)
            # --- 重试逻辑结束 ---

            time.sleep(2)  # 给自动探索一些时间让其执行

            # 检查自动探索结果
            current_img = context.tasker.controller.post_screencap().wait().get()
            result = context.run_recognition(
                "Autosky_SkyExplore_Confirm_Finish", current_img
            )

            if not result:
                logger.info("未成功消耗能量，可能没能量或者雷达满了，任务结束。")
                # 强制达到退出条件，并跳出主循环
                self._completed_exploration_rounds = self._target_exploration_rounds
                break
            else:
                logger.info("自动探索成功，消耗了能量。")
                context.run_task(
                    "Autosky_SkyExplore_Confirm_Finish"
                )  # 确认完成，并自动回到雷达界面
                # 继续下一轮主循环（如果没有达到目标轮次且没有遇到打不过的敌人）

        # 主循环结束后的最终处理
        if self._encountered_unbeatable:
            logger.info("Autosky 任务因遇到打不过的敌人而终止。自动回到大地图")
            context.run_task("Autosky_ReturnBigMap")
            return CustomAction.RunResult(success=False)
        elif self._TroopLoss:
            logger.info("Autosky 任务因遇到克隆体战损而终止。自动回到大地图")
            context.run_task("Autosky_ReturnBigMap")
            return CustomAction.RunResult(success=False)
        elif self._completed_exploration_rounds >= self._target_exploration_rounds:
            logger.info(
                f"Autosky 任务已成功完成全部 {self._target_exploration_rounds} 轮探索。自动回到大地图"
            )
            send_message(
                "MaaGB",
                f"天空探索：已完成全部 {self._target_exploration_rounds} 轮探索。",
            )
            context.run_task("Autosky_ReturnBigMap")
            return CustomAction.RunResult(success=True)
        else:
            logger.error("Autosky 任务意外退出")
            return CustomAction.RunResult(success=False)
