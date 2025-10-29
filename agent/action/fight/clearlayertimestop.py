from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger
from action.fight import fightProcessor


# 等待测试
@AgentServer.custom_action("Fight_ClearCurrentLayerTimeStop")
class Fight_ClearCurrentLayerTimeStop(CustomAction):
    def __init__(self) -> None:
        self.fightProcessor_ctx = fightProcessor.FightProcessor()

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # 需要自己设置时停的color lower和upper
        self.fightProcessor_ctx.clearCurrentLayer()

        return CustomAction.RunResult(success=True)
