"""问题三：0/6/12/18 时四次光伏预测驱动的确定性 MILP-MPC。

输入：附件2实际负荷/光伏、附件3分时发布光伏预测、附件1固定电价。
输出：results/q3_results.json、q3_daily.csv、q3_detail.npz。
运行：python code/q3_model.py --full --ablation
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from q34_helpers import (
    ORIGIN_SLOTS,
    load_c_data,
    select_load_params,
    simulate_mpc,
    summarize_run,
)


ROOT = Path(__file__).resolve().parents[1]
ATTACHMENTS = ROOT / "problems" / "选题C_2026正式" / "附件"
RESULTS = ROOT / "results"
STATE_OUTPUTS = ROOT / "state" / "agent_outputs"
SPECIFIED_DATES = ("2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21")


def _price_provider(data):
    return lambda day, origin: data.fixed_price[origin:].copy()


def _version_npz(versions, nday: int):
    grid = np.full((nday, 4, 144), np.nan)
    load_hat = np.full((nday, 4, 144), np.nan)
    pv_hat = np.full((nday, 4, 144), np.nan)
    for row, day_record in enumerate(versions):
        for ver in day_record["versions"]:
            oi = ORIGIN_SLOTS.index(ver["origin"])
            origin = ver["origin"]
            grid[row, oi, origin:] = ver["new_grid"]
            load_hat[row, oi, origin:] = ver["load_forecast"]
            pv_hat[row, oi, origin:] = ver["pv_forecast"]
    return grid, load_hat, pv_hat


def run(full: bool, ablation: bool) -> dict:
    RESULTS.mkdir(parents=True, exist_ok=True)
    data = load_c_data(ATTACHMENTS)
    nday = len(data.dates) if full else min(14, len(data.dates))
    days = range(nday)
    arrays, _, versions = simulate_mpc(
        data,
        days,
        6000.0,
        ORIGIN_SLOTS,
        _price_provider(data),
        np.tile(data.fixed_price, (len(data.dates), 1)),
        keep_versions=True,
    )
    report_start = 31 if nday > 31 else 0
    main_summary = summarize_run(arrays, report_start)

    comparisons = {"0_6_12_18": main_summary}
    if ablation:
        for name, origins in {
            "0_only": (0,),
            "0_6": (0, 36),
            "0_6_12": (0, 36, 72),
        }.items():
            comp, _, _ = simulate_mpc(
                data,
                days,
                6000.0,
                origins,
                _price_provider(data),
                np.tile(data.fixed_price, (len(data.dates), 1)),
            )
            comparisons[name] = summarize_run(comp, report_start)

    dates = data.dates[:nday]
    daily = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "planned_cost_yuan": arrays["planned_cost"],
            "adjustment_cost_yuan": arrays["adjustment_cost"],
            "emergency_cost_yuan": arrays["emergency_cost"],
            "total_cost_yuan": arrays["total_cost"],
            "emergency_energy_kwh": arrays["emergency"].sum(axis=1),
            "grid_energy_kwh": arrays["effective_grid"].sum(axis=1),
            "minimum_soc_kwh": arrays["soc"].min(axis=1),
            "solve_seconds": arrays["solve_seconds"],
        }
    )
    daily.to_csv(RESULTS / "q3_daily.csv", index=False, encoding="utf-8-sig")
    grid_versions, load_forecasts, pv_forecasts = _version_npz(versions, nday)
    np.savez_compressed(
        RESULTS / "q3_detail.npz",
        dates=dates.strftime("%Y-%m-%d").to_numpy(),
        **arrays,
        grid_versions=grid_versions,
        load_forecasts=load_forecasts,
        pv_forecasts=pv_forecasts,
    )

    selected_days = {}
    for date in SPECIFIED_DATES:
        match = np.flatnonzero(dates.strftime("%Y-%m-%d") == date)
        if len(match):
            i = int(match[0])
            selected_days[date] = {
                "planned_cost_yuan": float(arrays["planned_cost"][i]),
                "adjustment_cost_yuan": float(arrays["adjustment_cost"][i]),
                "emergency_cost_yuan": float(arrays["emergency_cost"][i]),
                "total_cost_yuan": float(arrays["total_cost"][i]),
                "emergency_energy_kwh": float(arrays["emergency"][i].sum()),
                "minimum_soc_kwh": float(arrays["soc"][i].min()),
                "load_predictor_params": list(select_load_params(data, i)),
            }

    result = {
        "sub_question": "Q3",
        "status": "success" if main_summary["max_balance_residual_kwh"] <= 1e-5 and main_summary["max_soc_residual_kwh"] <= 1e-5 else "failed",
        "model": "确定性MILP-MPC（0/6/12/18滚动更新）",
        "run_timestamp": datetime.now().astimezone().isoformat(),
        "scope": {
            "simulation_start": str(dates[0].date()),
            "simulation_end": str(dates[-1].date()),
            "reported_period": (
                f"{dates[report_start].date()}至{dates[-1].date()}" if nday else ""
            ),
        },
        "settlement_rule": {
            "initial_plan": "p*G0",
            "increase": "+1.5*p*max(Gnew-Gold,0)",
            "decrease": "-0.5*p*max(Gold-Gnew,0)",
            "emergency": "+5*p*Ractual",
            "comparison_base": "immediately_previous_effective_plan",
        },
        "key_results": main_summary,
        "update_ablation": comparisons,
        "specified_days": selected_days,
        "constraint_check": {
            "all_passed": bool(
                main_summary["max_balance_residual_kwh"] <= 1e-5
                and main_summary["max_soc_residual_kwh"] <= 1e-5
                and main_summary["minimum_soc_kwh"] >= 1200 - 1e-5
                and main_summary["maximum_soc_kwh"] <= 10800 + 1e-5
            ),
            "simultaneous_charge_discharge": 0,
        },
        "risk_enhancement": {
            "retained": False,
            "reason": "场景/CVaR并非题面必需；按预先锁定门槛，未取得九指标滚动样本外显著改善前不进入主模型。",
        },
        "evidence_files": ["results/q3_daily.csv", "results/q3_detail.npz"],
        "warnings": [
            "日前至日内负荷预测参数按每个决策日前14个完整日的执行段WAPE自动选择；早期样本不足时使用典型日先验。",
            "Q3逐日时域不人为重置SOC；上一日末SOC严格传递至下一日。",
        ],
    }
    (RESULTS / "q3_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    STATE_OUTPUTS.mkdir(parents=True, exist_ok=True)
    (STATE_OUTPUTS / "q3_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="顺序回测全年；默认仅14日冒烟测试")
    parser.add_argument("--ablation", action="store_true", help="比较0、0/6、0/6/12和四次更新")
    args = parser.parse_args()
    summary = run(args.full, args.ablation)
    print(json.dumps(summary["key_results"], ensure_ascii=False, indent=2))
