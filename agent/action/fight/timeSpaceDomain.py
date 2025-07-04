from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.define import RecognitionDetail

from utils import logger
from action.fight import fightUtils

import time
import re
    
fleetRoiList: dict = {
    "奥鲁维":[130, 199, 60, 51],
    "卡纳斯":[227, 200, 63, 50],
    "游荡者":[327, 200, 64 ,49],
    "深渊":[425, 199, 64, 53]
}

highestFleet = "" # 最高战力舰队
exploreNums = 1 # 剩余需要探索的次数

@AgentServer.custom_action("TSD_explore")
class TSD_explore(CustomAction):
    
    # 获取舰队战力值
    def getAllFleetPower(self, context: Context) -> dict:
        fleetPowerRoiList: dict = {
            "奥鲁维":[62, 123, 139, 28],
            "卡纳斯":[207, 123, 150, 27],
            "游荡者":[361, 124, 151, 26],
            "深渊":[515, 120, 140, 32]
        }
        global highestFleet
        img = context.tasker.controller.post_screencap().wait().get()
        powerList: dict = {}
        for key in fleetPowerRoiList:
            nums = context.run_recognition(
                "TSD_getPowerNumber",
                img,
                pipeline_override = {
                    "TSD_getPowerNumber":{
                        "roi": fleetPowerRoiList[key]
                    }
                }  
            )
            if nums:
                powerNumber = fightUtils.extract_num(nums.filterd_results[0].text)
                powerList[key] = powerNumber
            else:
                powerList[key] = 0
        highestFleet = self.comparePower(powerList)
        return powerList
    
    # 获取最高战力舰队
    def comparePower(self, powerList: dict) -> str:
        name = "奥鲁维"
        power = powerList[name]
        for name in powerList:
            if power < powerList[name]:
                power = powerList[name]
                name = name
        return name
    # 检查舰队状态，是否都是空闲
    def checkAllFleetStatus(self, context: Context) -> int:
        img = context.tasker.controller.post_screencap().wait().get()
        fleetStatus = context.run_recognition(
            "checkAllFleetStatus",
            img,
            pipeline_override={
                    "checkAllFleetStatus": {
                        "recognition": "TemplateMatch",
                        "template": "fight/timeSpaceDomain/fleetFree.png",
                        "roi": [109, 182, 397, 95],
                        "threshold": 0.8,
                    }
            }
        )
        if fleetStatus and fleetStatus.filterd_results:
            return len(fleetStatus.filterd_results)
        else:
            return 0
    
    # 返回所有舰队
    def returnFleets(self, context: Context) -> bool:
        while True:
            img = context.tasker.controller.post_screencap().wait().get()
            for key in fleetRoiList:
                status = context.run_recognition(
                    "TSD_checkFreeFleet",
                    img,
                    pipeline_override={
                        "TSD_checkFreeFleet": {
                            "roi": fleetRoiList[key]
                        }
                    },
                )
                if not status:
                    time.sleep(1)
                    logger.info(f"正在返回{key}舰队")
                    context.run_task("TSD_ClickFleet",
                        pipeline_override={
                            "TSD_ClickFleet":{
                                "target": fleetRoiList[key]
                            }       
                    })
                    context.run_task("TSD_ReturnFleet",
                        pipeline_override={
                            "TSD_checkFreeFleet":{
                                "roi": fleetRoiList[key]
                            },
                            "TSD_checkTargetFleet":{
                                "roi": fleetRoiList[key]
                            },
                            "TSD_checkTargetFlying":{
                                "roi": fleetRoiList[key]
                            }
                    })                    
                    time.sleep(1)
                else:
                    logger.info(f"{key}舰队已返回,无需操作")
            if nums := self.checkAllFleetStatus(context) == 4 :
                logger.info("所有舰队已返回")
                break;        
        return True
    # 获取当前屏幕的探索目标
    def GetExploreTargetList(self, context: Context):
        global exploreNums
        img = context.tasker.controller.post_screencap().wait().get()
        exploreList = context.run_recognition(
            "GetExploreTargetList",
            img,
            pipeline_override={
                    "GetExploreTargetList": {
                        "recognition": "TemplateMatch",
                        "template": "fight/timeSpaceDomain/exploreTarget.png",
                        "roi": [12, 268, 693, 872],
                        "threshold": 0.91,
                    }
                }
        )
        if exploreList and exploreList.filterd_results:
            exploreNums = len(exploreList.filterd_results)
            return exploreList.filterd_results
        else: 
            exploreNums = 0
            return []
    
    # 按列表执行事件
    def runExplore(self, context: Context, exploreList: []) -> bool:
        global exploreNums
        for explore in exploreList:
            box = explore.box
            btn = context.tasker.controller.post_click(
                box[0] + box[2] // 2, box[1] + box[3] // 2
            )
            time.sleep(2)
            task1 = context.run_task("TSD_Investigate")
            if task1.status.succeeded == False:
                context.run_task("BackText")
                return False
            exploreNums -= 1
            time.sleep(1)
        return True
    
    def checkBoundary(self, context: Context, direction: str) -> bool:
        boundaryRoiDict:dict = {
            "LeftTop":[12, 268, 137, 147],
            "Right":[597, 272, 96, 871],
            "Left":[14, 275, 116, 766],
            "RightBottom":[590, 1052, 117, 102]
        }
        img = context.tasker.controller.post_screencap().wait().get()
        boundaryList = context.run_recognition(
            "GridCheckTargetBoundary",
            img,
            pipeline_override={
                "GridCheckTargetBoundary":{
                    "recognition": "TemplateMatch",
                    "template": f"fight/timeSpaceDomain/boundary{direction}.png",
                    "roi": boundaryRoiDict[direction],
                    "threshold": 0.92
                }
            }
        )
        if boundaryList and  boundaryList.filterd_results:
            return True
        return False
    # 检测目标是否还存在
    def checkTargetExist(self, context: Context) -> bool:
        global exploreNums 
        
        # 先判断当前屏幕有无目标，没有的话再移动至左上角开始检查
        self.GetExploreTargetList(context)
        if exploreNums > 0 :
            return True
        else:
            while True: # 将地图移动至左上角
                tempPath = "fight/timeSpaceDomain/boundaryLeftTop.png"
                if self.checkBoundary(context, "LeftTop"):
                    break
                else:
                    context.run_task("FD_SwipeMapMiddleToTopLeft")
                time.sleep(1)
            logger.info("地图已移动至左上角")

        flag = True
        isDown = False # 判断是否下移过一次
        direction = "Right"
        # 检查是否存在目标（从左上角向右检测）
        while flag:
            self.GetExploreTargetList(context)
            if exploreNums > 0 :
                logger.info(f"已找到{exploreNums}个探索目标")
                flag = False
            else :
                logger.info(f"未找到探索目标，将移动地图再次搜索")
                if self.checkBoundary(context, direction):
                    logger.info(f"地图{direction}边界")
                    if self.checkBoundary(context, "RightBottom"):
                        logger.info("已到达地图边界")
                        flag = False
                        return False
                    elif not isDown: # 未达到右下角，地图下移一次
                        logger.info("地图下移")
                        context.run_task("FD_SwipeMapToDown")
                        direction = "Left" if direction == "Right" else "Right"
                        isDown = True
                    else: # 已经下移过一次，按direction移动一次
                        logger.info("地图移动")
                        if direction =="Right":
                            context.run_task("FD_SwipeMapToRight")
                        else :
                            context.run_task("FD_SwipeMapToLeft")
                        isDown = False
                else: # 未达到边界，地图按当前direction继续移动一次
                    logger.info("地图移动")
                    if direction =="Right":
                        context.run_task("FD_SwipeMapToRight")
                    else :
                        context.run_task("FD_SwipeMapToLeft")
                    isDown = False
        return True

    def closeUnionMsgBox(self, context: Context) -> bool:
        img = context.tasker.controller.post_screencap().wait().get()
        opened = context.run_recognition(
            "checkUnionMsgBox", 
            img,
            pipeline_override={
                "checkUnionMsgBox": {
                    "recognition": "TemplateMatch",
                    "template": "fight/timeSpaceDomain/unionMsgOpened.png",
                    "roi": [91, 1042, 80, 80],
                    "threshold": 0.8
                }
            },
        )
        if opened :
            context.run_task("TSD_closeUnionMsgBox")
            logger.info("关闭联盟聊天窗口")
        else:
            logger.info("联盟聊天窗口未打开")
        return True
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        global exploreNums
        
        # 先关闭联盟聊天窗口，避免干扰
        self.closeUnionMsgBox(context)
        
        # 获取所有舰队战力
        powerList = self.getAllFleetPower(context)
        logger.info(f"当前探索战力：{powerList}，最高战力舰队：{highestFleet}")
        
        # 所有舰队返回
        self.returnFleets(context)
        
        # 开始探索
        while self.checkTargetExist(context) :
            lists = self.GetExploreTargetList(context)
            self.runExplore(context, lists)
        
        
        logger.info("探索完成！")
        return CustomAction.RunResult(success=True)