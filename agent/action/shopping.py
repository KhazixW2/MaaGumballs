from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from utils import logger

import json
import time


@AgentServer.custom_action("Shopping")
class Shopping(CustomAction):

    # checkShopListWindows
    def CheckShopListWindows(self, context: Context):
        recoDetail = context.run_recognition(
            "CheckShopListWindows",
            context.tasker.controller.post_screencap().wait().get(),
            pipeline_override={
                "CheckShopListWindows": {
                    "recognition": "OCR",
                    "expected": ["商店列表"],
                    "roi": [133, 165, 449, 210],
                    "timeout": 3000,
                }
            },
        )
        return recoDetail

    # 进入指定商店
    def EnterShop(self, context: Context, ShopName: str):
        img = context.tasker.controller.post_screencap().wait().get()
        recoDetail = context.run_recognition(
            "EnterShop",
            img,
            pipeline_override={
                "EnterShop": {
                    "recognition": "OCR",
                    "expected": [ShopName],
                    "roi": [32, 185, 637, 735],
                    "timeout": 3000,
                }
            },
        )
        # Click boxCenter
        if recoDetail:
            box = recoDetail.best_result.box
            context.tasker.controller.post_click(
                int(box[0] + box[2] / 2), int(box[1] + box[3] / 2)
            )
        time.sleep(1)

        return recoDetail

    # 商人冈布奥奖励检查
    def Shop_ShoppingRewards_Check(self, context: Context):
        # 检查是否触发商人奖励
        img = context.tasker.controller.post_screencap().wait().get()
        recoDetail = context.run_recognition(
            "Shop_ShoppingRewards_Check",
            img,
            pipeline_override={
                "Shop_ShoppingRewards_Check": {
                    "recognition": "OCR",
                    "expected": "商人冈布奥",
                    "roi": [60, 388, 628, 496],
                    "threshold": 0.8,
                }
            },
        )
        return recoDetail

    # 金币商店
    def Shop_GoldCoins(self, context: Context):

        # 进入商店
        SwipeCount = 5
        while SwipeCount > 0:
            img = context.tasker.controller.post_screencap().wait().get()
            recoDetail = context.run_recognition(
                "Shop_FindGoldCions_reco",
                img,
                pipeline_override={
                    "Shop_FindGoldCions_reco": {
                        "recognition": "TemplateMatch",
                        "template": "Shop/GoldCoins.png",
                        "roi": [65, 334, 610, 686],
                        "threshold": 0.8,
                    }
                },
            )

            if recoDetail:
                logger.info(f"找到商品{len(recoDetail.all_results)}个, 开始购物")
                for result in recoDetail.all_results:
                    if result.score < 0.8:
                        continue
                    box = result.box
                    context.tasker.controller.post_click(
                        int(box[0] + box[2] / 2) + 65, int(box[1] + box[3] / 2) - 85
                    ).wait()
                    time.sleep(1)
                    context.run_task("ConfirmButton")
                    if self.Shop_ShoppingRewards_Check(context):
                        context.run_task("Shop_ShoppingRewards")

            context.run_task("SwipeShopList")
            SwipeCount -= 1

        # 返回商店列表
        if not self.CheckShopListWindows(context):
            context.run_task("BackText")
        return True

    # 天空商店
    def Shop_RuinCoins(self, context: Context):

        # 进入天空商店购物
        SwipeCount = 5
        while SwipeCount > 0:
            img = context.tasker.controller.post_screencap().wait().get()
            recoDetail = context.run_recognition(
                "Shop_RuinCoins_reco",
                img,
                pipeline_override={
                    "Shop_RuinCoins_reco": {
                        "recognition": "TemplateMatch",
                        "template": "Shop/RuinCoinsIcon.png",
                        "roi": [65, 334, 610, 686],
                        "threshold": 0.8,
                    }
                },
            )

            if recoDetail:
                logger.info(f"找到商品{len(recoDetail.all_results)}个, 开始购物")
                for result in recoDetail.all_results:
                    if result.score < 0.8:
                        continue
                    box = result.box
                    context.tasker.controller.post_click(
                        int(box[0] + box[2] / 2) + 40, int(box[1] + box[3] / 2) - 80
                    )
                    time.sleep(0.5)
                    context.run_task("ConfirmButton")

            context.run_task("SwipeShopList")
            SwipeCount -= 1

        # 检查是否存在符石商店
        img = context.tasker.controller.post_screencap().wait().get()
        recoDetail = context.run_recognition(
            "Shop_Runestone_reco",
            img,
            pipeline_override={
                "Shop_Runestone_reco": {
                    "recognition": "OCR",
                    "expected": ["符石"],
                    "roi": [44, 835, 470, 228],
                },
            },
        )

        # 符石商店购物
        if recoDetail:
            context.run_task("Shop_Runestone")

        # 返回商店列表
        if not self.CheckShopListWindows(context):
            context.run_task("BackText")

        return True

    # 佣兵商店
    def Shop_Mercenary(self, context: Context):
        # 检查是否存在佣兵商店
        img = context.tasker.controller.post_screencap().wait().get()
        recoDetail = context.run_recognition(
            "Shop_Mercenary_reco",
            img,
            pipeline_override={
                "Shop_Mercenary_reco": {
                    "recognition": "OCR",
                    "expected": ["碎片兑换"],
                    "roi": [84, 224, 554, 297],
                },
            },
        )

        # 佣兵商店购物
        if recoDetail:
            context.run_task("Shop_Mercenary")

        # 返回商店列表
        if not self.CheckShopListWindows(context):
            context.run_task("BackText")

        return True

    # UnionShop
    def UnionShop(self, context: Context):
        img = context.tasker.controller.post_screencap().wait().get()

    # TravelShop
    def TravelShop(self, context: Context):
        img = context.tasker.controller.post_screencap().wait().get()

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        taskList: dict = json.loads(argv.custom_action_param)
        print(taskList)
        if not taskList:
            return CustomAction.RunResult(success=True)

        # 进入商店列表
        context.run_task("ClickSwitchShopButton")

        if self.CheckShopListWindows(context):
            # 进入商店
            logger.info("进入商店列表成功")

            # execute task
            logger.info("开始旅行商人购物")
            self.EnterShop(context, "旅行商人")
            self.Shop_GoldCoins(context)

            logger.info("开始佣兵营地购物")
            self.EnterShop(context, "佣兵营地")
            self.Shop_Mercenary(context)

            logger.info("开始天空商人购物")
            self.EnterShop(context, "天空集市")
            self.Shop_RuinCoins(context)

        else:
            logger.info("进入商店失败，请检查商店列表")
            return CustomAction.RunResult(success=False)

        logger.info("购物完成，返回大地图")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("SkillShop_Shopping")
class SkillShop_Shopping(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        # 技能商店开始购物
        if recoDetail := context.run_recognition(
            "SkillShop_Reco",
            context.tasker.controller.post_screencap().wait().get(),
            pipeline_override={
                "SkillShop_Reco": {
                    "recognition": "TemplateMatch",
                    "template": "items/scroll/",
                    "roi": [65, 334, 610, 686],
                    "threshold": 0.8,
                }
            },
        ):
            logger.info(f"找到商品{len(recoDetail.all_results)}个, 开始购物")
            for result in recoDetail.all_results:
                if result.score < 0.8:
                    continue
                box = result.box
                context.tasker.controller.post_click(
                    box[0] + box[2] // 2, box[1] + box[3] // 2
                )
                time.sleep(0.5)
                context.run_task("ConfirmButton_500ms")
        context.run_task("Fight_ReturnMainWindow")
        return CustomAction.RunResult(success=True)
