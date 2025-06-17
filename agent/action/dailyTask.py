from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from utils import logger

import json
import time  

@AgentServer.custom_action("DailyTaskSelect")
class DailyTask(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        taskList: dict = json.loads(argv.custom_action_param)
        logger.info(taskList)

        custom_order = [
            "DailySignIn",    # 每日签到
            "WildernessExplore",  # 荒野探索
            "CircusTask",      # 马戏团任务
            "DailySweep",     # 每日清扫
            "SendLizards",    # 派遣蜥蜴
            "AlchemySignboard",   # 炼金招牌
            "SkyExplore",     # 天空探索
            "RuinsExplore",   # 遗迹探索
        ]

        for key in custom_order:
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)
            
            if taskList.get(key) == 1:
                # 生成任务执行逻辑框架
                logger.info(f"执行任务: {key}")
                image = context.tasker.controller.post_screencap().wait().get()
                if context.run_recognition(key,image):
                    context.run_task(key)
                    logger.info(f"完成任务: {key}")
                else:
                    logger.warning(f"任务: {key} 识别失败, 跳过该任务")
                context.run_task("ReturnHall")
                
                time.sleep(2)

        return CustomAction.RunResult(success=True)
