"""
MAA_SnowBreak
MAA_SnowBreak pipeline覆盖器
作者:overflow65537
"""

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
import json


@AgentServer.custom_action("PPOverride")
class PPOverride(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        argv = json.loads(argv.custom_action_param)
        if not argv:
            return CustomAction.RunResult(success=True)
        context.override_pipeline(argv)
        return CustomAction.RunResult(success=True)
