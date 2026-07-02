from nt import pipe
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from utils import logger

from action.fight.foreignDomainUtils import foreignDomainUtils

import time
import json


@AgentServer.custom_action("DailyTaskSelect")
class DailyTask(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:

        custom_order = [
            "DailySignIn",  # 每日签到
            "WildernessExplore",  # 荒野探索
            "CircusTask",  # 马戏团任务
            "DailySweep",  # 每日清扫
            "SendLizards",  # 派遣蜥蜴
            "AlchemySignboard",  # 炼金招牌
            "SkyExplore",  # 天空探索
            "RuinsExplore",  # 遗迹探索
            "WeeklyRaid",  # 每周周赛
            "FD_Entry" # 秩序域挖矿
        ]

        for key in custom_order:
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)
            # 检查任务是否开启

            nodeDetail = context.get_node_data(f"{key}")
            if not nodeDetail or not nodeDetail.get("enabled", False):
                logger.info(f"任务: {key} 已禁用, 跳过该任务")
                continue

            logger.info(f"执行任务: {key}")
            IsCheck = False
            context.run_action("HallSwipeToUp")
            if key == "FD_Entry":
                context.run_task("ReturnBigMap")
                context.run_task(key)
                IsCheck = True
            else:
                for i in range(3):
                    image = context.tasker.controller.post_screencap().wait().get()
                    if context.run_recognition(key, image).hit:
                        logger.info(f"第{i+1}轮检测到任务图标: {key}")
                        context.run_task(key)
                        IsCheck = True
                        break
                    else:
                        context.run_action("HallSwipeToDown")
            
            if IsCheck:
                logger.info(f"完成任务: {key}")
            else:
                logger.warning(f"任务: {key} 识别失败, 跳过该任务")
            
            if key == "FD_Entry":
                context.run_task("TSD_BackToBigMap")
            else:
                context.run_task("ReturnHall")

            time.sleep(1)

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("WeeklyRaidFighting")
class WeeklyRaidFighting(CustomAction):
    def __init__(self):
        self.weeklyRaidList = ["永恒王座", "六重天","惑星走私集团"]
        super().__init__()
        # 这个做成一个map，通过我们的副本名称一个string来映射一个string列表
        self.MonsterCheckPath: str = "dailyTask/weeklyRaid/"
        self.MonsterList1 = [
            self.MonsterCheckPath + "永恒王座冈布奥1.png",
            self.MonsterCheckPath + "永恒王座冈布奥2.png",
            self.MonsterCheckPath + "永恒王座冈布奥3.png",
            self.MonsterCheckPath + "永恒王座冈布奥4.png",
            self.MonsterCheckPath + "永恒王座冈布奥5.png",
            self.MonsterCheckPath + "永恒王座冈布奥6.png",
            self.MonsterCheckPath + "永恒王座冈布奥7.png",
        ]
        self.MonsterList2 = [
            self.MonsterCheckPath + "六重天冈布奥1.png",
            self.MonsterCheckPath + "六重天冈布奥2.png",
            self.MonsterCheckPath + "六重天冈布奥3.png",
            self.MonsterCheckPath + "六重天冈布奥4.png",
            self.MonsterCheckPath + "六重天冈布奥5.png",
            self.MonsterCheckPath + "六重天冈布奥6.png",
            self.MonsterCheckPath + "六重天冈布奥7.png",
        ]
        self.MonsterList3 = [
            self.MonsterCheckPath + "惑星走私集团1.png",
            self.MonsterCheckPath + "惑星走私集团2.png",
            self.MonsterCheckPath + "惑星走私集团3.png",
            self.MonsterCheckPath + "惑星走私集团4.png",
            self.MonsterCheckPath + "惑星走私集团5.png",
            self.MonsterCheckPath + "惑星走私集团6.png",
            self.MonsterCheckPath + "惑星走私集团7.png",
        ]
        self.MonsterMap = {
            "永恒王座": self.MonsterList1,
            "六重天": self.MonsterList2,
            "惑星走私集团": self.MonsterList3
        }

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        # 每周周赛战斗
        # 1. 检测是什么副本

        if recoDetail := context.run_recognition(
            "WeeklyRaid_Check",
            context.tasker.controller.post_screencap().wait().get(),
        ):
            if recoDetail.best_result.text in self.weeklyRaidList:
                taskName = recoDetail.best_result.text
                logger.info(f"检测到周赛战斗为: {taskName}")
        else:
            logger.warning("未检测到周赛战斗")
            return CustomAction.RunResult(success=False)

        # 2. 执行战斗, 一共6~7轮
        for i in range(12):
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)

            logger.info(f"第{i+1}/12轮识别怪物")
            if MonsterReco := context.run_recognition(
                "WeeklyRaid_MonsterCheck",
                context.tasker.controller.post_screencap().wait().get(),
                pipeline_override={
                    "WeeklyRaid_MonsterCheck": {"template": self.MonsterMap[taskName]}
                },
            ):
                if MonsterReco.hit:
                    # 2.1 点开怪物
                    for item in MonsterReco.filtered_results:
                        box = item.box
                        center_x, center_y = box[0] + box[2] // 2, box[1] + box[3] // 2
                        context.tasker.controller.post_click(center_x, center_y).wait()
                        time.sleep(0.5)
                        # 2.2 袭击怪物
                        context.run_task("WeeklyRaid_Attack")
                context.run_task("WeeklyRaid_SwipeToRight")

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("DailyGoldCoin_BuyClayPot_Costing")
class DailyGoldCoin_BuyClayPot_Costing(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:

        argv_dict: dict = json.loads(argv.custom_action_param)
        times = int(argv_dict.get("times", 10))

        # 1. 打开商店
        context.run_task("DailyGoldCoin_OpenShop")

        # 2. 购买 ClayPot
        for i in range(times):
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)
            context.run_task("DailyGoldCoin_BuyClayPot")

        time.sleep(2)
        # 兜底 检测最后一次是否触发土罐彩蛋
        if context.run_recognition(
            "DailyGoldCoin_BuyClayPot_Kickback",
            context.tasker.controller.post_screencap().wait().get(),
        ).hit:
            logger.info("触发了土罐彩蛋")
            context.run_task("DailyGoldCoin_BuyClayPot_Kickback_Confirm")

        context.run_task("ReturnBigMap")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("DailyForeignDomain_Explore")
class DailyForeignDomain_Explore(CustomAction):

    def __init__(self):
        super().__init__()
        self.FDUtils = foreignDomainUtils(self)

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        context.run_task("ClickCenterBelow_500ms")

        # 先关闭联盟聊天窗口，避免干扰
        self.FDUtils.closeUnionMsgBox(context)

        # 所有舰队返回
        self.FDUtils.returnFleets_FD(context)

        # 移动到地图右下角开始
        self.FDUtils.swipeMapToBottomRight(context)
        planets = ["X", "U", "E", "G"]
        default_fleets = ["奥鲁维", "卡纳斯", "游荡者", "深渊"]

        time.sleep(2)
        while len(planets) > 0:
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)

            remove_list = []
            for i in range(0, len(planets)):
                key = planets[i]
                img = context.tasker.controller.post_screencap().wait().get()
                recoDetail = context.run_recognition(
                    "FD_FindPlanet",
                    img,
                    pipeline_override={
                        "FD_FindPlanet": {
                            "template": f"fight/time_space_domain/planet{key}.png",
                            "threshold": 0.85,
                        }
                    },
                )
                if recoDetail.hit:
                    logger.info(f"检测到星球{key}")
                    box = recoDetail.best_result.box
                    context.tasker.controller.post_click(
                        box[0] + box[2] // 2 - 15, box[1] + box[3] // 2 - 15
                    )
                    time.sleep(2)
                    context.run_task(
                        "TSD_Investigate",
                        pipeline_override={
                            "TSD_Investigate": {
                                "recognition":"TemplateMatch",
                                "template": "fight/time_space_domain/派遣舰队.png",
                                "threshold": 0.9,
                            },
                            "TSD_SelectFreeFleetInList":{"expected": default_fleets[0]}
                        })
                    default_fleets.pop(0)
                    remove_list.append(key)

            if i == len(planets) - 1:
                self.FDUtils.swipeMap(context)
            for key in remove_list:
                planets.remove(key)
        logger.info("所有星球已全部找到")
        for key in self.FDUtils.fleetRoiList:
            box = self.FDUtils.fleetRoiList[key]
            context.tasker.controller.post_click(box[0] + box[2] // 2, box[1] + box[3] // 2)
            time.sleep(1)
            context.run_task("FD_PlanetExplore")
            time.sleep(1)
            context.run_task("BackText")
        logger.info("秩序域挖矿完成")
        

        return CustomAction.RunResult(success=True)
