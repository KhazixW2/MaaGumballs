from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from maa.define import RecognitionDetail
from utils import logger
from action.fight import fightUtils

import time
import re
import json


@AgentServer.custom_action("SaveLoad_little")
class SaveLoad_little(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        img = context.tasker.controller.post_screencap().wait().get()
        reco_inMaze = context.run_recognition("ConfirmEquipmentPack", img)
        if reco_inMaze:
            # 登出游戏
            logger.info("登出游戏")
            context.run_task("LogoutGame")

            # 返回迷宫
            logger.info("返回迷宫")
            context.run_task("ReturnMaze")
        else:
            logger.warning("不在迷宫中，无需保存")

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("GoDownstairsTrick_Test")
class GoDownstairsTrick_Test(CustomAction):
    # 这里检查永恒套装
    def CheckEternalSuit(self, context: Context, image, tartget_equipment_path):
        checkEternalDetail = context.run_recognition(
            "CheckEternalSuit",
            image,
            pipeline_override={
                "CheckEternalSuit": {
                    "recognition": "TemplateMatch",
                    "template": [tartget_equipment_path],
                    "roi": [30, 68, 665, 590],
                    "threshold": 0.7,
                }
            },
        )
        return checkEternalDetail

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # 这里检查永恒套装
        logger.info("黑永恒 检查是否有目标装备")
        context.run_task("OpenEquipmentPackage")
        img = context.tasker.controller.post_screencap().wait().get()
        before_gloves = self.CheckEternalSuit(
            context, img, "equipments/5level/永恒腕轮.png"
        )
        before_cloak = self.CheckEternalSuit(
            context, img, "equipments/5level/永恒披风.png"
        )
        before_helmet = self.CheckEternalSuit(
            context, img, "equipments/5level/永恒王冠.png"
        )
        before_weapon = self.CheckEternalSuit(
            context, img, "equipments/5level/永恒之球.png"
        )
        context.run_task("BackText")

        for i in range(101):
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)

            logger.info(f"黑永恒第{i}次尝试")
            context.run_task("Save_Status")
            context.run_task("StartAppV2")
            context.run_task("Fight_OpenedDoor")
            fightUtils.cast_magic("土", "地震术", context)
            context.run_task("KillChestMonster")

            logger.info("黑永恒 检查是否黑到目标装备")
            context.run_task("OpenEquipmentPackage")
            time.sleep(1)
            img_2 = context.tasker.controller.post_screencap().wait().get()
            temp = 0
            if not before_gloves:
                after_gloves = self.CheckEternalSuit(
                    context, img_2, "equipments/5level/永恒腕轮.png"
                )
                if after_gloves:
                    temp += 1
            else:
                after_gloves = before_gloves
            if not before_cloak:
                after_cloak = self.CheckEternalSuit(
                    context, img_2, "equipments/5level/永恒披风.png"
                )
                if after_cloak:
                    temp += 1
            else:
                after_cloak = before_cloak
            if not before_helmet:
                after_helmet = self.CheckEternalSuit(
                    context, img_2, "equipments/5level/永恒王冠.png"
                )
                if after_helmet:
                    temp += 1
            else:
                after_helmet = before_helmet
            if not before_weapon:
                after_weapon = self.CheckEternalSuit(
                    context, img_2, "equipments/5level/永恒之球.png"
                )
                if after_weapon:
                    temp += 1
            else:
                after_weapon = before_weapon

            context.run_task("BackText")

            if temp >= 1:
                logger.info("黑永恒成功，恢复网络，可以暂离保存")
                context.run_task("StopAppV2")
                time.sleep(1)
                context.run_task("Save_Status")
                return CustomAction.RunResult(success=True)

            else:
                logger.info("黑永恒失败, 小SL然后联网进行下一次尝试")
                context.run_task("LogoutGame")
                context.run_task("StopAppV2")
                context.run_task("ReturnMaze")

        logger.warning("黑永恒失败")
        return CustomAction.RunResult(success=False)


@AgentServer.custom_action("PoolTrick_Test")
class PoolTrick_Test(CustomAction):

    # 这里检查攻击力数值
    def getArmorATK(self, context: Context) -> int:
        armorATK = 0

        context.run_task("OpenArmorPage")
        recoDetail = context.run_task("OCRArmorATK")
        if recoDetail.nodes:
            armorATK = recoDetail.nodes[0].recognition.best_result.text
            armorATK = int(armorATK.replace(" ", ""))
            logger.info(f"检测当前攻击力数值: {armorATK}")

        context.run_task("BackText")
        return armorATK

    # 这里检查火神
    def checkFiregod(self, context: Context):
        time.sleep(0.5)
        img = context.tasker.controller.post_screencap().wait().get()
        checkfiregodDetail = context.run_recognition(
            "CheckEternalSuit",
            img,
            pipeline_override={
                "CheckEternalSuit": {
                    "recognition": "TemplateMatch",
                    "template": [
                        "fight/divineForgeLand/Firegod.png",
                        "fight/divineForgeLand/Firegod_time_stop.png",
                        "fight/divineForgeLand/RedHatBody.png",
                        "fight/divineForgeLand/RedHatBody_stop.png",
                        "fight/divineForgeLand/Weapon.png",
                        "fight/divineForgeLand/Weapon_time_stop.png",
                    ],
                    "roi": [8, 131, 710, 997],
                    "timeout": 3000,
                }
            },
        )
        return checkfiregodDetail

    # 这里是核心函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        # 这里检查攻击力数值
        before_ArmorATK = self.getArmorATK(context)

        # 这里保存状态
        context.run_task("Save_Status")

        # 先找到泉水位置
        checkCount = 10
        searchpoolpos = None
        searchDetail = context.run_task("SearchPool")
        while not (searchDetail.nodes or checkCount <= 0):
            checkCount -= 1
            fightUtils.PushOne(context)
            searchDetail = context.run_task("SearchPool")
        if searchDetail.nodes:
            logger.info("找到泉水位置")
            searchpoolpos = searchDetail.nodes[0].recognition.best_result.box
        else:
            logger.info("没有找到泉水位置")
            return CustomAction.RunResult(success=False)

        # 检查是否有火神，如果有可以不用释放技能推序
        firegod = self.checkFiregod(context)

        # 这里进行小退，恢复现场
        context.run_task("LogoutGame")
        context.run_task("ReturnMaze")

        # 这里进行小退，恢复尸体
        for i in range(31):
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)
            logger.info(f"黑泉水第{i}次尝试")

            if not firegod:
                fightUtils.PushOne(context)
            context.run_task("Save_Status")

            # 每次暂离之后，执行点击泉水的操作
            click_job = context.tasker.controller.post_click(
                searchpoolpos[0] + searchpoolpos[2] // 2,
                searchpoolpos[1] + searchpoolpos[3] // 2,
            )
            click_job.wait()
            time.sleep(0.1)

            # 翻找泉水
            context.run_task("SearchPool_Next")

            # 检查是否泉水加成在攻击
            after_ArmorATK = self.getArmorATK(context)
            if after_ArmorATK != before_ArmorATK:
                logger.info(
                    f"黑泉水成功，检测到攻击力数值提升: {after_ArmorATK - before_ArmorATK}"
                )
                context.run_task("Save_Status")
                return CustomAction.RunResult(success=True)

            # 不满足条件则小退恢复尸体
            context.run_task("LogoutGame")
            context.run_task("ReturnMaze")

        logger.warning("黑泉水失败")
        return CustomAction.RunResult(success=False)


@AgentServer.custom_action("SunlightTrick_Test")
class SunlightTrick_Test(CustomAction):
    def getImprintNumber(self, context: Context) -> list:
        # Init
        sunlightimprintnumber = [0]
        starlightimprintnumber = [0]

        # 打开刻印背包
        context.run_task("OpenArmorPage")
        context.run_task("OpenImprintPage")

        # 这里检查日光和星光
        context.run_task("ClickSunlightImprint")
        sunLightDetail = context.run_task("findpercent")
        context.run_task("ClickStarlightImprint")
        starLightDetail = context.run_task("findpercent")

        # 如果检测到星光和日光，提取数字，否则默认0
        if sunLightDetail.nodes:
            sunlightimprintnumber = sunLightDetail.nodes[0].recognition.best_result.text
            sunlightimprintnumber = re.findall(r"\d+", sunlightimprintnumber)
        if starLightDetail.nodes:
            starlightimprintnumber = starLightDetail.nodes[
                0
            ].recognition.best_result.text
            starlightimprintnumber = re.findall(r"\d+", starlightimprintnumber)

        res = [int(sunlightimprintnumber[0]), int(starlightimprintnumber[0])]
        # print(res)
        context.run_task("BackText")
        context.run_task("BackText")
        return res

    # 这里检查火神
    def checkFiregod(self, context: Context):
        time.sleep(0.5)
        img = context.tasker.controller.post_screencap().wait().get()
        checkfiregodDetail = context.run_recognition(
            "CheckEternalSuit",
            img,
            pipeline_override={
                "CheckEternalSuit": {
                    "recognition": "TemplateMatch",
                    "template": [
                        "fight/divineForgeLand/Firegod.png",
                        "fight/divineForgeLand/Firegod_time_stop.png",
                        "fight/divineForgeLand/RedHatBody.png",
                        "fight/divineForgeLand/RedHatBody_stop.png",
                        "fight/divineForgeLand/Weapon.png",
                        "fight/divineForgeLand/Weapon_time_stop.png",
                    ],
                    "roi": [8, 131, 710, 997],
                    "timeout": 3000,
                }
            },
        )
        return checkfiregodDetail

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        # 这里确定是否要星光
        starlight_accept_para = json.loads(argv.custom_action_param)["accept_sunlight"]

        # 这里检查日光和星光
        before_sunlightimprintnumber, before_starlightimprintnumber = (
            self.getImprintNumber(context)
        )

        # 这里保存状态
        context.run_task("Save_Status")

        # 先找到尸体
        checkCount = 10
        searchbodypos = None
        searchDetail = context.run_task("SearchBody")
        while not (searchDetail.nodes or checkCount <= 0):
            checkCount -= 1
            fightUtils.PushOne(context)
            searchDetail = context.run_task("SearchBody")
        if searchDetail.nodes:
            searchbodypos = searchDetail.nodes[0].recognition.best_result.box
        else:
            logger.warning("没有找到尸体或者兵器")
            return CustomAction.RunResult(success=False)

        # 检查是否有火神，如果有可以不用释放技能推序
        firegod = self.checkFiregod(context)

        # 这里进行小退，恢复现场
        context.run_task("LogoutGame")
        context.run_task("ReturnMaze")

        for i in range(31):
            if context.tasker.stopping:
                logger.info("检测到停止任务, 开始退出agent")
                return CustomAction.RunResult(success=False)

            logger.info(f"黑日光第{i}次尝试")
            if not firegod:
                fightUtils.PushOne(context)
            context.run_task("Save_Status")

            # 每次暂离之后，执行点击尸体的操作
            click_job = context.tasker.controller.post_click(
                searchbodypos[0] + searchbodypos[2] // 2,
                searchbodypos[1] + searchbodypos[3] // 2,
            )
            click_job.wait()
            time.sleep(0.1)

            # 翻找尸体
            context.run_task("SearchBody_Next")

            # 检查是否出日光或者星光
            after_sunlightimprintnumber, after_starlightimprintnumber = (
                self.getImprintNumber(context)
            )
            condition_met = False
            if starlight_accept_para:
                if (
                    after_sunlightimprintnumber != before_sunlightimprintnumber
                    or after_starlightimprintnumber != before_starlightimprintnumber
                ):
                    condition_met = True
            else:
                if after_sunlightimprintnumber != before_sunlightimprintnumber:
                    condition_met = True

            # 这里检查是否满足条件
            if condition_met:
                logger.info("黑日光成功，检测到日光或者星光: ")
                context.run_task("Save_Status")
                return CustomAction.RunResult(success=True)
            else:
                context.run_task("LogoutGame")
                context.run_task("ReturnMaze")

        logger.warning("黑日光失败")
        return CustomAction.RunResult(success=False)


@AgentServer.custom_action("Find_Stove_Sequence_Test")
class Find_Stove_Sequence_Test(CustomAction):

    def split_zero_sequence_advanced(self, input_list):
        """
        用来处理101序列，返回垫子序列和日光装备等级序列
        参数:
            input_list (list): 输入列表，例如 [5,3]
        返回:
            zero_counts (list): 包含开头零、非零间零和结尾零的列表，如 [0]
            non_zero_values (list): 非零值列表，如 [5,3]
        """

        zero_counts = []
        non_zero_values = []
        current_index = 0
        list_length = len(input_list)

        # 处理开头的零
        has_leading_zeros = False
        while current_index < list_length and input_list[current_index] == 0:
            current_index += 1
            has_leading_zeros = True
        if has_leading_zeros:
            zero_counts.append(current_index)
        else:
            # 如果没有前导零，并且列表不为空，则添加一个0
            if list_length > 0:
                zero_counts.append(0)

        # 处理中间的非零值和零
        previous_was_non_zero = False

        while current_index < list_length:
            current_value = input_list[current_index]

            if current_value != 0:
                # 遇到非零值
                non_zero_values.append(current_value)

                if previous_was_non_zero:
                    # 如果前一个也是非零值，记录0表示它们之间没有零
                    zero_counts.append(0)
                previous_was_non_zero = True
            else:
                # 遇到零
                previous_was_non_zero = False

                # 计算连续零的数量
                consecutive_zeros = 1
                current_index += 1
                while current_index < list_length and input_list[current_index] == 0:
                    consecutive_zeros += 1
                    current_index += 1

                # 添加连续零的数量到结果
                zero_counts.append(consecutive_zeros)
                continue  # 跳过下面的索引递增，因为在内层循环中已经处理过了

            current_index += 1

        # 处理结尾的零
        # （在当前逻辑中，结尾的零已经在主循环中处理，无需额外步骤）

        # 处理空输入的情况
        if not non_zero_values and not zero_counts and list_length > 0:
            zero_counts.append(list_length)

        return zero_counts, non_zero_values

    # 这里是填入高星装备,从最右边找到最左边
    def find_and_click_equipment_from_right(
        self, context: Context, equipment_level: int
    ) -> RecognitionDetail | None:
        """从背包最右侧开始查找并点击指定等级的装备

        Args:
            context: 任务上下文
            equipment_level: 装备等级

        Returns:
            RecognitionDetail | None: 找到并点击成功则返回识别结果，否则返回 None
        """
        equipment_action = {
            6: "Find_and_Click_level6_Equipmnet",
            5: "Find_and_Click_level5_Equipmnet",
            4: "Find_and_Click_level4_Equipmnet",
            3: "Find_and_Click_level3_Equipmnet",
        }.get(equipment_level)

        if not equipment_action:
            logger.warning(f"不支持的装备等级: {equipment_level}")
            return None

        logger.info("首先在当前页面查找装备...")
        image = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition(equipment_action, image):
            logger.info(f"在当前页识别到 {equipment_level} 星装备，正在点击...")
            find_equipment_detail = context.run_task(equipment_action)
            if find_equipment_detail.nodes:
                logger.info(f"已在当前页找到并点击 {equipment_level} 星装备")
                time.sleep(1)
                return find_equipment_detail

        logger.info("当前页未找到，将从最右侧页面开始查找...")
        context.run_task("Bag_ToRightestPage")
        time.sleep(0.5)

        for _ in range(10):
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition(equipment_action, image):
                logger.info(f"识别到 {equipment_level} 星装备，正在点击...")
                find_equipment_detail = context.run_task(equipment_action)
                if find_equipment_detail.nodes:
                    logger.info(f"已找到并点击 {equipment_level} 星装备")
                    time.sleep(1)
                    return find_equipment_detail

            logger.info("当前页未找到，尝试翻到上一页")
            prev_page_detail = context.run_task("Bag_ToPrevPage")
            time.sleep(1)

            if not prev_page_detail.nodes:
                logger.info("已到达背包最左侧页面，停止查找")
                break

        logger.warning(f"未在背包中找到 {equipment_level} 星装备")
        return None

    def wait_and_click_select_equipment(self, context: Context, pre_waiting=1):
        """等待并点击装备选择按钮并且熔炼装备,确保成功熔炼
        Args:
            context: 任务上下文
            pre_waiting: 前置等待时间
        """
        time.sleep(pre_waiting)
        image = context.tasker.controller.post_screencap().wait().get()
        while not context.run_recognition("Click_Select_Equipment", image):
            time.sleep(0.5)
            image = context.tasker.controller.post_screencap().wait().get()
        image = context.tasker.controller.post_screencap().wait().get()
        while not context.run_recognition("Click_Smelt_Equipment", image):
            time.sleep(0.5)
            image = context.tasker.controller.post_screencap().wait().get()
            context.run_task("Click_Smelt_Equipment")
        logger.info("成功熔炼")

    def _get_current_atk(self, context: Context) -> str | None:
        """获取当前攻击力，如果超过4位数字，只返回最后4位"""
        for _ in range(3):
            atk_detail = context.run_task("GetCurrentAtk")
            if atk_detail.nodes:
                atk = atk_detail.nodes[0].recognition.best_result.text
                # 移除空格并确保是数字
                atk = atk.replace(" ", "")
                # 如果提取到的攻击力超过4位数字，只保留最后4位
                if atk.isdigit() and len(atk) > 4:
                    original_atk = atk
                    atk = atk[-4:]
                    logger.info(f"当前攻击: {original_atk}，截取后: {atk}")
                else:
                    logger.info(f"当前攻击: {atk}")
                return atk
            logger.warning("未找到攻击力，1秒后重试")
            time.sleep(1)
        logger.error("重试3次后仍未找到攻击力")
        return None

    def add_low_level_equipment(
        self, context: Context, num: int, page: int = 2, auto_melt: int = 0
    ):
        if num == 0:
            logger.info("个数为0, 无需填入低星装备")
            return
        context.run_task("Bag_ToLeftestPage")
        for _ in range(page):
            context.run_task("Bag_ToNextPage")

        time.sleep(1)
        if auto_melt == 3:
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition("CheckFirstEquipmentLevel", image):
                # 说明出现了第一格出现了4星装备,根据情况提前结束
                logger.info("第一格出现了4星装备,提前结束")
                return False
        elif auto_melt == 6:
            image = context.tasker.controller.post_screencap().wait().get()
            if context.run_recognition(
                "CheckFirstEquipmentLevel_empty_box",
                image,
                pipeline_override={
                    "CheckFirstEquipmentLevel_empty_box": {
                        "recognition": "TemplateMatch",
                        "template": "fight/divineForgeLand/empty_box.png",
                        "roi": [57, 630, 131, 142],
                        "action": "DoNothing",
                        "timeout": 1500,
                    }
                },
            ):

                # 说明出现了第一格出现了空格，说明所有装备都熔完了,根据情况提前结束
                logger.info("所有装备熔炼完毕")
                return False

        for _ in range(num):

            context.run_task("AddLowLevelEquipment")
            self.wait_and_click_select_equipment(context)
        logger.info(f"填入低星装备{num}个成功")
        return True

    def get_base_stove_sequence(self, context: Context, stove_sequence: list = None):
        assert len(stove_sequence) == 101
        context.run_task("ConfirmPutonArmor")
        context.run_task("OpenEquipmentStovePage")
        for i in range(101):
            if context.tasker.stopping:
                logger.info("测序被停止")
                return []

            before_atk = self._get_current_atk(context)
            if not before_atk:
                logger.error("未获取到当前攻击, 停止测序")
                return []
            find_equipment_detail = self.find_and_click_equipment_from_right(context, 6)
            if find_equipment_detail:
                # 找到装备并且点击，进入后续操作，点击选择--点击熔炼装备--判断是否出现天下布武
                self.wait_and_click_select_equipment(context)

                after_atk = self._get_current_atk(context)
                if not after_atk:
                    logger.error("未获取到当前攻击, 停止测序")
                    return []
                if after_atk != before_atk:
                    logger.info(f"第{i}次攻击变动")
                    stove_sequence[i] = 6

            else:
                # 没找到装备，进入后续操作，点击返回--点击返回--小SL--回到之前的状态--根据当前轮次填入一定数量的低星装备--找到装备--点击选择--点击熔炼装备--判断是否出现天下布武
                context.run_task("BackText")
                context.run_task("BackText")
                context.run_task("LogoutGame")
                context.run_task("ReturnMaze")
                context.run_task("ConfirmPutonArmor")
                context.run_task("OpenEquipmentStovePage")
                # 这里要填入i次低星装备，填入低星装备之后正常填入高星装备
                self.add_low_level_equipment(context, i)
                before_atk = self._get_current_atk(context)
                if not before_atk:
                    logger.error("未获取到当前攻击, 停止测序")
                    return []
                find_equipment_detail = self.find_and_click_equipment_from_right(
                    context, 6
                )
                if find_equipment_detail:
                    # 找到装备并且点击，进入后续操作，点击选择--点击熔炼装备--判断是否出现天下布武
                    self.wait_and_click_select_equipment(context)
                    after_atk = self._get_current_atk(context)
                    if not after_atk:
                        logger.error("未获取到当前攻击, 停止测序")
                        return []
                    if after_atk != before_atk:
                        logger.info(f"第{i}次攻击变动")
                        stove_sequence[i] = 6
        # 恢复现场
        logger.info("恢复现场")
        context.run_task("BackText")
        context.run_task("BackText")
        context.run_task("LogoutGame")
        context.run_task("ReturnMaze")

        return stove_sequence

    def upgrade_stove_sequence(self, context: Context, stove_sequence: list = None):
        assert len(stove_sequence) == 101
        stove_sequence_copy = stove_sequence.copy()
        for star in range(1, 4):
            low_star_num = 0
            context.run_task("ConfirmPutonArmor")
            context.run_task("OpenEquipmentStovePage")
            for i in range(len(stove_sequence)):
                if context.tasker.stopping:
                    logger.info("测序被停止")
                    return []
                if stove_sequence[i] == 0:
                    # 如果当前序列为0，跳过
                    low_star_num += 1

                else:
                    # 如果当前序列不为0，说明需要进行升级操作
                    logger.info(f"第{i}次尝试")
                    # 填入低星装备
                    self.add_low_level_equipment(context, low_star_num)
                    low_star_num = 0
                    before_atk = self._get_current_atk(context)
                    if not before_atk:
                        logger.error("未获取到当前攻击, 停止测序")
                        return []

                    # 进入后续操作，点击选择--点击熔炼装备--判断是否出现天下布武
                    find_equipment_detail = self.find_and_click_equipment_from_right(
                        context, stove_sequence[i] - star
                    )
                    if find_equipment_detail:
                        self.wait_and_click_select_equipment(context)

                        after_atk = self._get_current_atk(context)
                        if not after_atk:
                            logger.error("未获取到当前攻击, 停止测序")
                            return []
                        if after_atk != before_atk:
                            logger.info(f"第{i}次攻击变动")

                            logger.info(
                                f"{stove_sequence[i]}星装备更换为{stove_sequence[i]-star}星装备"
                            )
                            stove_sequence_copy[i] = stove_sequence[i] - star
                    else:
                        context.run_task("BackText")
                        context.run_task("BackText")
                        context.run_task("LogoutGame")
                        context.run_task("ReturnMaze")
                        context.run_task("ConfirmPutonArmor")
                        context.run_task("OpenEquipmentStovePage")

                        self.add_low_level_equipment(context, i)
                        low_star_num = 0
                        before_atk = self._get_current_atk(context)

                        if not before_atk:
                            logger.error("未获取到当前攻击, 停止测序")
                            return []
                        find_equipment_detail = (
                            self.find_and_click_equipment_from_right(
                                context, stove_sequence[i] - star
                            )
                        )
                        if find_equipment_detail:
                            self.wait_and_click_select_equipment(context)

                            after_atk = self._get_current_atk(context)

                            if not before_atk:
                                logger.error("未获取到当前攻击, 停止测序")
                                return []
                            if after_atk != before_atk:
                                logger.info(f"第{i}次攻击变动")
                                logger.info(
                                    f"{stove_sequence[i]}星装备更换为{stove_sequence[i]-star}星装备"
                                )
                                stove_sequence_copy[i] = stove_sequence[i] - star

            # 恢复现场
            logger.info(stove_sequence_copy)
            logger.info("恢复现场")
            context.run_task("BackText")
            context.run_task("BackText")
            context.run_task("LogoutGame")
            context.run_task("ReturnMaze")

        return stove_sequence_copy

    def get_sunlightImprint_from_sequence(
        self,
        context: Context,
        stove_sequence: list = None,
        auto_melt: int = 0,
    ):
        assert len(stove_sequence) == 101

        low_star_num = 0
        context.run_task("ConfirmPutonArmor")
        context.run_task("OpenEquipmentStovePage")
        while True:
            for i in range(len(stove_sequence)):
                if context.tasker.stopping:
                    logger.info("测序被停止")
                    # 正常退出
                    return 0
                if stove_sequence[i] == 0:
                    # 如果当前序列为0，跳过
                    low_star_num += 1

                    if i == 100:
                        logger.info("到了序列末尾")
                        # 填入低星装备
                        flag = self.add_low_level_equipment(
                            context, low_star_num, auto_melt=auto_melt
                        )
                        # 正常退出
                        if flag == False:
                            return 0
                        low_star_num = 0

                else:
                    # 如果当前序列不为0，说明需要放入对应星级的装备
                    logger.info(f"第{i}次尝试")
                    # 填入低星装备
                    flag = self.add_low_level_equipment(
                        context, low_star_num, auto_melt=auto_melt
                    )
                    low_star_num = 0
                    # 正常退出
                    if flag == False:
                        return 0
                        # 进入后续操作，点击选择--点击熔炼装备
                    before_atk = self._get_current_atk(context)
                    if not before_atk:
                        return -1
                    find_equipment_detail = self.find_and_click_equipment_from_right(
                        context, stove_sequence[i]
                    )
                    if find_equipment_detail:
                        self.wait_and_click_select_equipment(context)

                    else:
                        number = 1
                        while not find_equipment_detail:
                            if stove_sequence[i] + number <= 6:
                                find_equipment_detail = (
                                    self.find_and_click_equipment_from_right(
                                        context, stove_sequence[i] + number
                                    )
                                )
                            else:
                                # 异常退出
                                logger.warning(
                                    f"未找到{stove_sequence[i] + number}星级装备"
                                )
                                return -1
                            number += 1
                        self.wait_and_click_select_equipment(context)

                    after_atk = self._get_current_atk(context)
                    if not after_atk:
                        logger.error("未获取到当前攻击, 停止测序")
                        return -1
                    if after_atk != before_atk:
                        logger.info(f"第{i}次攻击变动")
                    else:
                        logger.warning(f"第{i}次攻击未变动")
                        # 异常退出
                        return -1

    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        # 这里确定目标日光数
        target_sunlight_para = json.loads(argv.custom_action_param)["target_sunlight"]
        auto_melt_para = json.loads(argv.custom_action_param)["auto_melt"]

        base_stove_sequence = [0 for _ in range(101)]
        stove_sequence = self.get_base_stove_sequence(context, base_stove_sequence)
        if stove_sequence == []:
            return CustomAction.RunResult(success=False)

        logger.info(stove_sequence)
        count = len([x for x in stove_sequence if x != 0])
        logger.info(
            f"本次101序列中共有{count}个日光, 目标为{target_sunlight_para}个日光"
        )
        if count >= target_sunlight_para:
            logger.info("本次101序列满足目标日光要求")
            after_update_stove_sequence = self.upgrade_stove_sequence(
                context, stove_sequence
            )
            if after_update_stove_sequence == []:
                logger.warning(
                    "迭代后的101序列为空, 出现异常情况, 请检查锻火刻印是否已熔"
                )
                return CustomAction.RunResult(success=False)
            logger.info(f"迭代后的101序列为: {after_update_stove_sequence}")
            # 格式化
            low_star_list, sun_list = self.split_zero_sequence_advanced(
                after_update_stove_sequence
            )
            logger.info(f"垫子序列为: {low_star_list}")
            logger.info(f"日光装备等级序列为: {sun_list}")
        else:
            logger.info("本次101序列不满足目标日光要求")
            return CustomAction.RunResult(success=False)

        if auto_melt_para != 0:
            checkdetail = self.get_sunlightImprint_from_sequence(
                context, after_update_stove_sequence, auto_melt=auto_melt_para
            )
            if checkdetail == 0:
                return CustomAction.RunResult(success=True)
            elif checkdetail == -1:
                logger.warning("自动熔炼失败, 出现异常情况, 请检查锻火刻印是否已熔")
                return CustomAction.RunResult(success=False)
        return CustomAction.RunResult(success=True)
