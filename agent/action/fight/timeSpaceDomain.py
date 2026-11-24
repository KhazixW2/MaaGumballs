from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from utils import logger, send_message
from action.fight import fightUtils
from action.fight.foreignDomainUtils import foreignDomainUtils

import time
import json

# 星球固定为 4 个, 收集完即视为星球任务完成
PLANET_TOTAL = 4


@AgentServer.custom_action("TSD_explore")
class TSD_explore(CustomAction):

    def __init__(self):
        super().__init__()

        self.powerList: dict = {}  # 舰队战力
        self.highestFleet = ""  # 最高战力舰队
        self.exploreNums = 1  # 剩余需要探索的次数
        self.fleet_nums = 4  # 默认出战舰队数量
        self.fight_fleets = []  # 根据选择的舰队数量按战力大小排列的舰队列表
        self.fleet_list = []  # 当前可用的舰队列表
        self.planetList: list = []  # 记录探索的星球

        self.FDUtils = foreignDomainUtils()

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
            if nums.hit:
                powerNumber = fightUtils.extract_num(nums.filtered_results[0].text)
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
        if exploreList.hit:
            self.exploreNums = len(exploreList.filtered_results)
            return exploreList.filtered_results
        else:
            self.exploreNums = 0
            return []

    # 按列表执行事件
    def runTask(
        self,
        context: Context,
        taskType: str,
    ) -> bool | CustomAction.RunResult:
        taskEntry: dict = {
            "explore": {
                "taskName": "TSD_Investigate",
                "pipeline_override": {
                    "TSD_SelectFreeFleetInList": {"expected": self.fleet_list[:1]}
                },
            },
            "monster": {
                "taskName": "TSD_ClearMonster",
                "pipeline_override": {
                    "TSD_SelectFreeFleetInList": {
                        "recognition": "OCR",
                        "expected": self.fleet_list[:1],
                        "roi": [44, 164, 627, 537],
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
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)

            box = explore.box
            btn = context.tasker.controller.post_click(
                box[0] + box[2] // 2, box[1] + box[3] // 2
            ).wait()
            time.sleep(2)
            if not self.checkClickTarget(context, ["调查", "袭击"]):
                # 未点击到目标，证明因为地图移动导致目标位置变化，重新检查目标
                logger.info("未点击到目标，重新检查目标")
                return False
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
            # 目标已被成功处理, 记为一次实质进展
            self.FDUtils.mark_progress()
            self.exploreNums -= 1
            self.fleet_list.append(self.fleet_list.pop(0))  # 轮换舰队顺序
            taskEntry["explore"]["pipeline_override"]["TSD_SelectFreeFleetInList"][
                "expected"
            ] = self.fleet_list[:1]
            taskEntry["monster"]["pipeline_override"]["TSD_SelectFreeFleetInList"][
                "expected"
            ] = self.fleet_list[:1]
            # logger.info(f"出战舰队顺序: {self.fleet_list}")

            if inPlanet and self.exploreNums == 0:
                # 星球小怪任务完成后，返回地图
                logger.info("该星球已无小怪，返回地图")
                context.run_task("BackText")
            time.sleep(1)
        return True

    def checkClickTarget(self, context: Context, target: list) -> bool:
        targetList = context.run_recognition(
            "checkClickTarget",
            context.tasker.controller.post_screencap().wait().get(),
            pipeline_override={
                "checkClickTarget": {
                    "recognition": "OCR",
                    "expected": target,
                    "roi": [12, 152, 696, 1120],
                    "threshold": 0.8,
                }
            },
        )
        if targetList.hit:  # 检测到目标
            return True
        return False

    # 检测目标是否还存在(返回 False 表示该任务已无可处理目标)
    def checkTargetExist(
        self, context: Context, taskType: str, threshold: float
    ) -> bool:
        if taskType == "planet" and len(self.planetList) >= PLANET_TOTAL:
            # 星球不会消失, 靠"已完成星球数量"判断任务结束
            logger.info(f"已完成 {len(self.planetList)} 个星球, 星球任务结束")
            return False

        flag = True
        # 检查是否存在目标
        while flag:
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return False
            targetList = self.GetTaskTargetList(context, taskType, threshold)
            if self.exploreNums > 0:
                if taskType == "planet":
                    time.sleep(1)
                    if len(self.planetList) < PLANET_TOTAL:
                        # 获取星球的名字
                        box = targetList[0].box
                        btn = context.tasker.controller.post_click(
                            box[0] + box[2] // 2, box[1] + box[3] // 2
                        ).wait()
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
                        if planetName.hit:
                            logger.info(
                                f"识别到星球名称: {planetName.filtered_results[0].text}, 已探索星球列表: {self.planetList}"
                            )
                            self.GetTaskTargetList(context, "monster_planet", 0.82)
                            if planetName.filtered_results[0].text in self.planetList:
                                if self.exploreNums == 0:
                                    logger.info(f"该星球已发现过且已无小怪，请继续探索")
                                    context.run_task("BackText")  # 返回地图并移动
                                    if not self.FDUtils.swipeMap(
                                        context, expect_target=True
                                    ):
                                        # 连续多圈都没找到下一个星球, 放弃
                                        logger.warning(
                                            f"地图扫描完毕, 仅找到 {len(self.planetList)} 个星球: {self.planetList}"
                                        )
                                        return False
                                else:
                                    # 该星球已发现过，但是仍有怪物未清除
                                    flag = False
                            else:
                                if self.exploreNums == 0:
                                    logger.info(f"该星球已无小怪，请继续探索")
                                    context.run_task("BackText")  # 返回地图并移动
                                    # 完成清理，记录星球名称
                                    self.planetList.append(
                                        planetName.filtered_results[0].text
                                    )
                                    # 新星球探索完毕, 记为一次实质进展
                                    self.FDUtils.mark_progress()
                                    if not self.FDUtils.swipeMap(
                                        context, expect_target=True
                                    ):
                                        logger.warning(
                                            f"地图扫描完毕, 仅找到 {len(self.planetList)} 个星球: {self.planetList}"
                                        )
                                        return False
                                else:
                                    logger.info("发现新星球")
                                    flag = False
                    else:
                        # 已经探索过的星球数量达到上限，结束探索
                        logger.info(f"已探索 {PLANET_TOTAL} 个星球，结束探索")
                        flag = False
                        return False
                else:
                    logger.info(f"已找到{self.exploreNums}个探索目标")
                    flag = False
            else:
                logger.info(f"未找到探索目标，将移动地图再次搜索")
                # 星球一定存在于地图上, 空圈只是这轮漏识别, 应重扫;
                # 小怪/废墟/ Boss 处理完就消失, 整圈没有即任务完成
                if not self.FDUtils.swipeMap(context, expect_target=False):
                    # 已经完整探索一遍未发现目标，结束任务
                    flag = False
                    return False
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
        self.FDUtils.closeUnionMsgBox(context)

        # 获取所有舰队战力
        self.getAllFleetPower(context)
        logger.info(f"当前选择出战舰队数量：{self.fleet_nums}")
        logger.info(f"当前舰队战力：{ self.powerList }")
        logger.info(f"最高战力舰队：{ self.highestFleet }")
        logger.info(f"选择出战舰队列表：{ self.fight_fleets }")

        # 所有舰队返回
        if not self.FDUtils.returnFleets(context):
            return CustomAction.RunResult(success=False)

        # # 开始探索
        for key in taskList:

            if taskList[key]["enabled"] == True:
                logger.info(f"开始执行【{ taskList[key]['name'] }】任务")
                self.fleet_list = (
                    list(self.FDUtils.default_fleets)
                    if key == "explore"
                    else list(self.fight_fleets)
                )  # 如果是探索任务，使用全部舰队；复制一份避免轮换时污染原列表
                # 扫描状态按任务重置, 保证"整圈无进展"能跨 checkTargetExist 调用累计
                self.FDUtils.reset_sweep()
                # 这两个任务需要先定位到右下角再开始扫描
                if key in ["monster_boss", "planet"]:
                    if not self.FDUtils.swipeMapToBottomRight(context):
                        logger.warning(f"【{ taskList[key]['name'] }】地图定位失败")
                        continue
                while self.checkTargetExist(context, key, taskList[key]["threshold"]):
                    if context.tasker.stopping:
                        logger.info("检测到停止任务, 开始退出agent")
                        return CustomAction.RunResult(success=False)
                    self.runTask(context, key)
                logger.info(f"【{ taskList[key]['name'] }】任务执行完毕")
            else:
                logger.info(f"未开启【{ taskList[key]['name'] }】任务")
                continue

        logger.info("所有任务完成！")
        send_message("外域探索", "外域探索所有任务完成！")
        return CustomAction.RunResult(success=True)
