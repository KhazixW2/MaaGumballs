from typing import TYPE_CHECKING

from maa.context import Context
from action.fight import fightUtils
from action.fight.fightUtils import timing_decorator

if TYPE_CHECKING:
    from action.fight.mars101 import Mars101
from utils import logger                     

class MarsHPManager:
    """马尔斯101血量管理器：负责血量检查、治疗、安全压血等逻辑"""

    # 优先级：痊愈术(卷轴) → 神恩术(卷轴) → 治疗术(MP，永远最后)
    HEAL_ORDER = (("水", "痊愈术"), ("光", "神恩术"), ("水", "治疗术"))
    HEAL_TARGET = 0.8
    HEAL_MAX_CAST =5
    # 轮到治疗术之前，是否把两种卷轴法术重新补探一轮（应对中途补到卷轴）
    RE_PROBE_SCROLLS = True
    
    def __init__(self, mars: "Mars101") -> None:
        self.mars: "Mars101" = mars

    def Check_DefaultStatus(self, context: Context):
        """检查冈布奥状态，保持80%以上HP"""
        tempNum = self.mars.layers % 10
        if (
            (11 <= self.mars.layers <= 79) and (tempNum == 1 or tempNum == 5 or tempNum == 9)
        ) or self.mars.layers >= 80:
            if self.mars.layers <= 60 and self.mars.useEarthGate > 0:
                return True
            cast_time = 0
            StatusDetail = fightUtils.checkGumballsStatusV2(context)
            CurrentHP = float(StatusDetail["当前生命值"])
            MaxHp = float(StatusDetail["最大生命值"])
            HPStatus = CurrentHP / MaxHp

            if HPStatus < self.HEAL_TARGET:
                if self.mars.layers <= 60:
                    fightUtils.cast_magic_special("生命颂歌", context)
                if self.mars.layers >= 120:
                    fightUtils.cast_magic("气", "静电场", context)

                final_hp = self._heal_to_target(context,hp=HPStatus)
                if final_hp < self.HEAL_TARGET:
                    logger.warning(f"第 {self.mars.layers} 层补血未达标（{final_hp:.0%}）")
                    # context.run_task("Fight_ReturnMainWindow")
                    # StatusDetail = fightUtils.checkGumballsStatusV2(context)
                    # AfterHP = float(StatusDetail["当前生命值"])
                    # MaxHp = float(StatusDetail["最大生命值"])
                    # HPStatus = AfterHP / MaxHp
            if self.mars.layers >= 51 and not fightUtils.checkBuffStatus("神圣重生", context):
                fightUtils.cast_magic("光", "神圣重生", context)
        return True

    def _heal_to_target(self, context: Context,
                        target: float = HEAL_TARGET,
                        max_cast: int = HEAL_MAX_CAST,
                        hp: float = 1) -> float:
        """按 痊愈术 → 神恩术 → 治疗术 的优先级补血，返回补完后的 HP 百分比。

        "用完"只记录在本次调用内（局部变量）：
        下一次补血会重新从痊愈术开始试，所以后续补充到卷轴后，
        痊愈术会自动恢复成首选，不会被历史状态屏蔽。
        """
        exhaust: set[str] = set()        # 本次会话内失效的法术
        no_effect: dict[str, int] = {}   # 施放了但血量没涨的连续次数
        re_probed = False                # 本次会话是否已补探过卷轴法术

        for _ in range(max_cast):


            spell = next((s for s in self.HEAL_ORDER if s[1] not in exhaust), None)

            # 只剩治疗术可用时，补探一轮卷轴法术（只做一次）
            if (spell is None or spell[1] == "治疗术") and self.RE_PROBE_SCROLLS \
                    and not re_probed and (exhaust & {"痊愈术", "神恩术"}):
                re_probed = True
                exhaust -= {"痊愈术", "神恩术"}
                logger.info("即将动用治疗术，补探一次痊愈术/神恩术（可能已补充卷轴）")
                continue

            if spell is None:
                logger.warning("痊愈术/神恩术/治疗术 均不可用，停止补血")
                return hp
            element, name = spell

            # 判据一：魔法书里找不到（卷轴用完）→ 本次会话内跳过，且不消耗施法轮次
            if not fightUtils.cast_magic(element, name, context):
                logger.info(f"{name} 找不到/已用完，本次会话降级")
                exhaust.add(name)
                continue

            context.run_task("Fight_ReturnMainWindow")
            after = self.Get_CurrentHPStatus(context)
            if after >= target or context.tasker.stopping:
                return after

            # 判据二：找到了也点了，但血量没涨（图标还在、实际放不出来）→ 连续 2 次才算失效
            if after <= hp:
                no_effect[name] = 0
                continue
            no_effect[name] = no_effect.get(name, 0) + 1
            logger.info(f"{name} 施放后血量未变化（{hp:.0%} -> {after:.0%}），"
                        f"第 {no_effect[name]} 次")
            if name != "治疗术" and no_effect[name] >= 2:
                logger.warning(f"{name} 连续 {no_effect[name]} 次无效，本次会话标记为不可用")
                exhaust.add(name)

        return self.Get_CurrentHPStatus(context)
    
    def Get_CurrentHPStatus(self, context: Context):
        """获取当前HP百分比"""
        StatusDetail = fightUtils.checkGumballsStatusV2(context)
        CurrentHP = float(StatusDetail["当前生命值"])
        MaxHp = float(StatusDetail["最大生命值"])
        return CurrentHP / MaxHp

    @timing_decorator
    def Control_TenpecentHP(self, context: Context):
        """安全压血主逻辑，尽可能压低目标血量同时确保目标不会死亡"""
        SAFETY_MARGIN = 0.08
        MAX_ATTEMPTS = 20
        TEST_ROUNDS = 3
        MIN_CHANGE_THRESHOLD = 0.01
        CONSECUTIVE_STALL_LIMIT = 3
        BLESSING_DAMAGE_MULTIPLIER = 9
        DAMAGE_HISTORY_SIZE = 3

        current_hp = self.Get_CurrentHPStatus(context)

        _, max_stoneskin_damage = self.Test_Stoneskin_Damage(context, TEST_ROUNDS)
        if max_stoneskin_damage is None:
            return 10000000

        blessing_damage = max_stoneskin_damage * BLESSING_DAMAGE_MULTIPLIER
        current_hp = self.Get_CurrentHPStatus(context)
        stoneskin_damage_history = []
        blessing_damage_history = []
        attempts = 0
        consecutive_no_change = 0

        while attempts < MAX_ATTEMPTS:
            safe_hp_to_reduce = current_hp - SAFETY_MARGIN

            if blessing_damage <= safe_hp_to_reduce and current_hp > 0.1:
                prev_hp = current_hp
                fightUtils.cast_magic("光", "祝福术", context)
                context.run_task("Fight_ReturnMainWindow")
                current_hp = self.Get_CurrentHPStatus(context)

                actual_damage = prev_hp - current_hp
                if actual_damage > 0:
                    blessing_damage_history.append(actual_damage)
                    if len(blessing_damage_history) > DAMAGE_HISTORY_SIZE:
                        blessing_damage_history.pop(0)
                    new_max_blessing = max(blessing_damage_history)
                    if new_max_blessing > blessing_damage:
                        blessing_damage = new_max_blessing
                    elif new_max_blessing < blessing_damage * 0.8:
                        blessing_damage = new_max_blessing

            elif max_stoneskin_damage <= safe_hp_to_reduce and current_hp > 0.1:
                prev_hp = current_hp
                fightUtils.cast_magic("土", "石肤术", context)
                context.run_task("Fight_ReturnMainWindow")
                current_hp = self.Get_CurrentHPStatus(context)

                if current_hp <= 0:
                    return -1

                actual_damage = prev_hp - current_hp
                if actual_damage > 0:
                    stoneskin_damage_history.append(actual_damage)
                    if len(stoneskin_damage_history) > DAMAGE_HISTORY_SIZE:
                        stoneskin_damage_history.pop(0)
                    new_max_stoneskin = max(stoneskin_damage_history)
                    if new_max_stoneskin > max_stoneskin_damage:
                        max_stoneskin_damage = new_max_stoneskin
            else:
                return current_hp

            hp_change = prev_hp - current_hp
            attempts += 1

            if hp_change > 0:
                consecutive_no_change = 0
            else:
                consecutive_no_change += 1
                if consecutive_no_change >= CONSECUTIVE_STALL_LIMIT:
                    return current_hp

        return current_hp

    def Test_Stoneskin_Damage(self, context: Context, test_rounds: int):
        """测试石肤术伤害"""
        effective_casts = 0
        damage_values = []

        for _ in range(test_rounds):
            prev_hp = self.Get_CurrentHPStatus(context)
            fightUtils.cast_magic("土", "石肤术", context)
            context.run_task("Fight_ReturnMainWindow")
            current_hp = self.Get_CurrentHPStatus(context)

            if current_hp <= 0:
                return None, None

            if prev_hp > current_hp:
                damage_values.append(prev_hp - current_hp)
                effective_casts += 1

        if effective_casts == 0:
            return None, None

        avg_damage = sum(damage_values) / effective_casts
        max_damage = max(damage_values)

        return avg_damage, max_damage
