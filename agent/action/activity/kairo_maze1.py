from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger
import time


@AgentServer.custom_action("Kairo_Difficulty3_Start")
class Kairo_Difficulty3_Start(CustomAction):
    """
    一个按顺序执行多个预定义Maa Pipeline节点的自定义动作。
    """

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        """
        执行自定义动作的核心逻辑。
        :param context: Maa提供的上下文对象，用于与Maa框架交互。
        :param argv: 动作的参数（如果JSON中配置了）。
        :return: CustomAction.RunResult，表示动作的成功或失败。
        """
        logger.info("开始探索开罗迷宫执行。")

        # 定义需要顺序执行的任务列表
        """ 
        tasks_to_execute = [
              
        ]
        """

        tasks_to_execute = [
            ("Kairo_Enter_Cave1", "进入洞穴1"),
            ("Kairo_Return_Home", "返回家园"),
            ("Kairo_Enter_Pub", "进入酒馆"),
            ("Kairo_SearchingMale", "找男冒险者并招募"),
            ("Kairo_SearchingMale", "找男冒险者并招募"),
            ("Kairo_SearchingMale", "找男冒险者并招募"),
            ("BackText_500ms", "出酒馆"),
            ("Kairo_Return_Hotel", "住旅馆并返回大地图"),
            ("Kairo_Enter_Cave1", "进入洞穴1"),
            ("Kairo_Enter_Cave2", "进入洞穴2"),
            ("Kairo_Return_Home", "返回家园"),
            ("Kairo_Return_Hotel", "住旅馆并返回大地图"),
            ("Kairo_Enter_Cave1", "进入洞穴1"),
            ("Kairo_Enter_Cave2", "进入洞穴2"),
            ("Kairo_Return_Home", "返回家园"),
            ("Kairo_Return_Hotel", "住旅馆并返回大地图"),
            ("Kairo_Enter_Cave1", "进入洞穴1"),
            ("Kairo_Enter_Cave2", "进入洞穴2"),
            ("Kairo_Return_Home", "返回家园"),
            ("Kairo_Return_Hotel", "住旅馆并返回大地图"),
            ("Kairo_Enter_Cave1", "进入洞穴1"),
            ("Kairo_Enter_Cave2", "进入洞穴2"),
            ("Kairo_Return_Home", "返回家园"),
            ("Kairo_Enter_WeaponStore", "进武器店"),
            ("Kairo_Choose_HolyMace", "买权杖"),
            ("Kairo_Choose_HolyMace", "买权杖"),
            ("Kairo_Choose_Axe", "买斧子"),
            ("Kairo_Choose_Axe", "买斧子"),
            ("Kairo_Choose_Axe", "买斧子"),
            ("BackText_500ms", "出武器店"),
            ("Kairo_Enter_MonkPromotionStore", "进法师转职商店"),
            ("Kairo_Choose_MonkMedal_4", "买4阶法师转职"),
            ("BackText_500ms", "出来"),                       
            ("Kairo_ViewTeams", "查看队伍并点击第一个角色"),
            ("Kairo_ClickEquipmentBar1", "点武器栏"),
            ("Kairo_Choose_HolyMace", "背包里找到权杖并装备"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickEquipmentBar1", "点武器栏"),
            ("Kairo_Choose_HolyMace", "背包里找到权杖并装备"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickEquipmentBar1", "点武器栏"),
            ("Kairo_Choose_Axe", "背包里找到斧子并装备"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickEquipmentBar1", "点武器栏"),
            ("Kairo_Choose_Axe", "背包里找到斧子并装备"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickEquipmentBar1", "点武器栏"),
            ("Kairo_Choose_Axe", "背包里找到斧子并装备"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickPromotionInterface", "点进进入转职界面"),
            ("Kairo_ClickSwitchMagic", "切换到魔法职业"),
            ("MapSwipeUpToDown", "翻到转职界面底部"),
            ("Kairo_PromoteToMonk_0", "转职为主教"),            
            ("BackText_500ms", "退出角色界面"),
            ("BackText_500ms", "退出队伍界面"),
            ("Kairo_Return_Hotel", "住旅馆并返回大地图"),
            ("Kairo_Enter_Cave3", "进入洞穴3"),
            ("Kairo_Enter_Cave2", "进入洞穴2"),
            ("Kairo_Enter_Cave1", "进入洞穴1"),
            ("Kairo_Return_Home", "返回家园"),
            ("Kairo_Return_Hotel", "住旅馆并返回大地图"),
            ("Kairo_Enter_Cave3", "进入洞穴3"),
            ("Kairo_Enter_Cave2", "进入洞穴2"),
            ("Kairo_Enter_Cave1", "进入洞穴1"),
            ("Kairo_Return_Home", "返回家园"),
            ("Kairo_Enter_ArmorStore", "进防具店"),
            ("Kairo_Choose_Armor", "买神圣铠甲"),
            ("Kairo_Choose_Armor", "买神圣铠甲"),
            ("Kairo_Choose_Armor", "买神圣铠甲"),
            ("Kairo_Choose_Armor", "买神圣铠甲"),
            ("Kairo_Choose_Armor", "买神圣铠甲"),
            ("BackText_500ms", "出防具店"),                      
            ("Kairo_ViewTeams", "查看队伍并点击第一个角色"),
            ("Kairo_ClickEquipmentBar2", "点防具栏"),
            ("Kairo_Choose_Armor", "背包里找到铠甲并装备"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickEquipmentBar2", "点防具栏"),
            ("Kairo_Choose_Armor", "背包里找到铠甲并装备"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickEquipmentBar2", "点防具栏"),
            ("Kairo_Choose_Armor", "背包里找到铠甲并装备"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickEquipmentBar2", "点防具栏"),
            ("Kairo_Choose_Armor", "背包里找到铠甲并装备"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickEquipmentBar2", "点防具栏"),
            ("Kairo_Choose_Armor", "背包里找到铠甲并装备"),
            ("BackText_500ms", "退出角色界面"),
            ("BackText_500ms", "退出队伍界面"),
            ("Kairo_Return_Hotel", "住旅馆并返回大地图"),
            ("Kairo_Enter_Cave3", "进入洞穴3"),
            ("Kairo_Enter_Cave2", "进入洞穴2"),
            ("Kairo_Enter_Cave1", "进入洞穴1"),
            ("Kairo_Return_Home", "返回家园"),
            ("Kairo_Enter_WarriorPromotionStore", "进战士转职商店"),
            ("Kairo_Choose_WarriorMedal", "买5阶战士转职"),
            ("Kairo_Choose_WarriorMedal", "买5阶战士转职"),
            ("Kairo_Choose_WarriorMedal", "买5阶战士转职"),
            ("BackText_500ms", "出来"),
            ("Kairo_Enter_SupportPromotionStore", "进辅助转职商店"),
            ("Kairo_Choose_SupportMedal", "买5阶辅助转职"),
            ("BackText_500ms", "出来"),
            ("Kairo_Enter_MonkPromotionStore", "进法师转职商店"),
            ("Kairo_Choose_MonkMedal", "买5阶法师转职"),
            ("BackText_500ms", "出来"),
            ("Kairo_ViewTeams", "查看队伍并点击第一个角色"),
            ("Kairo_ClickPromotionInterface", "点进进入转职界面"),
            ("Kairo_ClickSwitchMagic", "切换到魔法职业"),
            ("MapSwipeUpToDown", "翻到转职界面底部"),
            ("Kairo_PromoteToMonk", "转职为大主教"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickPromotionInterface", "点进进入转职界面"),
            ("MapSwipeUpToDown", "翻到转职界面底部"),
            ("Kairo_PromoteToWhiteQueen", "转职为白皇后"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickPromotionInterface", "点进进入转职界面"),
            ("MapSwipeUpToDown", "翻到转职界面底部"),
            ("Kairo_PromoteToKnight", "转职为光辉骑士"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickPromotionInterface", "点进进入转职界面"),
            ("MapSwipeUpToDown", "翻到转职界面底部"),
            ("Kairo_PromoteToKnight", "转职为光辉骑士"),
            ("Kairo_ClickChangeCharacter", "切换下一个角色"),
            ("Kairo_ClickPromotionInterface", "点进进入转职界面"),
            ("MapSwipeUpToDown", "翻到转职界面底部"),
            ("Kairo_PromoteToSwordsman", "转职为剑士统帅"),
            ("BackText_500ms", "退出角色界面"),
            ("BackText_500ms", "退出队伍界面"),
            ("Kairo_Return_Hotel", "住旅馆并返回大地图"),
            ("Kairo_Enter_Cave7", "打boss结束"),
        ]

        for task_name, task_description in tasks_to_execute:
            logger.info(f"正在执行任务 - {task_description}.")

            # 检查是否收到停止任务的请求
            if context.tasker.stopping:
                logger.info(f"检测到停止任务请求，在执行 {task_description} 前退出。")
                return CustomAction.RunResult(success=False)

            run_result_detail = context.run_task(task_name)

            # 判断任务是否成功：
            if hasattr(run_result_detail, "nodes") and not run_result_detail.nodes:
                if not run_result_detail.nodes:
                    task_successful = False
            else:
                task_successful = True  # 假设只要 run_task 没有抛异常，且不是识别失败（nodes为空），就算成功

            if not task_successful:
                logger.error(f"任务 '{task_description}' 执行失败或未达到成功条件！")
                return CustomAction.RunResult(success=False)
            else:
                # logger.info(f"任务 {task_description} 执行成功。")
                pass

            # 模拟用户操作间隔
            time.sleep(1)
        logger.info("所有顺序任务执行完毕，成功探索开罗迷宫。")
        return CustomAction.RunResult(success=True)
