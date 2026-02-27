# 新年迷宫（东方的归途） interface的entry： Eastern_Start
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger, send_message

from action.fight import fightUtils
from action.fight import fightProcessor

import json, time, re

boss_x = 360
boss_y = 680


@AgentServer.custom_action("Eastern_Activity")
class Eastern_Activity(CustomAction):
    def __init__(self):
        super().__init__()
        self.layers = 1
        self.received = False
        self.received_count = 0

    def initialize(self, context: Context):
        self.__init__()
        logger.info("初始化完成")
        # 检查当前层数
        context.run_task("Fight_ReturnMainWindow")
        RunResult = context.run_task("Fight_CheckLayer")
        if RunResult.nodes:
            self.layers = fightUtils.extract_num_layer(
                RunResult.nodes[0].recognition.best_result.text
            )

    def Check_CurrentLayers(self, context: Context):
        tempLayers = fightUtils.handle_currentlayer_event(context)
        self.layers = tempLayers
        return True

    def handle_ClearMonster(self, context: Context):
        # 处理可能出现的保险
        context.run_task("Eastern_Handoff")
        context.run_task(
            "Eastern_Fight_clearCurrentLayer",
            pipeline_override={
                "Eastern_Fight_clearCurrentLayer": {
                    "custom_action_param": {"layers": self.layers}
                }
            },
        )
        context.run_task("Fight_OpenedDoor")

    def handle_interrupt_event(self, context: Context):
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_FindRespawn", image).hit:
            logger.info("检测到死亡， 尝试小SL")
            fightUtils.Saveyourlife(context)
            fightUtils.cast_magic("水", "治疗术", context)
            fightUtils.cast_magic("土", "石肤术", context)
            return False

        if context.run_recognition(
            "Eastern_Inter_Confirm_Success",
            image,
        ).hit:
            logger.info("检测到卡剧情, 本层重新探索")
            context.run_task("Eastern_Inter_Confirm_Success")
            return False

        if context.run_recognition(
            "Eastern_Inter_Confirm_Fail",
            image,
        ).hit:
            if context.run_recognition("Fight_FindRespawn", image).hit:
                logger.info("检测到死亡， 尝试小SL")
                fightUtils.Saveyourlife(context)
                fightUtils.cast_magic("水", "治疗术", context)
                fightUtils.cast_magic("土", "石肤术", context)
                return False
            logger.info("检测到卡离开, 本层重新探索")
            context.run_task("Eastern_Inter_Confirm_Fail")
            return False

        # 检测卡返回
        if context.run_recognition("BackText", image).hit:
            logger.info("检测到卡返回, 本层重新探索")
            context.run_task("Fight_ReturnMainWindow")
            return False

        return True

    def get_drug_name(self, name):
        match = re.search(r"/([^/.]+)\.", name)

        if match:
            result = match.group(1)
            return result
        else:
            return ""

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # logger.info("成功进入迷宫")
        self.initialize(context)
        drugs = context.get_node_data("Select_Drug_Next")["recognition"]["param"][
            "template"
        ][0]
        self.drug = self.get_drug_name(drugs)
        # logger.info(fightUtils.openBagAndUseItem("wages", False, context))
        while self.layers < 7:
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)

            # 检查当前层数, 确保不是0层
            if not self.Check_CurrentLayers(context):
                return CustomAction.RunResult(success=False)
            logger.info(f"开始探索 {self.layers} 层.")

            if self.layers == 1:
                if context.run_recognition(
                    "Eastern_enter_confirm",
                    context.tasker.controller.post_screencap().wait().get(),
                    pipeline_override={
                        "Eastern_enter_confirm": {
                            "recognition": "OCR",
                            "expected": "电池",
                            "roi": [97, 646, 182, 50],
                            "threshold": 0.7,
                        }
                    },
                ).hit:
                    for _ in range(4):
                        context.run_task("Eastern_Talk_Confirm")
                        time.sleep(0.02)
                self.received_count += 1
                logger.info("领取工资")
                if not self.received:
                    context.run_task("Eastern_Receive_Salary")
                    self.received = True

                if self.received_count > 1:
                    context.run_task("Bag_Open")
                    if not fightUtils.findItem("钞票", False, context):
                        logger.info("没领到工资，再领一次")
                        context.run_task("Eastern_Receive_Salary")
                        if self.received_count > 5:
                            send_message(
                                "MaaGB", "多次领取工资失败，请冒险者大人回来重启任务！"
                            )
                            logger.info("多次领取工资失败，请冒险者大人回来重启任务！")
                            context.run_task("Fight_ReturnMainWindow")
                            return CustomAction.RunResult(success=False)
                    context.run_task("Fight_ReturnMainWindow")
                context.run_task("Fight_OpenedDoor")
            elif self.layers < 5:
                self.handle_ClearMonster(context)
                if self.layers == 4:
                    context.run_task("Eastern_Enter_Market")
                    if context.run_recognition(
                        "Eastern_Enter_Market_Check",
                        context.tasker.controller.post_screencap().wait().get(),
                    ).hit:
                        logger.info("进入超市")
                        logger.info("开始购买年货.")
                        for i in range(5, 2, -1):
                            context.run_task(
                                "Eastern_Buy_One",
                                pipeline_override={
                                    "Eastern_Buy_One": {
                                        "template": f"fight/eastern/shop{i}.png"
                                    },
                                    "Eastern_Buy_One_Confirm": {"next": ["BackText"]},
                                },
                            )
                        for i in range(1, 3):
                            context.run_task(
                                "Eastern_Buy_All",
                                pipeline_override={
                                    "Eastern_Buy_All": {
                                        "template": f"fight/eastern/shop{i}.png"
                                    }
                                },
                            )
                            if AddButtonRecoDetail := context.run_recognition(
                                "Eastern_Buy_All_AddButton",
                                context.tasker.controller.post_screencap().wait().get(),
                            ):
                                if AddButtonRecoDetail.hit:
                                    box = AddButtonRecoDetail.best_result.box
                                    for _ in range(30):
                                        context.tasker.controller.post_click(
                                            box[0] + box[2] // 2,
                                            box[1] + box[3] // 2,
                                        ).wait()
                                        time.sleep(0.02)
                                context.run_task("Eastern_Buy_One_Confirm")
                        context.run_task("Eastern_Enter_Train")
                    logger.info("离开超市")
                    context.run_task("Fight_OpenedDoor")
            elif self.layers == 5:
                # logger.info("boss层")
                if context.run_recognition(
                    "Eastern_enter_confirm",
                    context.tasker.controller.post_screencap().wait().get(),
                    pipeline_override={
                        "Eastern_enter_confirm": {
                            "recognition": "OCR",
                            "expected": "黄牛",
                            "roi": [96, 628, 156, 75],
                            "threshold": 0.7,
                        }
                    },
                ).hit:
                    for _ in range(3):
                        context.run_task("Eastern_Talk_Confirm")
                        time.sleep(0.02)
                fightUtils.cast_magic_special("摄魂魔法", context)
                fightUtils.cast_magic_special("记忆标本", context)
                fightUtils.openBagAndUseItem(
                    "记忆标本", True, context, True, boss_x, boss_y
                )
                fightUtils.openBagAndUseItem("充电器", True, context)
                fightUtils.cast_magic_special("摄魂魔法", context)
                fightUtils.cast_magic_special("记忆标本", context)
                fightUtils.openBagAndUseItem(
                    "记忆标本", True, context, True, boss_x, boss_y
                )
                if self.drug == "电能试剂":
                    fightUtils.openBagAndUseItem("电能试剂", True, context)
                    fightUtils.cast_magic_special("摄魂魔法", context)
                    fightUtils.cast_magic_special("记忆标本", context)
                    fightUtils.openBagAndUseItem(
                        "记忆标本", True, context, True, boss_x, boss_y
                    )
                elif self.drug == "秘法之水":
                    for _ in range(5):
                        fightUtils.openBagAndUseItem("秘法之水", True, context)
                        fightUtils.cast_magic_special("摄魂魔法", context)
                        fightUtils.cast_magic_special("记忆标本", context)
                        fightUtils.openBagAndUseItem(
                            "记忆标本", True, context, True, boss_x, boss_y
                        )

                fightUtils.openBagAndUseItem("灵魂", True, context)

                context.run_task("Eastern_Buy_Ticket")
                context.run_task("Eastern_Enter_Train")
            elif self.layers == 6:
                logger.info("开始结算")
                context.run_task("Eastern_Leave")
                context.run_task("Eastern_Leave_holl")

                while not context.run_recognition(
                    "Eastern_cacl_count",
                    context.tasker.controller.post_screencap().wait().get(),
                ).hit:
                    if context.tasker.stopping:
                        logger.info("检测到停止任务, 开始退出agent")
                        return CustomAction.RunResult(success=False)

                    for _ in range(3):
                        context.run_task("Eastern_Talk_Confirm")
                        time.sleep(0.02)
                image = context.tasker.controller.post_screencap().wait().get()
                count = context.run_recognition("Eastern_get_count", image)
                if count.hit:
                    count = fightUtils.extract_num(count.filtered_results[0].text)
                    logger.info(f"获得红包 {count} 个。")

                context.run_task("BackText")
                time.sleep(2)
                context.run_task("AlchemyReward")

                return CustomAction.RunResult(success=True)

            # 检查是否触发中断事件

            if not self.handle_interrupt_event(context):
                continue

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Eastern_Fight_clearCurrentLayer")
class Eastern_Fight_clearCurrentLayer(CustomAction):
    def __init__(self):
        super().__init__()
        self.fightProcessor = fightProcessor.FightProcessor()

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # 读取传入的层数参数（兼容 dict/对象）
        layers_arg = json.loads(argv.custom_action_param)["layers"]
        if layers_arg is not None:
            try:
                # 作为变量传入处理器，后续可按需使用
                self.fightProcessor.layers = layers_arg
            except Exception:
                pass

        self.fightProcessor.grid_count = 40
        self.fightProcessor.clearCurrentLayer(context, isclearall=True)
        return CustomAction.RunResult(success=True)
