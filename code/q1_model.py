"""问题一正式求解：确定性MILP主模型与LP连续松弛对照。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from common_milp import solve_deterministic_dispatch
from data_loader import ROOT, load_q1


def _summary(result) -> dict:
    return {
        "objective_yuan": float(result.objective),
        "grid_kwh": float(result.grid.sum()),
        "charge_kwh": float(result.charge.sum()),
        "discharge_kwh": float(result.discharge.sum()),
        "curtailment_kwh": float(result.curtailment.sum()),
        "soc_start_kwh": float(result.soc[0]),
        "soc_end_kwh": float(result.soc[-1]),
        "soc_min_kwh": float(result.soc.min()),
        "soc_max_kwh": float(result.soc.max()),
        "simultaneous_intervals": int(np.sum((result.charge > 1e-7) & (result.discharge > 1e-7))),
        "max_balance_residual_kwh": float(result.max_balance_residual),
        "max_soc_residual_kwh": float(result.max_soc_residual),
        "solve_seconds": float(result.solve_seconds),
        "success": bool(result.success),
        "solver_message": result.message,
    }


def main() -> None:
    data = load_q1()
    kwargs = dict(
        load_kwh=data["load_kwh"], pv_kwh=data["pv_kwh"], price=data["price"],
        initial_soc=6000.0, terminal_soc=6000.0, allow_emergency=False,
    )
    milp_result = solve_deterministic_dispatch(**kwargs, binary_mode=True)
    lp_result = solve_deterministic_dispatch(**kwargs, binary_mode=False)

    selected_labels = ["10:00-10:10", "12:00-12:10", "14:00-14:10", "16:00-16:10", "18:00-18:10", "20:00-20:10"]
    # 同序号对齐下，10:00-10:10对应附件第60项（数组下标59），其后每2小时增加12项。
    selected_indices = [59, 71, 83, 95, 107, 119]
    selected = {
        label: float(milp_result.grid[idx])
        for label, idx in zip(selected_labels, selected_indices)
    }
    blocks = []
    for start in range(0, 144, 24):
        blocks.append({
            "interval": f"{start // 6}:00-{(start + 24) // 6}:00",
            "charge_kwh": float(milp_result.charge[start:start + 24].sum()),
            "discharge_kwh": float(milp_result.discharge[start:start + 24].sum()),
            "soc_end_kwh": float(milp_result.soc[start + 24]),
        })

    no_storage_cost = float(np.dot(data["price"], np.maximum(data["load_kwh"] - data["pv_kwh"], 0.0)))
    report = {
        "question": "Q1",
        "model": "deterministic_MILP_with_charge_discharge_mutex",
        "status": "success",
        "source_files": ["problems/选题C_2026正式/附件/附件1.xlsx"],
        "time_step_hours": 1.0 / 6.0,
        "alignment_rule": "附件与结果模板按同序号对应，不循环平移",
        "milp": _summary(milp_result),
        "lp_relaxation": _summary(lp_result),
        "lp_lower_bound_gap_yuan": float(milp_result.objective - lp_result.objective),
        "no_storage_baseline_cost_yuan": no_storage_cost,
        "cost_saving_vs_no_storage_yuan": float(no_storage_cost - milp_result.objective),
        "cost_saving_rate": float((no_storage_cost - milp_result.objective) / no_storage_cost),
        "selected_interval_grid_kwh": selected,
        "four_hour_blocks": blocks,
        "validation": {
            "balance_residual_le_1e-6": bool(milp_result.max_balance_residual <= 1e-6),
            "soc_residual_le_1e-6": bool(milp_result.max_soc_residual <= 1e-6),
            "soc_bounds": bool(milp_result.soc.min() >= 1200 - 1e-6 and milp_result.soc.max() <= 10800 + 1e-6),
            "terminal_soc": bool(abs(milp_result.soc[-1] - 6000) <= 1e-6),
            "no_simultaneous": bool(np.all((milp_result.charge <= 1e-7) | (milp_result.discharge <= 1e-7))),
            "lp_lower_bound": bool(lp_result.objective <= milp_result.objective + 1e-6),
        },
        "claims": [
            {
                "claim_id": "Q1-COST",
                "value": float(milp_result.objective),
                "unit": "元/日",
                "code": "code/q1_model.py",
                "data": "problems/选题C_2026正式/附件/附件1.xlsx",
            }
        ],
    }
    report["status"] = "success" if all(report["validation"].values()) else "failed"

    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    details = pd.DataFrame({
        "slot": np.arange(1, 145), "time": data["time"], "price_yuan_per_kwh": data["price"],
        "load_kwh": data["load_kwh"], "pv_kwh": data["pv_kwh"], "grid_kwh": milp_result.grid,
        "charge_kwh": milp_result.charge, "discharge_kwh": milp_result.discharge,
        "curtailment_kwh": milp_result.curtailment, "soc_start_kwh": milp_result.soc[:-1],
        "soc_end_kwh": milp_result.soc[1:],
    })
    details.to_csv(out_dir / "q1_detail.csv", index=False, encoding="utf-8-sig")
    result_path = ROOT / "state" / "agent_outputs" / "q1_results.json"
    result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
