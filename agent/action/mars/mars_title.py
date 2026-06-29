from typing import TYPE_CHECKING

from maa.context import Context
from action.fight import fightUtils
from action.fight.fightUtils import timing_decorator
from utils import logger

if TYPE_CHECKING:
    from action.fight.mars101 import Mars101


class MarsTitleManager:
    """马尔斯101称号管理器：负责按层数自动学习称号"""

    def __init__(self, mars: "Mars101") -> None:
        self.mars: "Mars101" = mars
        # 称号学习状态标志
        self.isTitle_L1 = False
        self.isTitle_L10 = False
        self.isTitle_L61 = False
        self.isTitle_L86 = False
        self.isGetDragonTitle = False

    @timing_decorator
    def Check_DefaultTitle(self, context: Context):
        """
        检查默认称号
        1. 检查1层的称号: 魔法学徒点满
        2. 检查28层称号: 点满符文师
        3. 检查61层的称号: 位面点满即可
        4. 检查86层的称号: 位面，大铸剑师，大剑师都点满
        """
        if (self.mars.layers >= 1 and self.mars.layers <= 3) and self.isTitle_L1 == False:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 4, context)
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L1 = True
            return True
        elif (self.mars.layers >= 10 and self.mars.layers <= 13) and self.isTitle_L10 == False:
            fightUtils.title_learn("冒险", 1, "寻宝者", 1, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 1, context)
            fightUtils.title_learn("冒险", 3, "符文师", 4, context)
            context.run_task("Fight_ReturnMainWindow")
            self.isTitle_L10 = True
            return True
        elif (self.mars.layers >= 61 and self.mars.layers <= 63) and self.isTitle_L61 == False:
            fightUtils.title_learn("魔法", 1, "魔法学徒", 1, context)
            fightUtils.title_learn("魔法", 2, "黑袍法师", 1, context)
            fightUtils.title_learn("魔法", 3, "咒术师", 2, context)
            fightUtils.title_learn("魔法", 4, "土系大师", 1, context)
            fightUtils.title_learn("魔法", 5, "位面先知", 1, context)
            fightUtils.title_learn_branch("魔法", 5, "魔力强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "生命强化", 3, context)
            fightUtils.title_learn_branch("魔法", 5, "魔法强化", 3, context)
            context.run_task("Fight_ReturnMainWindow")

            self.isTitle_L61 = True
            return True

        elif (self.mars.layers >= 86 and self.mars.layers <= 88) and self.isTitle_L86 == False:
            fightUtils.title_learn("战斗", 1, "见习战士", 3, context)
            fightUtils.title_learn("战斗", 2, "战士", 3, context)
            fightUtils.title_learn("战斗", 3, "剑舞者", 3, context)
            fightUtils.title_learn("战斗", 4, "大剑师", 3, context)
            fightUtils.title_learn("魔法", 2, "黑袍法师", 3, context)
            # fightUtils.title_learn("魔法", 3, "咒术师", 3, context)
            # fightUtils.title_learn("魔法", 4, "土系大师", 3, context)
            fightUtils.title_learn("冒险", 1, "寻宝者", 2, context)
            fightUtils.title_learn("冒险", 2, "勘探家", 2, context)
            if self.isTitle_L10 == False:
                fightUtils.title_learn("冒险", 3, "符文师", 3, context)
                self.isTitle_L10 = True
            # fightUtils.title_learn("冒险", 3, "符文师", 3, context)
            fightUtils.title_learn("冒险", 4, "武器大师", 3, context)
            fightUtils.title_learn("冒险", 5, "大铸剑师", 1, context)
            fightUtils.title_learn_branch("冒险", 5, "攻击强化", 3, context)
            fightUtils.title_learn_branch("冒险", 5, "生命强化", 3, context)
            # fightUtils.title_learn_branch("冒险", 5, "魔法强化", 3, context)
            if self.mars.astrological_title_para and self.mars.is_demontitle_enable:
                logger.info("点了恶魔")
                fightUtils.title_learn("恶魔", 1, "堕落者", 1, context)
                fightUtils.title_learn("恶魔", 2, "下位恶魔", 3, context)
                fightUtils.title_learn("恶魔", 3, "中位恶魔", 3, context)
                fightUtils.title_learn("恶魔", 4, "上位恶魔", 3, context)
                fightUtils.title_learn("恶魔", 5, "恶魔大领主", 1, context)
                fightUtils.title_learn_branch("恶魔", 5, "攻击强化", 3, context)
                fightUtils.title_learn_branch(
                    "恶魔", 5, "攻击强化", 3, context, repeatable=True
                )
                fightUtils.title_learn_branch("恶魔", 5, "生命强化", 3, context)
            else:
                logger.info("没点恶魔")
            if self.mars.target_leave_layer_para >= 149 and fightUtils.title_check(
                "巨龙", context
            ):
                self.isGetDragonTitle = True
                fightUtils.title_learn("巨龙", 1, "亚龙血统", 3, context)
                fightUtils.title_learn("巨龙", 2, "初级龙族血统", 3, context)
                fightUtils.title_learn("巨龙", 3, "中级龙族血统", 3, context)
                fightUtils.title_learn("巨龙", 4, "高级龙族血统", 3, context)

            context.run_task("Fight_ReturnMainWindow")

            self.isTitle_L86 = True
            return True
        return False
