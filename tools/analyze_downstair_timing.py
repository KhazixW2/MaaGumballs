#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import io
import math
import re
from collections import Counter, defaultdict
from contextlib import redirect_stdout
from pathlib import Path

TIMING_RE = re.compile(r"\[timing:([^\]]+)\] cost ([0-9.]+)s")
DOWNSTAIR_RESULT_RE = re.compile(
    r"\[downstair_result\] result=([^ ]+) old_layer=([-0-9]+) new_layer=([-0-9]+) attempts=([0-9]+)(?: branch=([^ ]+))?"
)
RUN_START_RE = re.compile(r"马尔斯101初始化完成")
TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
START_EXPLORE_RE = re.compile(r"Start Explore ([0-9]+) layer")
INTERRUPT_EVENT_PATTERNS = {
    "story_stuck": ("卡剧情", re.compile(r"检测到卡剧情, 本层重新探索")),
    "leave_stuck": ("卡离开", re.compile(r"检测到卡离开, 本层重新探索")),
    "back_stuck": ("卡返回", re.compile(r"检测到卡返回, 本层重新探索")),
}
KEYHOLE_WAIT_STAGES = {
    "post.downstair.keyhole_wait_total",
    "post.downstair.keyhole_wait_sleep",
}
KEYHOLE_WAIT_PARENT_STAGE = "post.downstair"

STAGE_INFO = {
    "layer.current_check": (
        "当前层数确认",
        "每层开始前识别当前层数，保证后续逻辑基于正确楼层执行。"
    ),
    "pre.layer": (
        "战前总流程",
        "每层清怪前的整体准备耗时，包含剧情确认、技能助手、保命 buff 和地震等粗粒度步骤。"
    ),
    "pre.inter_confirm": (
        "战前剧情确认",
        "99层或目标层附近检查并处理战前剧情确认弹窗。"
    ),
    "pre.skill_assist": (
        "战前技能助手",
        "处理机械人技能选择和魔法助手开启。多数层应很短，命中技能/助手时会变长。"
    ),
    "pre.survival_buff": (
        "战前保命 buff",
        "接近出图层时检查血量和护盾，必要时释放静电场、寒冰护盾或极光屏障。"
    ),
    "pre.earthquake": (
        "战前地震术",
        "魔法助手已开启且处于100到110层时释放地震术，减少后续清层压力。"
    ),
    "fight.layer_total": (
        "战中总流程",
        "每层从开始清怪/探索到清层动作结束的外层总耗时；Boss层包含 fight.boss，普通层包含 fight.normal_task_total。"
    ),
    "fight.clear_layer": (
        "战中总流程(旧名)",
        "历史日志中的旧埋点名，等价于新版 fight.layer_total。"
    ),
    "fight.boss": (
        "Boss层战斗",
        "30/40/50等 boss 层的召唤和战斗处理耗时。"
    ),
    "fight.normal_task_total": (
        "普通层任务调用",
        "普通层调用 Mars_Fight_ClearCurrentLayer 自定义动作的耗时，包含 Maa 任务调度和内部处理器执行。"
    ),
    "fight.clear_current_layer": (
        "普通层任务调用(旧名)",
        "历史日志中的旧埋点名，等价于新版 fight.normal_task_total。"
    ),
    "fight.normal_processor_total": (
        "普通层处理器清层",
        "Mars_Fight_ClearCurrentLayer 内部 FightProcessor.clearCurrentLayer 的真实清层耗时，主要包含找地板、点击、攻击怪物。"
    ),
    "fight.processor_clear_current_layer": (
        "普通层处理器清层(旧名)",
        "历史日志中的旧埋点名，等价于新版 fight.normal_processor_total。"
    ),
    "fight.interrupt_check": (
        "战中后异常检查",
        "清层后检查是否仍有地板、是否死亡、是否卡剧情或卡返回。"
    ),
    "post.layer": (
        "战后总流程",
        "清层和异常检查完成后的整体战后流程，包含奖励、事件、特殊层、下楼等 post.* 子埋点。"
    ),
    "post.default_status": (
        "战后状态检查",
        "检查/恢复默认状态。耗时高通常表示状态识别或补状态动作发生了等待。",
    ),
    "post.reward": (
        "奖励处理",
        "处理马尔斯战后奖励、弹窗或掉落确认。非零耗时一般来自界面识别和点击流程。",
    ),
    "post.body": (
        "尸体事件",
        "识别并处理地图上的尸体类事件。耗时主要是事件识别、进入事件、退出主界面。",
    ),
    "post.ruins_shop": (
        "遗迹商店",
        "识别并处理遗迹商店。大量 0 表示本层未命中，偶发高值表示实际进入商店或等待。",
    ),
    "post.statue": (
        "雕像事件",
        "识别并处理雕像/老头雕像类事件。高值通常代表真的触发了事件。",
    ),
    "post.exchange_shop": (
        "交换商店",
        "识别并处理交换商店。非零耗时通常是进入商店、识别商品、退出界面。",
    ),
    "post.title": (
        "称号检查/加点",
        "战后检查默认称号。极大值通常表示打开称号页、购买称号或界面卡顿。",
    ),
    "post.special_layer": (
        "特殊层入口",
        "检查休息室/特殊层入口并处理特殊层逻辑。高值多半是真实进入特殊层或识别等待。",
    ),
    "post.before_leave": (
        "出图前处理",
        "接近目标层时执行离开迷宫前的收尾逻辑，次数少但单次可能很长。",
    ),
    "post.downstair": (
        "下楼总流程",
        "从准备下楼到确认楼层变化的整体耗时。默认会剔除手动等钥匙洞穴时间。",
    ),
    "post.downstair.layer_before": (
        "下楼前识别层数",
        "点击门之前识别当前楼层，用于后续判断楼层是否变化。",
    ),
    "post.downstair.read_cached_door": (
        "读取门缓存",
        "读取 fightProcessor 保存的门坐标。正常应接近 0。",
    ),
    "post.downstair.execute_door_click": (
        "点击缓存门坐标",
        "直接点击缓存的门坐标。正常应很短。",
    ),
    "post.downstair.fallback_screencap": (
        "兜底截图",
        "缓存门点击后楼层未变时，重新截图给兜底识别使用。",
    ),
    "post.downstair.fallback_detect_opened_door": (
        "兜底找开门",
        "缓存门点击失败后，再截图识别已打开的门。",
    ),
    "post.downstair.detect_opened_door": (
        "识别开门",
        "旧版下楼流程中截图识别已打开的门。若仍出现，说明日志来自旧逻辑或兜底路径。",
    ),
    "post.downstair.detect_key_hole": (
        "识别钥匙洞穴",
        "未找到开门时检查是否出现神秘洞穴。命中后通常会进入手动等待。",
    ),
    "post.downstair.execute_opened_door": (
        "执行开门任务",
        "通过识别到的开门节点执行下楼任务。新版只应在兜底识别路径中出现。",
    ),
    "post.downstair.keyhole_wait_total": (
        "等待钥匙洞穴",
        "发现神秘洞穴后的人工等待时间。默认从下楼总耗时中剔除，避免污染性能判断。",
    ),
    "post.downstair.keyhole_wait_sleep": (
        "钥匙洞穴轮询等待",
        "等待钥匙期间的 sleep 轮询时间。默认不纳入统计。",
    ),
    "post.downstair.wait_change_total": (
        "等待楼层变化总耗时",
        "点击门后反复识别楼层，直到层数变化或达到最大次数。当前下楼耗时的主要来源。",
    ),
    "post.downstair.wait_change_iter": (
        "单轮确认楼层变化",
        "每次确认楼层是否变化的循环耗时，包含一次当前楼层识别。",
    ),
    "post.downstair.layer_after": (
        "下楼后识别层数",
        "点击门后识别当前楼层。它被包含在 wait_change_iter 内，不要和父级相加。",
    ),
    "post.downstair.wait_change_sleep": (
        "楼层未变等待",
        "本轮未确认楼层变化时的固定 sleep。它被包含在 wait_change_total 内。",
    ),
}

RESULT_INFO = {
    "changed_confirmed": "已确认楼层变化，正常下楼成功",
    "no_change_but_continue": "多次确认后层数仍未变，但继续流程，可能在夹层或识别异常",
    "stopped_during_keyhole_wait": "等待钥匙洞穴期间收到停止任务",
    "processor_click_sent": "已发送缓存门点击，但这通常只是中间状态",
    "fallback_opened_door": "缓存点击失败后，通过兜底识别找到开门",
    "keyhole_manual_wait": "识别到钥匙洞穴，进入人工等待",
    "door_not_detected": "没有找到可点击门，通常会进入兜底路径",
}

BRANCH_INFO = {
    "cached_processor_door": "使用 fightProcessor 缓存的门坐标，最快的正常路径",
    "fallback_recognition": "缓存路径未确认下楼后，重新截图识别门/洞穴的兜底路径",
    "unknown": "旧日志或缺少 branch 字段",
}

DOWNSTAIR_STAGE_ORDER = [
    "post.downstair",
    "post.downstair.layer_before",
    "post.downstair.read_cached_door",
    "post.downstair.execute_door_click",
    "post.downstair.fallback_screencap",
    "post.downstair.fallback_detect_opened_door",
    "post.downstair.detect_opened_door",
    "post.downstair.detect_key_hole",
    "post.downstair.execute_opened_door",
    "post.downstair.keyhole_wait_total",
    "post.downstair.keyhole_wait_sleep",
    "post.downstair.wait_change_total",
    "post.downstair.wait_change_iter",
    "post.downstair.layer_after",
    "post.downstair.wait_change_sleep",
]


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    rank = (len(values) - 1) * p
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return values[lower]
    weight = rank - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def read_log_lines(path: Path, start_line: int | None) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if start_line and start_line > 1:
        return lines[start_line - 1 :]
    return lines


def detect_log_segments(lines: list[str], base_start_line: int = 1) -> list[dict]:
    starts = [index for index, line in enumerate(lines) if RUN_START_RE.search(line)]
    if not starts:
        return [
            {
                "index": 1,
                "start_offset": 0,
                "end_offset": len(lines),
                "start_line": base_start_line,
                "end_line": base_start_line + len(lines) - 1 if lines else base_start_line - 1,
                "first_layer": find_first_explore_layer(lines),
                "start_time": find_first_timestamp(lines),
                "marker": "未找到初始化标记，按整个范围分析",
            }
        ]

    segments = []
    for segment_index, start_offset in enumerate(starts, start=1):
        end_offset = starts[segment_index] if segment_index < len(starts) else len(lines)
        segment_lines = lines[start_offset:end_offset]
        segments.append(
            {
                "index": segment_index,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "start_line": base_start_line + start_offset,
                "end_line": base_start_line + end_offset - 1,
                "first_layer": find_first_explore_layer(segment_lines),
                "start_time": find_first_timestamp(segment_lines),
                "marker": "马尔斯101初始化完成",
            }
        )
    return segments


def find_first_timestamp(lines: list[str]) -> str:
    for line in lines:
        match = TIMESTAMP_RE.search(line)
        if match:
            return match.group(1)
    return "未知时间"


def find_first_explore_layer(lines: list[str]) -> int | None:
    for line in lines:
        match = START_EXPLORE_RE.search(line)
        if match:
            return int(match.group(1))
    return None


def default_output_dir(log_path: Path) -> Path:
    return log_path.with_name(f"{log_path.stem}_timing_reports")


def segment_report_path(output_dir: Path, segment: dict) -> Path:
    layer = segment["first_layer"]
    layer_text = f"layer_{layer}" if layer is not None else "layer_unknown"
    return output_dir / f"segment_{segment['index']:02d}_{layer_text}_lines_{segment['start_line']}-{segment['end_line']}.txt"


def remove_keyhole_wait_from_downstair(
    downstair_costs: list[float], keyhole_wait_costs: list[float]
) -> list[float]:
    adjusted = sorted(downstair_costs, reverse=True)
    for wait_cost in sorted(keyhole_wait_costs, reverse=True):
        for index, cost in enumerate(adjusted):
            if cost >= wait_cost:
                adjusted[index] = max(0.0, cost - wait_cost)
                break
    return sorted(adjusted)


def analyze(lines: list[str], include_keyhole_wait: bool) -> dict:
    stage_costs: dict[str, list[float]] = defaultdict(list)
    downstair_costs: list[float] = []
    excluded_keyhole_wait_costs: list[float] = []
    downstair_results: list[dict] = []
    interrupt_events: Counter[str] = Counter()

    for line in lines:
        for event_key, (_, event_re) in INTERRUPT_EVENT_PATTERNS.items():
            if event_re.search(line):
                interrupt_events[event_key] += 1
                break

        timing_match = TIMING_RE.search(line)
        if timing_match:
            name = timing_match.group(1)
            cost = float(timing_match.group(2))
            if not include_keyhole_wait and name in KEYHOLE_WAIT_STAGES:
                if name == "post.downstair.keyhole_wait_total":
                    excluded_keyhole_wait_costs.append(cost)
                continue
            stage_costs[name].append(cost)
            if name == "post.downstair":
                downstair_costs.append(cost)
            continue

        result_match = DOWNSTAIR_RESULT_RE.search(line)
        if result_match:
            downstair_results.append(
                {
                    "result": result_match.group(1),
                    "old_layer": int(result_match.group(2)),
                    "new_layer": int(result_match.group(3)),
                    "attempts": int(result_match.group(4)),
                    "branch": result_match.group(5) or "unknown",
                }
            )

    if not include_keyhole_wait and excluded_keyhole_wait_costs:
        adjusted_downstair_costs = remove_keyhole_wait_from_downstair(
            downstair_costs, excluded_keyhole_wait_costs
        )
        stage_costs[KEYHOLE_WAIT_PARENT_STAGE] = adjusted_downstair_costs
        downstair_costs = adjusted_downstair_costs

    return {
        "stage_costs": stage_costs,
        "downstair_costs": sorted(downstair_costs),
        "excluded_keyhole_wait_costs": excluded_keyhole_wait_costs,
        "downstair_results": downstair_results,
        "interrupt_events": interrupt_events,
    }


def stage_title(name: str) -> str:
    return STAGE_INFO.get(name, ("未登记埋点", "查看代码里的 timing_section 名称。"))[0]


def stage_note(name: str) -> str:
    return STAGE_INFO.get(name, ("未登记埋点", "查看代码里的 timing_section 名称。"))[1]


def summarize_costs(name: str, costs: list[float], total_timed: float) -> dict:
    ordered = sorted(costs)
    total = sum(ordered)
    return {
        "name": name,
        "title": stage_title(name),
        "note": stage_note(name),
        "count": len(ordered),
        "total": total,
        "avg": total / len(ordered),
        "max": ordered[-1],
        "share": (total / total_timed * 100.0) if total_timed else 0.0,
    }


def print_scope_notes(include_keyhole_wait: bool, excluded_keyhole_wait_costs: list[float]) -> None:
    print("== 统计口径说明 ==")
    print("1. 表里的“总耗时”是同名埋点的累计耗时；“均值”是该埋点平均每次出现的耗时。")
    print("2. 子埋点可能被父埋点包含，例如 post.downstair 包含 wait_change_total，wait_change_total 又包含 layer_after 和 sleep；不要把父子埋点直接相加当作真实墙钟时间。")
    print("3. “占比”按所有已记录埋点耗时求和计算，用于看相对热度；因为父子埋点会重叠，它不是整轮运行真实时间占比。")
    if include_keyhole_wait:
        print("4. 本次包含钥匙洞穴人工等待时间，适合看完整等待成本，但不适合判断代码优化空间。")
    else:
        excluded_total = sum(excluded_keyhole_wait_costs)
        print(
            f"4. 默认已剔除钥匙洞穴人工等待时间：{len(excluded_keyhole_wait_costs)} 条，合计 {excluded_total:.4f}s；这样更适合判断代码本身耗时。"
        )
    print()


def print_stage_summary(stage_costs: dict[str, list[float]], top_n: int) -> None:
    rows = []
    total_timed = sum(sum(costs) for costs in stage_costs.values())
    for name, costs in stage_costs.items():
        rows.append(summarize_costs(name, costs, total_timed))
    rows.sort(key=lambda row: row["total"], reverse=True)

    print("== 总耗时排行（含中文说明） ==")
    print(
        f"{'埋点名':<38} {'中文含义':<18} {'次数':>6} {'总耗时(s)':>11} {'均值(s)':>10} {'最大(s)':>10} {'占比%':>8}"
    )
    for row in rows[:top_n]:
        print(
            f"{row['name']:<38} {row['title']:<18} {row['count']:>6} {row['total']:>11.4f} {row['avg']:>10.4f} {row['max']:>10.4f} {row['share']:>8.2f}"
        )
    print()

    print("== 排名前列埋点含义 ==")
    for row in rows[:top_n]:
        print(f"- {row['name']}（{row['title']}）：{row['note']}")
    print()


def print_downstair_summary(
    downstair_costs: list[float],
    downstair_results: list[dict],
    excluded_keyhole_wait_costs: list[float],
) -> None:
    print("== 下楼总流程摘要：post.downstair ==")
    if downstair_costs:
        print(f"次数        : {len(downstair_costs)}")
        print(f"累计耗时    : {sum(downstair_costs):.4f}s")
        print(f"平均耗时    : {sum(downstair_costs) / len(downstair_costs):.4f}s")
        print(f"最短耗时    : {downstair_costs[0]:.4f}s")
        print(f"中位数 p50  : {percentile(downstair_costs, 0.50):.4f}s")
        print(f"慢层 p90    : {percentile(downstair_costs, 0.90):.4f}s")
        print(f"慢层 p95    : {percentile(downstair_costs, 0.95):.4f}s")
        print(f"最慢单次    : {downstair_costs[-1]:.4f}s")
        if excluded_keyhole_wait_costs:
            print(
                f"已剔除洞穴等待: {len(excluded_keyhole_wait_costs)} 条，合计 {sum(excluded_keyhole_wait_costs):.4f}s"
            )
    else:
        print("没有找到 [timing:post.downstair] 记录。")
    print()

    print("== 下楼结果分布 ==")
    if downstair_results:
        counter = Counter(item["result"] for item in downstair_results)
        total = len(downstair_results)
        print(f"{'结果':<28} {'中文含义':<42} {'次数':>6} {'比例':>8}")
        for result, count in counter.most_common():
            meaning = RESULT_INFO.get(result, "未登记结果，查看 downstair_result 日志。")
            print(f"{result:<28} {meaning:<42} {count:>6} {count / total * 100:>7.2f}%")

        attempts = [item["attempts"] for item in downstair_results]
        print()
        print("确认楼层变化次数：")
        print(f"平均确认次数 : {sum(attempts) / len(attempts):.2f}")
        print(f"最大确认次数 : {max(attempts)}")
        attempts_counter = Counter(attempts)
        for attempt, count in sorted(attempts_counter.items()):
            print(f"  {attempt} 次确认: {count} 层，占 {count / total * 100:.2f}%")

        branch_counter = Counter(item["branch"] for item in downstair_results)
        print()
        print("下楼路径分布：")
        print(f"{'路径':<28} {'中文含义':<42} {'次数':>6} {'比例':>8}")
        for branch, count in branch_counter.most_common():
            meaning = BRANCH_INFO.get(branch, "未登记路径，查看 branch 字段。")
            print(f"{branch:<28} {meaning:<42} {count:>6} {count / total * 100:>7.2f}%")

        changed = [item for item in downstair_results if item["result"] == "changed_confirmed"]
        if changed:
            changed_attempts = [item["attempts"] for item in changed]
            print(f"成功下楼平均确认次数 : {sum(changed_attempts) / len(changed_attempts):.2f}")
    else:
        print("没有找到 [downstair_result] 记录。")
    print()


def print_downstair_stage_breakdown(stage_costs: dict[str, list[float]]) -> None:
    found = False
    print("== 下楼阶段拆解（父子埋点不要直接相加） ==")
    print(
        f"{'埋点名':<38} {'中文含义':<18} {'次数':>6} {'总耗时(s)':>11} {'均值(s)':>10} {'最大(s)':>10}"
    )
    for name in DOWNSTAIR_STAGE_ORDER:
        costs = stage_costs.get(name)
        if not costs:
            continue
        found = True
        ordered = sorted(costs)
        total = sum(ordered)
        print(
            f"{name:<38} {stage_title(name):<18} {len(ordered):>6} {total:>11.4f} {total / len(ordered):>10.4f} {ordered[-1]:>10.4f}"
        )
    if not found:
        print("没有找到详细的 post.downstair.* 计时记录。")
    print()

    if found:
        print("下楼阶段阅读提示：")
        for name in DOWNSTAIR_STAGE_ORDER:
            if name in stage_costs:
                print(f"- {name}（{stage_title(name)}）：{stage_note(name)}")
        print()


def print_interrupt_summary(interrupt_events: Counter[str]) -> None:
    print("== 中断异常统计 ==")
    total = sum(interrupt_events.values())
    if not total:
        print("没有检测到卡剧情、卡离开或卡返回。")
        print()
        return

    print(f"{'异常类型':<14} {'说明':<28} {'次数':>6} {'比例':>8}")
    for event_key, (label, _) in INTERRUPT_EVENT_PATTERNS.items():
        count = interrupt_events.get(event_key, 0)
        if not count:
            continue
        if event_key == "story_stuck":
            note = "剧情确认弹窗卡住后重新探索"
        elif event_key == "leave_stuck":
            note = "离开确认弹窗卡住后重新探索"
        else:
            note = "返回按钮/返回文本卡住后重新探索"
        print(f"{label:<14} {note:<28} {count:>6} {count / total * 100:>7.2f}%")
    print(f"合计          {'所有中断异常':<28} {total:>6} {100.0:>7.2f}%")
    print()


def print_report_header(
    log_path: Path,
    start_line: int,
    line_count: int,
    segment: dict | None = None,
    total_segments: int = 1,
) -> None:
    print(f"日志文件 : {log_path}")
    if segment:
        first_layer = segment["first_layer"]
        layer_text = first_layer if first_layer is not None else "未知"
        print(f"分段编号 : {segment['index']} / {total_segments}")
        print(f"分段标记 : {segment['marker']}")
        print(f"开始时间 : {segment['start_time']}")
        print(f"首个探索层: {layer_text}")
        print(f"统计范围 : 第 {segment['start_line']} 行 到 第 {segment['end_line']} 行")
    else:
        print(f"统计范围 : 第 {start_line} 行 到 EOF")
    print(f"参与统计行数: {line_count}")
    print()


def print_full_report(
    log_path: Path,
    lines: list[str],
    include_keyhole_wait: bool,
    top_n: int,
    start_line: int,
    segment: dict | None = None,
    total_segments: int = 1,
) -> dict:
    result = analyze(lines, include_keyhole_wait)
    print_report_header(log_path, start_line, len(lines), segment, total_segments)
    print_scope_notes(
        include_keyhole_wait,
        result["excluded_keyhole_wait_costs"],
    )
    print_stage_summary(result["stage_costs"], top_n)
    print_downstair_summary(
        result["downstair_costs"],
        result["downstair_results"],
        result["excluded_keyhole_wait_costs"],
    )
    print_interrupt_summary(result["interrupt_events"])
    print_downstair_stage_breakdown(result["stage_costs"])
    return result


def render_full_report(
    log_path: Path,
    lines: list[str],
    include_keyhole_wait: bool,
    top_n: int,
    start_line: int,
    segment: dict | None = None,
    total_segments: int = 1,
) -> tuple[str, dict]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = print_full_report(
            log_path,
            lines,
            include_keyhole_wait,
            top_n,
            start_line,
            segment,
            total_segments,
        )
    return buffer.getvalue(), result


def write_segment_reports(
    log_path: Path,
    lines: list[str],
    segments: list[dict],
    output_dir: Path,
    include_keyhole_wait: bool,
    top_n: int,
    base_start_line: int,
) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for segment in segments:
        segment_lines = lines[segment["start_offset"] : segment["end_offset"]]
        report_text, result = render_full_report(
            log_path,
            segment_lines,
            include_keyhole_wait,
            top_n,
            base_start_line,
            segment,
            len(segments),
        )
        path = segment_report_path(output_dir, segment)
        path.write_text(report_text, encoding="utf-8")
        reports.append(
            {
                "path": path,
                "segment": segment,
                "line_count": len(segment_lines),
                "downstair_count": len(result["downstair_costs"]),
                "downstair_total": sum(result["downstair_costs"]),
                "timing_stage_count": len(result["stage_costs"]),
                "story_stuck_count": result["interrupt_events"].get("story_stuck", 0),
                "leave_stuck_count": result["interrupt_events"].get("leave_stuck", 0),
                "back_stuck_count": result["interrupt_events"].get("back_stuck", 0),
            }
        )
    write_summary_report(log_path, output_dir, reports)
    return reports


def write_summary_report(log_path: Path, output_dir: Path, reports: list[dict]) -> Path:
    summary_path = output_dir / "summary.txt"
    lines = [
        f"日志文件 : {log_path}",
        f"分段数量 : {len(reports)}",
        f"报告目录 : {output_dir}",
        "",
        "== 分段报告索引 ==",
        f"{'段号':<6} {'开始时间':<19} {'首层':>6} {'行范围':<22} {'行数':>8} {'下楼次数':>8} {'卡剧情':>6} {'卡离开':>6} {'卡返回':>6} {'下楼总耗时(s)':>14} 报告文件",
    ]
    for item in reports:
        segment = item["segment"]
        first_layer = segment["first_layer"] if segment["first_layer"] is not None else "未知"
        line_span = f"{segment['start_line']}-{segment['end_line']}"
        lines.append(
            f"{segment['index']:<6} {segment['start_time']:<19} {str(first_layer):>6} {line_span:<22} {item['line_count']:>8} {item['downstair_count']:>8} {item['story_stuck_count']:>6} {item['leave_stuck_count']:>6} {item['back_stuck_count']:>6} {item['downstair_total']:>14.4f} {item['path'].name}"
        )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="分析 MaaGumballs 马尔斯战后与下楼阶段的 timing 日志，并输出中文说明。"
    )
    parser.add_argument("log_path", type=Path, help="日志文件路径")
    parser.add_argument(
        "--start-line",
        type=int,
        default=None,
        help="只分析这个 1-based 行号之后的日志",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="输出总耗时排行的前 N 个埋点",
    )
    parser.add_argument(
        "--include-keyhole-wait",
        action="store_true",
        help="把钥匙洞穴人工等待时间计入 post.downstair 总耗时",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="分段报告输出目录；默认写到日志同级的 <日志名>_timing_reports 目录",
    )
    parser.add_argument(
        "--no-auto-segment",
        action="store_true",
        help="关闭自动分段，按传入范围整体分析并输出到控制台",
    )
    parser.add_argument(
        "--force-output",
        action="store_true",
        help="即使只检测到一轮日志，也把报告写入文件",
    )
    args = parser.parse_args()

    base_start_line = args.start_line or 1
    lines = read_log_lines(args.log_path, args.start_line)
    if args.no_auto_segment:
        print_full_report(
            args.log_path,
            lines,
            args.include_keyhole_wait,
            args.top,
            base_start_line,
        )
        return

    segments = detect_log_segments(lines, base_start_line)
    should_write_files = len(segments) > 1 or args.force_output or args.output_dir is not None
    if should_write_files:
        output_dir = args.output_dir or default_output_dir(args.log_path)
        reports = write_segment_reports(
            args.log_path,
            lines,
            segments,
            output_dir,
            args.include_keyhole_wait,
            args.top,
            base_start_line,
        )
        print(f"已生成分段报告目录: {output_dir}")
        print(f"分段数量: {len(reports)}")
        print(f"索引文件: {output_dir / 'summary.txt'}")
        return

    print_full_report(
        args.log_path,
        lines,
        args.include_keyhole_wait,
        args.top,
        base_start_line,
    )


if __name__ == "__main__":
    main()
