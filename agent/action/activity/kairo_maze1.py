from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from utils import logger
from action.fight import fightUtils
import time


@AgentServer.custom_action("Kairo_Difficulty3_Start")
class Kairo_Difficulty3_Start(CustomAction):
    """
    一个按顺序执行多个预定义Maa Pipeline节点的自定义动作。
    """

    def __init__(self):
        super().__init__()
        self.context = None
        self.targetCnt = 9

    def _initialize(self, context: Context):
        self.context = context
        logger.info("初始化完毕,开始探索开罗迷宫")

    def _run_task(self, task_name: str, task_description: str = None):
        if task_description != None:
            logger.info(f"执行 '{task_description}' ")
        run_result_detail = self.context.run_task(task_name)
        if run_result_detail.nodes:
            pass
        else:
            logger.error(f"执行 '{task_description}' 失败或未达到成功条件！")
            return False

        return True

    def handle_Phase_1(self) -> bool:
        # 第一阶段
        self._run_task("Kairo_Return_Home", "返回家园")
        self._run_task("Kairo_Enter_Pub", "去酒馆招募三个冒险者")
        for _ in range(3):
            self._run_task("Kairo_SearchingMale")
        self.context.run_task("Fight_ReturnMainWindow")

        return True

    def handle_Phase_2(self) -> bool:
        # 第二阶段：洞穴探索循环
        for _ in range(self.targetCnt):
            self._run_task("Kairo_Return_Hotel")
            logger.info(f"第{_+1}/{self.targetCnt}次探索, 去洞穴1,2探索")
            self._run_task("Kairo_Enter_Cave1")
            self._run_task("Kairo_Enter_Cave2")
            self._run_task("Kairo_Return_Home")
        return True

    def handle_Phase_3(self) -> bool:
        # 第三阶段：武器购买与装备
        ## 购买武器和防具
        self._run_task("Kairo_Enter_WeaponStore", "买2权杖3斧子")
        for _ in range(2):
            self._run_task("Kairo_Choose_HolyMace")
        for _ in range(3):
            self._run_task("Kairo_Choose_Axe")
        self.context.run_task("Fight_ReturnMainWindow")

        self._run_task("Kairo_Enter_ArmorStore", "买5个神圣铠甲")
        for _ in range(5):
            self._run_task("Kairo_Choose_Armor")
        self.context.run_task("Fight_ReturnMainWindow")

        ## 购买徽章
        self._run_task("Kairo_Enter_WarriorPromotionStore", "买战士5级徽章3个")
        for _ in range(3):
            self._run_task("Kairo_Choose_WarriorMedal")
        self.context.run_task("Fight_ReturnMainWindow")
        self._run_task("Kairo_Enter_SupportPromotionStore", "买辅助5级徽章1个")
        self._run_task("Kairo_Choose_SupportMedal")
        self.context.run_task("Fight_ReturnMainWindow")
        self._run_task("Kairo_Enter_MonkPromotionStore", "买法师5级徽章1个")
        self._run_task("Kairo_Choose_MonkMedal")
        self.context.run_task("Fight_ReturnMainWindow")

        ## 分解不需要的装备
        self._run_task("Bag_Open")
        fightUtils.disassembleEquipment(
            777,
            ["白刃枪", "短剑", "铁斧", "木杖", "铁剑", "橡木杖", "佣兵之斧"],
            self.context,
        )
        self._run_task("Fight_ReturnMainWindow")

        ## 装备5个角色
        for _ in range(5):
            logger.info(f"武装第{_+1}个冒险者")
            if _ < 1:
                self._run_task("Kairo_ViewTeams")
            else:
                self._run_task("Kairo_ClickChangeCharacter")

            self._run_task("Kairo_ClickEquipmentBar1")
            if _ < 2:
                self._run_task("Kairo_Choose_HolyMace")
            else:
                self._run_task("Kairo_Choose_Axe")

            self._run_task("Kairo_ClickEquipmentBar2")
            self._run_task("Kairo_Choose_Armor")

        self.context.run_task("Fight_ReturnMainWindow")
        return True

    def handle_Phase_4(self):
        # 第四阶段：高级转职与最终战斗
        # 角色1-5转职
        for _ in range(5):
            if _ < 1:
                self._run_task("Kairo_ViewTeams")
            else:
                self._run_task("Kairo_ClickChangeCharacter")
            self._run_task("Kairo_ClickPromotionInterface")

            if _ < 1:
                self._run_task("Kairo_ClickSwitchMagic")
            self._run_task("MapSwipeUpToDown")

            if _ == 0:
                self._run_task("Kairo_PromoteToMonk", f"将第{_+1}个角色转职为主教")
            elif _ == 1:
                self._run_task(
                    "Kairo_PromoteToWhiteQueen", f"将第{_+1}个角色转职为白皇后"
                )
            else:
                self._run_task(
                    "Kairo_PromoteToKnight", f"将第{_+1}个角色转职为光辉骑士"
                )

        self.context.run_task("Fight_ReturnMainWindow")
        self._run_task("Kairo_Return_Hotel", "住旅馆并返回大地图")
        self._run_task("Kairo_Enter_Cave7", "打boss并进行结算")
        return True

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        """
        执行自定义动作的核心逻辑。
        :param context: Maa提供的上下文对象，用于与Maa框架交互。
        :param argv: 动作的参数（如果JSON中配置了）。
        :return: CustomAction.RunResult，表示动作的成功或失败。
        """
        # 初始化
        self._initialize(context)

        # 按阶段顺序执行任务
        phases = [
            self.handle_Phase_1,
            self.handle_Phase_2,
            self.handle_Phase_3,
            self.handle_Phase_4,
        ]

        for i, phase in enumerate(phases, 1):
            logger.info(f"开始执行第{i}阶段任务")
            if not phase():
                logger.error(f"第{i}阶段任务执行失败")
                return CustomAction.RunResult(success=False)
            # 检查是否收到停止任务的请求
            if self.context.tasker.stopping:
                logger.info(f"检测到停止任务请求，在第{i}阶段后退出。")
                return CustomAction.RunResult(success=False)
            time.sleep(1)

        logger.info("所有阶段任务执行完毕，成功探索开罗迷宫。")
        return CustomAction.RunResult(success=True)
