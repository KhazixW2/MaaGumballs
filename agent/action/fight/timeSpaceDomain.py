from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.define import RecognitionDetail

from utils import logger, send_message
from action.fight import fightUtils

import time
import json


@AgentServer.custom_action("TSD_explore")
class TSD_explore(CustomAction):

    def __init__(self):
        super().__init__()

        # 舰队状态roi列表
        self.fleetRoiList: dict = {
            "奥鲁维": [130, 199, 60, 51],
            "卡纳斯": [227, 200, 63, 50],
            "游荡者": [327, 200, 64, 49],
            "深渊": [425, 199, 64, 53],
        }

        self.powerList: dict = {}  # 舰队战力
        self.highestFleet = ""  # 最高战力舰队
        self.exploreNums = 1  # 剩余需要探索的次数
        self.fleet_nums = 4  # 默认出战舰队数量
        self.fight_fleets = []  # 根据选择的舰队数量按战力大小排列的舰队列表
        self.check = False  # 是否从左上角开始检查
        self.direction = "Right"  # 移动方向
        self.isDown = False  # 是否下移过一次
        self.planetList: list = []  # 记录探索的星球

    # 获取舰队战力值
    def getAllFleetPower(self, context: Context) -> bool:
        fleetPowerRoiList: dict = {
            "奥鲁维": [62, 123, 139, 28],
            "卡纳斯": [207, 123, 150, 27],
            "游荡者": [361, 124, 151, 26],
            "深渊": [515, 120, 140, 32],
        }

        img = context.tasker.controller.post_screencap().wait().get()
        for key in fleetPowerRoiList:
            nums = context.run_recognition(
                "TSD_getPowerNumber",
                img,
                pipeline_override={
                    "TSD_getPowerNumber": {"roi": fleetPowerRoiList[key]}
                },
            )
            if nums:
                powerNumber = fightUtils.extract_num(nums.filterd_results[0].text)
                self.powerList[key] = powerNumber
            else:
                self.powerList[key] = 0
        self.comparePower(self.powerList)
        return True

    # 获取最高战力舰队
    def comparePower(self, powerList: dict):
        powerList = dict(
            sorted(powerList.items(), key=lambda item: item[1], reverse=True)
        )
        self.fight_fleets = list(powerList.keys())[: self.fleet_nums]
        self.highestFleet = self.fight_fleets[0] if self.fight_fleets else ""

    # 检查舰队状态，是否都是空闲
    def checkAllFleetStatus(self, context: Context) -> int:
        img = context.tasker.controller.post_screencap().wait().get()
        fleetStatus = context.run_recognition(
            "checkAllFleetStatus",
            img,
            pipeline_override={
                "checkAllFleetStatus": {
                    "recognition": "TemplateMatch",
                    "template": "fight/time_space_domain/fleetFree.png",
                    "roi": [109, 182, 397, 95],
                    "threshold": 0.8,
                }
            },
        )
        if fleetStatus and fleetStatus.filterd_results:
            return len(fleetStatus.filterd_results)
        else:
            return 0

    # 返回所有舰队
    def returnFleets(self, context: Context) -> bool:
        while True:
            img = context.tasker.controller.post_screencap().wait().get()
            for key in self.fleetRoiList:
                status = context.run_recognition(
                    "TSD_checkFreeFleet",
                    img,
                    pipeline_override={
                        "TSD_checkFreeFleet": {"roi": self.fleetRoiList[key]}
                    },
                )
                if not status:
                    time.sleep(1)
                    logger.info(f"正在返回{key}舰队")
                    context.run_task(
                        "TSD_ClickFleet",
                        pipeline_override={
                            "TSD_ClickFleet": {"target": self.fleetRoiList[key]}
                        },
                    )
                    context.run_task(
                        "TSD_ReturnFleet",
                        pipeline_override={
                            "TSD_checkTargetFleetFree": {"roi": self.fleetRoiList[key]},
                            "TSD_View": {
                                "next": ["TSD_EndExploit"],
                                "interrupt": [
                                    "TSD_WithdrawFleet",
                                    "TSD_EndExplore",
                                    "BackText",
                                ],
                            },
                        },
                    )
                    time.sleep(1)
                else:
                    logger.info(f"{key}舰队已返回,无需操作")
            if nums := self.checkAllFleetStatus(context) == 4:
                logger.info("所有舰队已返回")

                break
        return True

    # 获取当前屏幕的探索目标
    def GetTaskTargetList(self, context: Context, taskType: str, threshold: float):
        TargetTemplate: dict = {
            "explore": "exploreTarget",
            "monster": "monsterTarget",
            "monster_boss": "monsterBossTarget",
            "planet": "planet",
            "monster_planet": "monsterPlanetTarget",
            "exploit": "exploitTarget",
        }
        img = context.tasker.controller.post_screencap().wait().get()
        template = f"fight/time_space_domain/{TargetTemplate[taskType]}.png"
        if taskType == "planet":
            template = [f"fight/time_space_domain/planet{i}.png" for i in range(0, 5)]
        exploreList = context.run_recognition(
            "GetTaskTargetList",
            img,
            pipeline_override={
                "GetTaskTargetList": {
                    "recognition": "TemplateMatch",
                    "template": template,
                    "roi": [12, 268, 693, 872],
                    "threshold": threshold,
                }
            },
        )
        if exploreList and exploreList.filterd_results:
            self.exploreNums = len(exploreList.filterd_results)
            self.check = False  # 存在目标，需要在运行到右下角时从左上角开始检查
            return exploreList.filterd_results
        else:
            self.exploreNums = 0
            return []

    # 按列表执行事件
    def runTask(
        self,
        context: Context,
        taskType: str,
    ) -> bool:
        taskEntry: dict = {
            "explore": {"taskName": "TSD_Investigate", "pipeline_override": None},
            "monster": {
                "taskName": "TSD_ClearMonster",
                "pipeline_override": {
                    "TSD_SelectFreeFleetInList": {
                        "recognition": "OCR",
                        "expected": self.fight_fleets[:1],
                        "roi": [44, 164, 627, 537],
                        "interrupt": ["TSD_SelectCancelButton"],
                        "next": ["TSD_ClickAttackButton"],
                    }
                },
            },
            "monster_boss": {
                "taskName": "TSD_ClearMonster",
                "pipeline_override": {
                    "TSD_ClickFleetButton": {"next": "TSD_SelectHighestFleet"},
                    "TSD_SelectHighestFleet": {"expected": [self.highestFleet]},
                },
            },
            "exploit": "TSD_ExploitAllFleet",  # 占位，未实现
        }
        exploreList = None
        inPlanet = False
        if taskType == "planet":
            inPlanet = True
            taskType = "monster"  # 星球小怪任务使用清理小怪任务的逻辑
            # 因为小怪图片不一样，所以获取怪物的参数不一样
            exploreList = self.GetTaskTargetList(context, "monster_planet", 0.8)
        elif taskType == "explore":
            exploreList = self.GetTaskTargetList(context, taskType, 0.91)
        else:
            exploreList = self.GetTaskTargetList(context, taskType, 0.82)
        for explore in exploreList:
            box = explore.box
            btn = context.tasker.controller.post_click(
                box[0] + box[2] // 2, box[1] + box[3] // 2
            )
            time.sleep(2)
            task1 = None
            if taskEntry[taskType]["pipeline_override"]:
                task1 = context.run_task(
                    taskEntry[taskType]["taskName"],
                    pipeline_override=taskEntry[taskType]["pipeline_override"],
                )
            else:
                task1 = context.run_task(taskEntry[taskType]["taskName"])
            if task1.status.succeeded == False:
                context.run_task("BackText")
                return False
            self.exploreNums -= 1
            self.fight_fleets.append(self.fight_fleets.pop(0))  # 轮换舰队顺序
            taskEntry["monster"]["pipeline_override"]["TSD_SelectFreeFleetInList"][
                "expected"
            ] = self.fight_fleets[:1]
            # logger.info(f"出战舰队顺序: {self.fight_fleets}")
            if inPlanet and self.exploreNums == 0:
                # 星球小怪任务完成后，返回地图
                logger.info("该星球已无小怪，返回地图")
                context.run_task("BackText")
            time.sleep(1)
        return True

    def checkBoundary(self, context: Context, direction: str) -> bool:
        boundaryRoiDict: dict = {
            "LeftTop": [12, 268, 137, 147],
            "Right": [597, 272, 96, 871],
            "Left": [14, 275, 116, 766],
            "RightBottom": [590, 1052, 117, 102],
        }
        img = context.tasker.controller.post_screencap().wait().get()
        boundaryList = context.run_recognition(
            "GridCheckTargetBoundary",
            img,
            pipeline_override={
                "GridCheckTargetBoundary": {
                    "recognition": "TemplateMatch",
                    "template": f"fight/time_space_domain/boundary{direction}.png",
                    "roi": boundaryRoiDict[direction],
                    "threshold": 0.92,
                }
            },
        )
        if boundaryList and boundaryList.filterd_results:
            return True
        return False

    def swipeMapToLeftTop(self, context: Context):
        while True:  # 将地图移动至左上角
            if self.checkBoundary(context, "LeftTop"):
                break
            else:
                context.run_task("FD_SwipeMapMiddleToTopLeft")
            time.sleep(1)
        self.direction = "Right"
        self.isDown = False
        time.sleep(1)

    def swipeMap(self, context: Context):
        if self.checkBoundary(context, self.direction):
            logger.info(f"地图{self.direction}边界")
            if self.checkBoundary(context, "RightBottom"):
                logger.info("已到达地图边界")
                if self.check:
                    self.check = False
                    return False
                else:
                    # 返回地图左上角重新检查一遍
                    self.check = True
                    self.swipeMapToLeftTop(context)

            elif not self.isDown:  # 未达到右下角，地图下移一次
                logger.info("地图下移")
                context.run_task("FD_SwipeMapToDown")
                self.direction = "Left" if self.direction == "Right" else "Right"
                self.isDown = True
                time.sleep(1)
            else:  # 已经下移过一次，按direction移动一次
                logger.info("地图移动")
                if self.direction == "Right":
                    context.run_task("FD_SwipeMapToRight")
                else:
                    context.run_task("FD_SwipeMapToLeft")
                self.isDown = False
                time.sleep(1)
        else:  # 未达到边界，地图按当前direction继续移动一次
            logger.info("地图移动")
            if self.direction == "Right":
                context.run_task("FD_SwipeMapToRight")
            else:
                context.run_task("FD_SwipeMapToLeft")
            self.isDown = False
            time.sleep(2)

    # 检测目标是否还存在
    def checkTargetExist(
        self, context: Context, taskType: str, threshold: float
    ) -> bool:

        if taskType in ["monster_boss", "planet"]:
            # 这两个任务直接可以从左上角开始检测
            self.swipeMapToLeftTop(context)

        flag = True
        # 检查是否存在目标
        while flag:
            targetList = self.GetTaskTargetList(context, taskType, threshold)
            if self.exploreNums > 0:
                if taskType == "planet":
                    time.sleep(1)
                    if len(self.planetList) < 4:
                        # 获取星球的名字
                        box = targetList[0].box
                        btn = context.tasker.controller.post_click(
                            box[0] + box[2] // 2, box[1] + box[3] // 2
                        )
                        time.sleep(2)  # 有动画，需要停顿下才能识别
                        planetName = context.run_recognition(
                            "GetPlanetName",
                            context.tasker.controller.post_screencap().wait().get(),
                            pipeline_override={
                                "GetPlanetName": {
                                    "recognition": "OCR",
                                    "roi": [195, 429, 329, 101],
                                    "timeout": 2000,
                                }
                            },
                        )
                        if planetName and planetName.filterd_results:
                            logger.info(
                                f"识别到星球名称: {planetName.filterd_results[0].text}, 已探索星球列表: {self.planetList}"
                            )
                            self.GetTaskTargetList(context, "monster_planet", 0.82)
                            if planetName.filterd_results[0].text in self.planetList:
                                if self.exploreNums == 0:
                                    logger.info(f"该星球已发现过且已无小怪，请继续探索")
                                    context.run_task("BackText")  # 返回地图并移动
                                    self.swipeMap(context)
                                else:
                                    # 该星球已发现过，但是仍有怪物未清除
                                    flag = False
                            else:
                                if self.exploreNums == 0:
                                    logger.info(f"该星球已无小怪，请继续探索")
                                    context.run_task("BackText")  # 返回地图并移动
                                    self.swipeMap(context)
                                else:
                                    logger.info("发现新星球")
                                    flag = False
                                self.planetList.append(
                                    planetName.filterd_results[0].text
                                )
                    else:
                        # 已经探索过4个星球，结束探索
                        logger.info("已探索4个星球，结束探索")
                        flag = False
                        return False
                else:
                    logger.info(f"已找到{self.exploreNums}个探索目标")
                    flag = False
            else:
                logger.info(f"未找到探索目标，将移动地图再次搜索")
                self.swipeMap(context)
        return True

    def closeUnionMsgBox(self, context: Context) -> bool:
        img = context.tasker.controller.post_screencap().wait().get()
        opened = context.run_recognition(
            "checkUnionMsgBox",
            img,
            pipeline_override={
                "checkUnionMsgBox": {
                    "recognition": "TemplateMatch",
                    "template": "fight/time_space_domain/unionMsgOpened.png",
                    "roi": [91, 1042, 80, 80],
                    "threshold": 0.8,
                }
            },
        )
        if opened:
            context.run_task("TSD_closeUnionMsgBox")
            logger.info("关闭联盟聊天窗口")
        else:
            logger.info("联盟聊天窗口未打开")
        return True

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        self.fleet_nums = json.loads(argv.custom_action_param)["fleet_nums"]
        taskList: dict = {
            "explore": {
                "name": "探索废墟",
                "enabled": context.get_node_data("TSD_CheckExploreTask")["enabled"],
                "threshold": 0.91,
            },
            "monster": {
                "name": "清理主地图小怪",
                "enabled": context.get_node_data("TSD_CheckMonsterTask")["enabled"],
                "threshold": 0.8,
            },
            "monster_boss": {
                "name": "清理主地图Boss",
                "enabled": context.get_node_data("TSD_CheckMonsterBossTask")["enabled"],
                "threshold": 0.8,
            },
            "planet": {
                "name": "清理星球小怪",
                "enabled": context.get_node_data("TSD_CheckMonsterPlanetTask")[
                    "enabled"
                ],
                "threshold": 0.9,
            },
            # "exploit": json.loads(argv.custom_action_param)["exploit"] # 占位
        }

        context.run_task("ClickCenterBelow_500ms")

        # 先关闭联盟聊天窗口，避免干扰
        self.closeUnionMsgBox(context)

        # 获取所有舰队战力
        self.getAllFleetPower(context)
        logger.info(f"当前选择出战舰队数量：{self.fleet_nums}")
        logger.info(f"当前舰队战力：{ self.powerList }")
        logger.info(f"最高战力舰队：{ self.highestFleet }")
        logger.info(f"选择出战舰队列表：{ self.fight_fleets }")

        # 所有舰队返回
        self.returnFleets(context)

        # # 开始探索
        for key in taskList:
            if taskList[key]["enabled"] == True:
                logger.info(f"开始执行【{ taskList[key]['name'] }】任务")
                while self.checkTargetExist(context, key, taskList[key]["threshold"]):
                    self.runTask(context, key)
                logger.info(f"【{ taskList[key]['name'] }】任务执行完毕")
            else:
                logger.info(f"未开启【{ taskList[key]['name'] }】任务")
                continue

        logger.info("所有任务完成！")
        send_message("外域探索", "外域探索所有任务完成！")
        return CustomAction.RunResult(success=True)
