"""把已验证结果与审核后的参考文献写入论文第一版 Markdown。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def fnum(x, digits=2):
    return f"{float(x):,.{digits}f}".replace(",", " ")


DATES = ("2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21")
PICK_INDEX = (59, 71, 83, 95, 107, 119)
PICK_LABELS = ("10:00-10:10", "12:00-12:10", "14:00-14:10",
               "16:00-16:10", "18:00-18:10", "20:00-20:10")


def md_table(headers, rows):
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *("| " + " | ".join(map(str, row)) + " |" for row in rows),
    ])


def block_cells(charge, discharge):
    return [f"{charge[s:s+24].sum():.2f}/{discharge[s:s+24].sum():.2f}" for s in range(0, 144, 24)]


def emergency_events(values, labels):
    events, i = [], 0
    while i < 144:
        if values[i] <= 1e-7:
            i += 1; continue
        j = i
        while j + 1 < 144 and values[j + 1] > 1e-7:
            j += 1
        events.append((f"{labels[i].split('-')[0]}-{labels[j].split('-')[-1]}", values[i:j+1].sum()))
        i = j + 1
    return events


def emergency_tables(dates, emergency, labels, caption):
    parts = [f"**{caption}**"]
    for day in DATES:
        i = int(np.flatnonzero(dates == day)[0])
        events = emergency_events(emergency[i], labels)
        parts.append(md_table([day + " 紧急购电时间段", "购电量/kWh"],
                              [[interval, fnum(value)] for interval, value in events] or [["无", "0"]]))
    return "\n\n".join(parts)


def q1_tables():
    frame = pd.read_csv(ROOT / "results/q1_detail.csv")
    values = frame["grid_kwh"].to_numpy()
    purchase_rows = []
    for offset in (0, 3):
        row = []
        for j in range(offset, offset + 3):
            row += [PICK_LABELS[j], fnum(values[PICK_INDEX[j]])]
        purchase_rows.append(row)
    purchase_rows.append(["全天购电量", fnum(values.sum()), "全天购电费", fnum((frame.price_yuan_per_kwh * frame.grid_kwh).sum()), "", ""])
    block = block_cells(frame.charge_kwh.to_numpy(), frame.discharge_kwh.to_numpy())
    return "\n\n".join([
        "**表6-1 指定时段购电量及全天汇总**",
        md_table(["时间段", "购电量/kWh"] * 3, purchase_rows),
        "**表6-2 储能分段充/放电量及首末储电量**",
        md_table(["时段", "充/放电量(kWh)", "时段", "充/放电量(kWh)"], [
            ["0:00-4:00", block[0], "4:00-8:00", block[1]],
            ["8:00-12:00", block[2], "12:00-16:00", block[3]],
            ["16:00-20:00", block[4], "20:00-24:00", block[5]],
            ["0:00储电量", fnum(frame.soc_start_kwh.iloc[0]), "24:00储电量", fnum(frame.soc_end_kwh.iloc[-1])],
        ]),
    ])


def annual_required_tables(npz_path, mode):
    z = np.load(npz_path, allow_pickle=True)
    dates = np.asarray(z["dates"]).astype(str)
    if mode == "q2":
        initial = effective = z["planned_grid_kwh"]
        charge, discharge = z["planned_charge_kwh"], z["planned_discharge_kwh"]
        emergency, soc0, soc1 = z["actual_emergency_kwh"], z["soc_start_kwh"], z["soc_end_kwh"]
        cost = z["planned_cost_yuan"]
        plan_caption, block_caption, emer_caption = "表7-1", "表7-2", "表7-3"
    elif mode == "q3":
        initial, effective = z["initial_grid"], z["effective_grid"]
        charge, discharge, emergency = z["charge"], z["discharge"], z["emergency"]
        soc0, soc1, cost = z["soc"][:,0], z["soc"][:,-1], z["total_cost"]
        plan_caption, block_caption, emer_caption = "表8-2", "表8-3", "表8-4"
    else:
        raise ValueError(mode)
    plan_rows, block_rows = [], []
    for day in DATES:
        i = int(np.flatnonzero(dates == day)[0])
        if mode == "q2":
            cells = [fnum(initial[i,j]) for j in PICK_INDEX]
        else:
            cells = [f"{initial[i,j]:.2f}/{effective[i,j]:.2f}" for j in PICK_INDEX]
        plan_rows.append([day, *cells, fnum(effective[i].sum()), fnum(cost[i])])
        block_rows.append([day, *block_cells(charge[i], discharge[i]), f"{soc0[i]:.2f}/{soc1[i]:.2f}"])
    plan_note = "购电量" if mode == "q2" else "0时计划量/最终有效量"
    labels = ["日期", *PICK_LABELS, "全天购电量/kWh", "全天购电费/元"]
    blocks = ["日期", "0-4时", "4-8时", "8-12时", "12-16时", "16-20时", "20-24时", "SOC(0时/24时)"]
    wb = __import__("openpyxl").load_workbook(
        ROOT / "problems/选题C_2026正式/附件/附件5/result2.xlsx", read_only=True, data_only=True
    )
    slot_labels = [str(wb.worksheets[0].cell(1, c).value) for c in range(2, 146)]
    wb.close()
    parts = [f"**{plan_caption} 指定日期、指定时段的{plan_note}及全天汇总**", md_table(labels, plan_rows),
             f"**{block_caption} 指定日期储能分段充/放电量（单元格为充电量/放电量，kWh）**", md_table(blocks, block_rows),
             emergency_tables(dates, emergency, slot_labels, f"{emer_caption} 指定日期紧急购电")]
    return "\n\n".join(parts)


def q4_tables():
    z = np.load(ROOT / "results/q4_detail.npz", allow_pickle=True)
    dates = np.asarray(z["dates"]).astype(str)
    rows = []
    for day in DATES:
        i = int(np.flatnonzero(dates == day)[0])
        rows.append([day, fnum(z["q42_total_cost"][i]), fnum(z["q42_emergency"][i].sum()),
                     fnum(z["q43_total_cost"][i]), fnum(z["q43_emergency"][i].sum())])
    return "\n\n".join(["**表9-2 波动电价下指定日期结果**",
        md_table(["日期", "Q4-2总费用/元", "Q4-2紧急购电/kWh", "Q4-3总费用/元", "Q4-3紧急购电/kWh"], rows)])


def main():
    q2 = json.loads((ROOT / "state/agent_outputs/q2_results.json").read_text(encoding="utf-8"))
    q3 = json.loads((ROOT / "state/agent_outputs/q3_results.json").read_text(encoding="utf-8"))
    q4 = json.loads((ROOT / "state/agent_outputs/q4_results.json").read_text(encoding="utf-8"))
    text = (ROOT / "paper/论文_C题_第一版草稿.md").read_text(encoding="utf-8")
    k2, k3, k4 = q2["key_results"], q3["key_results"], q4["key_results"]
    abl = q3["update_ablation"]
    labels = {"0_only": "仅0:00", "0_6": "0:00与6:00", "0_6_12": "0:00、6:00与12:00", "0_6_12_18": "0:00、6:00、12:00与18:00"}
    best_key = min(abl, key=lambda k: abl[k]["total_cost_yuan"])
    if best_key == "0_6_12_18":
        update_conclusion = "全部日内预报均具有覆盖其调整成本的净价值"
    else:
        omitted = {"0_only": "6:00、12:00、18:00", "0_6": "12:00与18:00", "0_6_12": "18:00"}[best_key]
        update_conclusion = f"{omitted}之后的新增预报不必机械触发交易，因其降低的应急费用不足以覆盖调整成本"
    q4_conclusion = (
        "日内联合更新光伏与价格信息能够明显降低紧急购电损失；完全价格信息仍有正价值，但远小于全外生信息缺失造成的成本差距"
        if k4["q4_3_causal"]["total_cost_yuan"] < k4["q4_2_causal"]["total_cost_yuan"]
        else "在本样本中日内调整交易成本抵消了信息更新收益，日前因果策略更经济"
    )
    replacements = {
        "Q1_REQUIRED_TABLES": q1_tables(),
        "Q2_REQUIRED_TABLES": annual_required_tables(ROOT / "results/q2_detail.npz", "q2"),
        "Q3_REQUIRED_TABLES": annual_required_tables(ROOT / "results/q3_detail.npz", "q3"),
        "Q4_REQUIRED_TABLES": q4_tables(),
        "Q2_TOTAL_COST": fnum(k2["actual_total_cost_yuan"]),
        "Q2_EMERGENCY": fnum(k2["emergency_purchase_kwh"]),
        "Q2_PLANNED_COST": fnum(k2["planned_cost_yuan"]),
        "Q2_EMERGENCY_COST": fnum(k2["emergency_cost_yuan"]),
        "Q2_WAPE": f"{100*q2['forecast_metrics']['WAPE']:.2f}%",
        "Q2_FIGURE_REF": "7-1",
        "Q3_BEST_UPDATE_POLICY": labels[best_key],
        "Q3_UPDATE_CONCLUSION": update_conclusion,
        "Q3_0_COST": fnum(abl["0_only"]["total_cost_yuan"]),
        "Q3_0_EMERGENCY": fnum(abl["0_only"]["emergency_energy_kwh"]),
        "Q3_0_TIME": fnum(abl["0_only"]["solve_seconds"]),
        "Q3_06_COST": fnum(abl["0_6"]["total_cost_yuan"]),
        "Q3_06_ADJ": fnum(abl["0_6"]["adjustment_cost_yuan"]),
        "Q3_06_EMERGENCY": fnum(abl["0_6"]["emergency_energy_kwh"]),
        "Q3_06_TIME": fnum(abl["0_6"]["solve_seconds"]),
        "Q3_0612_COST": fnum(abl["0_6_12"]["total_cost_yuan"]),
        "Q3_0612_ADJ": fnum(abl["0_6_12"]["adjustment_cost_yuan"]),
        "Q3_0612_EMERGENCY": fnum(abl["0_6_12"]["emergency_energy_kwh"]),
        "Q3_0612_TIME": fnum(abl["0_6_12"]["solve_seconds"]),
        "Q3_ALL_COST": fnum(abl["0_6_12_18"]["total_cost_yuan"]),
        "Q3_ALL_ADJ": fnum(abl["0_6_12_18"]["adjustment_cost_yuan"]),
        "Q3_ALL_EMERGENCY": fnum(abl["0_6_12_18"]["emergency_energy_kwh"]),
        "Q3_ALL_TIME": fnum(abl["0_6_12_18"]["solve_seconds"]),
        "Q42_COST": fnum(k4["q4_2_causal"]["total_cost_yuan"]),
        "Q43_COST": fnum(k4["q4_3_causal"]["total_cost_yuan"]),
        "Q42_PI_COST": fnum(k4["q4_2_perfect_price"]["total_cost_yuan"]),
        "Q43_PI_COST": fnum(k4["q4_3_perfect_price"]["total_cost_yuan"]),
        "Q4_ORACLE_COST": fnum(k4["full_information_oracle_lower_bound"]["total_cost_yuan"]),
        "Q42_PI_GAP": fnum(k4["q4_2_price_information_gap"]["yuan"]),
        "Q43_PI_GAP": fnum(k4["q4_3_price_information_gap"]["yuan"]),
        "Q4_CONCLUSION": q4_conclusion,
        "MAX_RESIDUAL": f"{max(q2['intermediate_results']['max_scenario_balance_residual_kwh'], k3['max_balance_residual_kwh'], k4['q4_2_causal']['max_balance_residual_kwh']):.2e}",
    }
    for key, value in replacements.items():
        text = text.replace("{{" + key + "}}", str(value))

    refs = json.loads((ROOT / "state/agent_outputs/reference_selection.json").read_text(encoding="utf-8"))
    chosen = set(refs["recommended_core_ids"])
    entries = [e for e in refs["entries"] if e["id"] in chosen]
    ref_text = "\n".join(f"[{i}] {e['gbt7714_candidate']}" for i, e in enumerate(entries, 1))
    text = text.replace("{{REFERENCES}}", ref_text)
    unresolved = [part.split("}}",1)[0] for part in text.split("{{")[1:]]
    if unresolved:
        raise RuntimeError(f"仍有未替换占位符: {unresolved}")
    output = ROOT / "paper/论文_C题_第一版.md"
    output.write_text(text, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
