from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
import json

@AgentServer.custom_action("Count")
class Count(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        '''
                自定义动作：
        custom_action_param:
            {
                "count": int,
                "target_count": int,
                "next_node": string,
                "run_node": string
            }
        count: 当前次数
        target_count: 目标次数
        next_node: 达到目标次数后执行的节点
        run_node:未达到目标次数前执行的节点,可以是某个任务链的开始节点
        '''
        argv: dict = json.loads(argv.custom_action_param)
        print(argv)
        if not argv:
            return CustomAction.RunResult(success=True)
        if argv.get("count") <= argv.get("target_count"):
            argv["count"] += 1
            context.override_pipeline(
                {
                    argv.get("self"): {
                        "custom_action_param": argv,
                    },
                }
            )
            print(f"execute {argv.get('count')}  argv.get("run_node"")
            context.run_task(argv.get("run_node"))
        else:
            context.override_pipeline(
                {
                    argv.get("self"): {
                        "custom_action_param": {
                            "self": argv.get("self"),
                            "run_node": "TL01_Start",
                            "count": 0,
                            "target_count": argv.get("target_count"),
                            "next_node": argv.get("next_node"),
                        },
                    },
                }
            )
            for i in argv.get("next_node"):
                context.run_task(i)

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("CountTask") 
class CountTask(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        argv: dict = json.loads(argv.custom_action_param)
        print(argv)
        if not argv:
            return CustomAction.RunResult(success=True)

        count = argv.get("count")
        target_count = argv.get("target_count")
        print(f"count = {count}, target_count = {target_count}")
        while count < target_count:
            print(f"excute {count} TL01_Start")
            context.run_task("TL01_Start")
            count += 1

        for i in argv.get("next_node"):
            context.run_task(i)

        return CustomAction.RunResult(success=True)
