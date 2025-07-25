from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger
import time


@AgentServer.custom_action("Autosky")
class Autosky(CustomAction):
    """
    一个按顺序执行Maa Pipeline节点以完成天空探索自动化任务的自定义动作。
    """

    def __init__(self):
        super().__init__()
        self.context = None  # 用于存储Maa上下文，方便在辅助方法中使用
        self.explore_attempts_per_batch = 16  # 每批次尝试探索/战斗的次数
        self.total_batches = 3  # 总共进行多少批次的探索

    def _initialize(self, context: Context):
        """
        初始化方法，用于在run方法开始时设置上下文。
        """
        self.context = context
        logger.info("Autosky: 初始化完毕，准备开始天空探索任务。")

    def _run_task(
        self, task_name: str, task_description: str = "", fail_on_error: bool = True
    ) -> bool:
        """
        封装执行单个Maa Pipeline任务的逻辑，包括日志、停止检查和结果判断。
        :param task_name: 要执行的Maa Pipeline节点名称。
        :param task_description: 任务的描述，用于日志。
        :param fail_on_error: 是否在任务失败时立即返回False。某些任务（如能量不足提示）失败是预期行为。
        :return: 如果任务成功则返回True，否则返回False。
        """
        full_description = (
            f"{task_description} ({task_name})" if task_description else task_name
        )
        logger.info(f"Autosky: 正在执行任务 - {full_description}...")

        # 检查是否收到停止任务的请求
        if self.context.tasker.stopping:
            logger.info(
                f"Autosky: 检测到停止任务请求，在执行 {full_description} 前退出。"
            )
            return False  # 返回False表示任务未完成，以便上层逻辑能够中止

        run_result_detail = self.context.run_task(task_name)

        # 判断任务是否成功：
        task_successful = True
        if hasattr(run_result_detail, "nodes") and not run_result_detail.nodes:
            task_successful = False

        if not task_successful:
            if fail_on_error:
                logger.error(
                    f"Autosky: 任务 '{full_description}' 执行失败或未达到成功条件！"
                )
                return False
            else:
                # 预期失败的情况，例如识别到“能量不足”或“无法显示更多目标”
                logger.warning(
                    f"Autosky: 任务 '{full_description}' 未找到匹配，按预期处理。"
                )
                return (
                    True  # 虽然没找到匹配，但我们认为这是成功处理了一种情况，让流程继续
                )
        else:
            logger.info(f"Autosky: 任务 '{full_description}' 执行成功。")
            time.sleep(1)  # 模拟用户操作间隔
            return True

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        """
        执行自定义动作的核心逻辑。
        :param context: Maa提供的上下文对象，用于与Maa框架交互。
        :param argv: 动作的参数（如果JSON中配置了）。
        :return: CustomAction.RunResult，表示动作的成功或失败。
        """
        self._initialize(context)

        # --- 任务开始流程 ---
        # 1. 进入伊甸并寻找天空探索入口
        if not self._run_task("EntryEden_Autosky", "进入伊甸"):
            logger.error("Autosky: 进入伊甸失败，任务终止。")
            return CustomAction.RunResult(success=False)

        # --- 循环探索批次 ---
        for i in range(1, self.total_batches + 1):
            logger.info(
                f"Autosky: 开始第 {i} 个探索批次（共 {self.total_batches} 批次）。"
            )

            # 检查停止请求
            if self.context.tasker.stopping:
                logger.info(
                    f"Autosky: 检测到停止任务请求，在第 {i} 批次开始前退出。任务被手动停止。"
                )
                return CustomAction.RunResult(success=False)

            # 执行 X 次浮岛探索/战斗尝试
            for attempt_num in range(1, self.explore_attempts_per_batch + 1):
                logger.info(
                    f"Autosky: 第 {i} 批次，进行第 {attempt_num}/{self.explore_attempts_per_batch} 次浮岛探索/战斗尝试。"
                )

                if not self._run_task(
                    "ChangeTarget0_Autosky", "尝试切换浮岛并探索/战斗"
                ):
                    logger.warning(
                        f"Autosky: 第 {i} 批次，第 {attempt_num} 次浮岛探索尝试的启动节点失败。可能没有可点击目标，将继续下一个尝试。"
                    )
                    # 这里保持 `pass` 策略，允许继续尝试其他浮岛
                    pass

            # 离开雷达界面
            if not self._run_task("Exit_Radar_Interface_Autosky", "离开雷达界面"):
                logger.error("Autosky: 离开雷达界面失败，任务终止。")
                return CustomAction.RunResult(success=False)

            # 进行一次自动探索消耗能量
            # 如果未能点击自动探索按钮，则认为是任务进入异常状态
            if not self._run_task("SkyExplore_Start_Autosky", "点击自动探索按钮"):
                logger.error(
                    "Autosky: 未能点击自动探索按钮，任务可能陷入异常状态，终止。"
                )
                return CustomAction.RunResult(success=False)

            # 关键：如果 SkyExplore_Start_Autosky 成功点击后，Maa Pipeline 自动进入了
            # SkyExplore_LackOfEnergy_Autosky 或 SkyExplore_LackOfBox_Autosky（它们最终会StopCureentTask）
            # 那么当前的 CustomAction 也会随之终止。
            # 如果当前 CustomAction 没有终止，就意味着自动探索成功并返回到了雷达界面，可以继续下一个批次。
            # 因此，这里不需要额外的 `if` 判断。

        logger.info(
            f"Autosky: 所有 {self.total_batches} 个批次的探索任务执行完毕。任务执行成功。"
        )
        return CustomAction.RunResult(success=True)
