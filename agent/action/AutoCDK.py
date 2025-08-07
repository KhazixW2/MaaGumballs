from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from utils import logger
import re
import time


@AgentServer.custom_action("AutoCdk")
class AutoCdk(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        # 傀儡节点（存储原始兑换码字符串）
        source_node = "Cdk_Source"
        # 二郎神节点（输入兑换码的节点）
        target_node = "Cdk_InputTexts"
        
        # 1. 读取傀儡节点的字符串
        source_data = context.get_node_data(source_node)
        if not source_data or not source_data.get("enabled", False):
            logger.error(f"傀儡节点 {source_node} 未启用或不存在")
            return CustomAction.RunResult(success=False)
        
        cdk_str = source_data.get("expected", "").strip()
        if not cdk_str:
            logger.error(f"傀儡节点 {source_node} 中未配置兑换码字符串")
            return CustomAction.RunResult(success=False)
        
        # 2. 分割字符串为兑换码数组
        cdk_list = [code.strip() for code in re.split(r"[,;/\n]", cdk_str) if code.strip()]
        if not cdk_list:
            logger.error("未解析到有效兑换码")
            return CustomAction.RunResult(success=False)
        
        logger.info(f"解析到 {len(cdk_list)} 个兑换码，开始执行最小步骤循环")
        
        # 3. 定义最小兑换步骤（pipeline最小流程）
        minimal_steps = [
            "Cdk_OpenInputPanel",  # 打开输入面板
            target_node,           # 二郎神节点（输入兑换码）
            "Cdk_Confirm",         # 确认兑换
            "Cdk_CloseResult"      # 关闭结果窗口
        ]
        
        # 4. 循环处理每个兑换码
        for index, code in enumerate(cdk_list, 1):
            if context.tasker.stopping:
                logger.warning("检测到停止信号，终止流程")
                return CustomAction.RunResult(success=False)
            
            logger.info(f"处理第 {index}/{len(cdk_list)} 个兑换码: {code}")
            
            # 覆盖二郎神节点的输入值
            context.override_node_data(target_node, {"expected": code})
            
            # 执行最小步骤流程
            step_success = True
            for step in minimal_steps:
                # 获取当前截图
                image = context.tasker.controller.post_screencap().wait().get()
                # 识别并执行步骤
                if not context.run_recognition(step, image):
                    logger.error(f"步骤 {step} 识别失败，中断当前兑换")
                    step_success = False
                    break
                context.run_task(step)
                time.sleep(0.5)  # 步骤间短延迟
            
            if not step_success:
                logger.warning(f"第 {index} 个兑换码处理失败，继续下一个")
                continue
            
            logger.info(f"第 {index} 个兑换码处理完成")
            time.sleep(1)  # 兑换间隔
        
        logger.info("所有兑换码处理完毕")
        return CustomAction.RunResult(success=True)
    