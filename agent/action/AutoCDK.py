from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from utils import logger
import re
import time


@AgentServer.custom_action("AutoCdk")
class AutoCdk(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        # 傀儡节点（存储原始兑换码字符串）
        source_node = "Cdk_Sources"
        target_node = "Cdk_TextInputAction"
        internal_node = "Cdk_Select_Textbox"

        # 1. 读取傀儡节点的字符串
        source_data = context.get_node_data(source_node)
        if not source_data or not source_data.get("enabled", False):
            logger.error(f"傀儡节点 {source_node} 未启用或不存在")
            return CustomAction.RunResult(success=False)

        # cdk_str = "123,456".strip()
        cdk_str = source_data.get("expected", "").strip()
        if not cdk_str:
            logger.error(f"傀儡节点 {source_node} 中未配置兑换码字符串")
            return CustomAction.RunResult(success=False)

        # 2. 分割字符串为兑换码数组
        cdk_list = [
            code.strip() for code in re.split(r"[,;/\n]", cdk_str) if code.strip()
        ]
        if not cdk_list:
            logger.error("未解析到有效兑换码")
            return CustomAction.RunResult(success=False)
        logger.info(f"解析到 {len(cdk_list)} 个兑换码，开始执行最小步骤循环")

        # 3. 循环处理每个兑换码
        for index, code in enumerate(cdk_list, 1):
            if context.tasker.stopping:
                logger.warning("检测到停止信号，终止流程")
                return CustomAction.RunResult(success=False)

            logger.info(f"处理第 {index}/{len(cdk_list)} 个兑换码: {code}")
            context.override_pipeline({target_node: {"input_text": code}})
            context.run_task("Cdk_Start")
            context.override_pipeline({internal_node: {"expected": code}})
            logger.info(f"第 {index} 个兑换码处理完成")
            time.sleep(1)  # 兑换间隔

        logger.info("所有兑换码处理完毕")
        return CustomAction.RunResult(success=True)
