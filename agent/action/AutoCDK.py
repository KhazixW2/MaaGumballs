from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from utils import logger
import time

@AgentServer.custom_action("AutoCdk")
class AutoCdk(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        """
        自动兑换密令（CDK）流程
        步骤顺序：
        1. 进入主设置菜单
        2. 定位密令入口
        3. 点击输入框
        4. 输入兑换码
        5. 确认提交
        6. 检测兑换结果
        """
        # 定义流程节点顺序（与JSON配置的next字段对应）
        cdk_flow = [
            "Cdk_MainSettingsEntrance",  # 主菜单入口
            "Cdk_Select_CdkEntrance",    # 密令入口
            "Cdk_Select_Textbox",        # 输入框定位
            "Cdk_InputTexts",           # 兑换码输入
            "Cdk_Text_Confirm",         # 确认提交
            "Cdk_CheckResult_flase"      # 失败检测
        ]

        # 从argv或外部获取兑换码（支持,; /分隔）
        cdk_codes = argv.get("Cdk_InputTexts", "").strip()
        if not cdk_codes:
            logger.error("未提供兑换码，任务终止")
            return CustomAction.RunResult(success=False)

        # 分割兑换码（兼容多种分隔符）
        codes = []
        for sep in [",", ";", "/"]:
            if sep in cdk_codes:
                codes = [code.strip() for code in cdk_codes.split(sep) if code.strip()]
                break
        if not codes:
            codes = [cdk_codes]  # 单兑换码情况

        logger.info(f"开始兑换密令，共{len(codes)}组")

        for code in codes:
            if context.tasker.stopping:
                logger.warning("检测到停止信号，终止兑换流程")
                return CustomAction.RunResult(success=False)

            # 动态设置当前兑换码（覆盖JSON中的expected空值）
            context.set_node_data("Cdk_InputTexts", {"expected": code})
            logger.info(f"正在兑换: {code}")

            # 按流程执行每个步骤
            for node in cdk_flow:
                if context.tasker.stopping:
                    break

                # 执行当前节点识别与操作
                image = context.tasker.controller.post_screencap().wait().get()
                if not context.run_recognition(node, image):
                    logger.warning(f"节点 {node} 识别失败，尝试中断处理")
                    self._handle_interrupt(context, node)
                    break

                # 执行节点动作（点击/输入等）
                context.run_task(node)
                time.sleep(context.get_node_data(node).get("post_delay", 1000) / 1000)

            # 返回大厅准备下一轮兑换
            context.run_task("ReturnHall")
            time.sleep(1)

        return CustomAction.RunResult(success=True)

    def _handle_interrupt(self, context: Context, current_node: str):
        """处理中断逻辑（如返回按钮、超时等）"""
        node_data = context.get_node_data(current_node)
        for interrupt_node in node_data.get("interrupt", []):
            if context.run_recognition(interrupt_node):
                context.run_task(interrupt_node)
                time.sleep(1)
                break