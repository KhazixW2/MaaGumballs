from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from utils import logger
from PIL import Image

import json
import os
from datetime import datetime


@AgentServer.custom_action("Count")
class Count(CustomAction):
    def _run_nodes(self, context: Context, nodes):
        """统一处理节点执行逻辑"""
        if not nodes:
            return
        if isinstance(nodes, str):
            nodes = [nodes]
        for node in nodes:
            context.run_task(node)

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        """
        自定义动作：
        custom_action_param:
            {
                "count": 0,
                "target_count": 10,
                "next_node": ["node1", "node2"],
                "else_node": ["node3"],
            }
        count: 当前次数
        target_count: 目标次数
        next_node: 达到目标次数后执行的节点. 支持多个节点，按顺序执行，可以出现重复节点，可以为空
        else_node: 未达到目标次数时执行的节点. 支持多个节点，按顺序执行，可以出现重复节点，可以为空
        """

        argv_dict: dict = json.loads(argv.custom_action_param)
        print(argv_dict)
        if not argv_dict:
            return CustomAction.RunResult(success=True)

        current_count = argv_dict.get("count", 0)
        target_count = argv_dict.get("target_count", 0)

        if current_count <= target_count:
            argv_dict["count"] = current_count + 1
            context.override_pipeline(
                {argv.node_name: {"custom_action_param": argv_dict}}
            )
            self._run_nodes(context, argv_dict.get("else_node"))
        else:
            context.override_pipeline(
                {
                    argv.node_name: {
                        "custom_action_param": {
                            "count": 0,
                            "target_count": target_count,
                            "else_node": argv_dict.get("else_node"),
                            "next_node": argv_dict.get("next_node"),
                        }
                    }
                }
            )
            self._run_nodes(context, argv_dict.get("next_node"))

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("CountTask")
class CountTask(CustomAction):

    def _run_nodes(self, context: Context, nodes):
        """统一处理节点执行逻辑"""
        if not nodes:
            return
        if isinstance(nodes, str):
            nodes = [nodes]
        for node in nodes:
            context.run_task(node)

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        """
                自定义动作：
        custom_action_param:
            {
                "count": int,
                "target_count": int,
                "next_node": string
            }
        count: 当前次数
        target_count: 目标次数
        next_node: 达到目标次数后执行的节点

        "CountTask_RunNode"节点：通过interface.json中的override来控制run_task使用的节点内容
        """
        argv_dict: dict = json.loads(argv.custom_action_param)
        if not argv_dict:
            return CustomAction.RunResult(success=True)

        count = argv_dict.get("count")
        target_count = argv_dict.get("target_count")

        while count < target_count:
            logger.info(f"执行第{count + 1}次, {count + 1}/{target_count}")
            context.run_task("CountTask_RunNode")
            count += 1

        context.override_pipeline(
            {
                argv.node_name: {
                    "custom_action_param": {
                        "count": 0,
                        "target_count": target_count,
                        "next_node": argv_dict.get("next_node"),
                    }
                }
            }
        )
        self._run_nodes(context, argv_dict.get("next_node"))

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Screenshot")
class Screenshot(CustomAction):
    """
    自定义截图动作，保存当前屏幕截图到指定目录。

    参数格式:
    {
        "save_dir": "保存截图的目录路径"
    }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        # image array(BGR)
        screen_array = context.tasker.controller.post_screencap().wait().get()

        # BGR2RGB
        if len(screen_array.shape) == 3 and screen_array.shape[2] == 3:
            rgb_array = screen_array[:, :, ::-1]
        else:
            rgb_array = screen_array
            logger.warning("当前截图并非三通道")

        img = Image.fromarray(rgb_array)

        save_dir = json.loads(argv.custom_action_param)["save_dir"]
        os.makedirs(save_dir, exist_ok=True)
        now = datetime.now()
        img.save(f"{save_dir}/{self._get_format_timestamp(now)}.png")
        logger.info(f"截图保存至 {save_dir}/{self._get_format_timestamp(now)}.png")

        task_detail = context.tasker.get_task_detail(argv.task_detail.task_id)
        logger.debug(
            f"task_id: {task_detail.task_id}, task_entry: {task_detail.entry}, status: {task_detail.status._status}"
        )

        return CustomAction.RunResult(success=True)

    def _get_format_timestamp(self, now):

        date = now.strftime("%Y.%m.%d")
        time = now.strftime("%H.%M.%S")
        milliseconds = f"{now.microsecond // 1000:03d}"

        return f"{date}-{time}.{milliseconds}"
