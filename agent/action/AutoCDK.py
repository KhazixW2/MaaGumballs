from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from utils import logger
import re

@AgentServer.custom_action("AutoCdk")
class AutoCdk(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        # 只读取傀儡节点的 expected 字符串
        cdk_codes = argv.get("expected") or context.get_node_data("Cdk_InputTexts").get("expected", "")
        cdk_codes = cdk_codes.strip()
        if not cdk_codes:
            logger.error("未提供兑换码，任务终止")
            return CustomAction.RunResult(success=False)

        codes = [code.strip() for code in re.split(r"[,;/]", cdk_codes) if code.strip()]
        if not codes:
            logger.error("未解析到有效兑换码")
            return CustomAction.RunResult(success=False)

        logger.info(f"开始兑换密令，共{len(codes)}组")

        for code in codes:
            if context.tasker.stopping:
                logger.warning("检测到停止信号，终止兑换流程")
                return CustomAction.RunResult(success=False)

            # 只 override 输入节点
            context.override_node_data("Cdk_InputTexts", {"expected": code})
            logger.info(f"正在兑换: {code}")

            # 执行最小领取流程
            context.run_task("Cdk_InputTexts")

        return CustomAction.RunResult(success=True)