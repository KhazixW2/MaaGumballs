from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from utils import logger

import time
import re


@AgentServer.custom_action("Reward_Execute")
class Reward_Execute(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        logger.info("开始领取联盟奖励")
        context.run_task("UnionReward_Start")
        logger.info("开始领取好友奖励")
        context.run_task("ObtainFriendReward")

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("UnionReward")
class UnionReward(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:

        roi_list = [
            [96, 814, 112, 110],
            [242, 812, 94, 102],
            [383, 816, 92, 94],
            [523, 816, 92, 94],
        ]

        for roi in roi_list:
            try:
                # Click Roi区域中间
                x_center, y_center = roi[0] + roi[2] // 2, roi[1] + roi[3] // 2
                context.tasker.controller.post_click(x_center, y_center)
                context.run_task("ObtainUnionReward")

            except Exception as e:
                print(f"Recognition error: {e}")
                continue

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("UnionReward_Execute")
class UnionReward_Execute(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:

        context.run_task("EntryUnionReward")

        img = context.tasker.controller.post_screencap().wait().get()
        if not context.run_recognition("CheckUnionWindows", img):
            context.run_task("BackText")

        context.run_task("EntryUnionTask")

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("CircusReward")
class CircusReward(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:

        context.run_task("getCircusReward_01")
        context.run_task("getCircusReward_01")
        context.run_task("getCircusReward_02")
        context.run_task("getCircusReward_03")

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("AutoCdk")
class AutoCdk(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        # 傀儡节点（存储原始密令字符串）
        source_node = "Cdk_Sources"
        target_node = "Cdk_TextInputAction"

        # 1. 读取傀儡节点的字符串
        source_data = context.get_node_data(source_node)
        if not source_data or not source_data.get("enabled", False):
            logger.error(f"傀儡节点 {source_node} 未启用或不存在")
            return CustomAction.RunResult(success=False)

        # cdk_str = "123,456".strip()
        cdk_str = source_data.get("focus", "").strip()
        if not cdk_str:
            logger.error(f"傀儡节点 {source_node} 中未配置密令字符串")
            return CustomAction.RunResult(success=False)

        # 2. 分割字符串为密令数组
        cdk_list = [
            code.strip() for code in re.split(r"[,;/\n]", cdk_str) if code.strip()
        ]
        if not cdk_list:
            logger.error("未解析到有效密令")
            return CustomAction.RunResult(success=False)
        logger.info(f"解析到 {len(cdk_list)} 个密令")

        # 3. 循环处理每个密令
        for index, code in enumerate(cdk_list, 1):
            if context.tasker.stopping:
                logger.warning("检测到停止信号，终止流程")
                return CustomAction.RunResult(success=False)

            logger.info(f"处理第 {index}/{len(cdk_list)} 个密令: {code}")
            context.override_pipeline({target_node: {"input_text": code}})
            context.run_task("BackText")
            context.run_task("Cdk_Start")
            logger.info(f"第 {index} 个密令处理完成")
            time.sleep(1)  # 兑换间隔

        logger.info("所有密令处理完毕")
        context.run_task("ReturnBigMap")
        return CustomAction.RunResult(success=True)
