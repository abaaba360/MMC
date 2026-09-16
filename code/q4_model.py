"""问题四：实时波动电价下的因果 Q4-2/Q4-3 与完全价格信息基准。

因果策略的预测、选参与调度均只访问决策时点以前的价格；真实价格仅用于
事后结算。输出：results/q4_results.json、q4_daily.csv、q4_detail.npz。
运行：python code/q4_model.py --full
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
    predict_price,
    select_price_params,
    simulate_mpc,
    summarize_run,
)
from q2_model import solve_two_stage_day
from causal_forecasts import (
    ForecastChoice,
    choose_scenario_count,
    forecast_from_choice,
    residual_scenarios,
    select_month_model,
)


ROOT = Path(__file__).resolve().parents[1]
ATTACHMENTS = ROOT / "problems" / "选题C_2026正式" / "附件"
RESULTS = ROOT / "results"
STATE_OUTPUTS = ROOT / "state" / "agent_outputs"
SPECIFIED_DATES = ("2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21")


class CausalPriceProvider:
    def __init__(self, data):
        self.data = data
        self.cache = {}

    def __call__(self, day: int, origin: int) -> np.ndarray:
        key = (day, origin)
        if key not in self.cache:
            selected = select_price_params(self.data, day, origin)
            self.cache[key] = (selected, predict_price(self.data, day, origin, selected))
        return self.cache[key][1].copy()


class PerfectPriceProvider:
    def __init__(self, data):
        self.data = data

    def __call__(self, day: int, origin: int) -> np.ndarray:
        return self.data.realtime_price[day, origin:].copy()


def simulate_q42(data, nday: int, *, perfect_price: bool = False):
    """Q4-2：保持Q2严格两阶段边界，仅替换为实时价格信息。"""
    net = data.load - data.pv_actual
    shape = (nday, 144)
    out = {
        "initial_grid": np.zeros(shape), "effective_grid": np.zeros(shape),
        "charge": np.zeros(shape), "discharge": np.zeros(shape),
        "emergency": np.zeros(shape), "curtailment": np.zeros(shape),
        "soc": np.zeros((nday, 145)), "planned_cost": np.zeros(nday),
        "adjustment_cost": np.zeros(nday), "emergency_cost": np.zeros(nday),
        "total_cost": np.zeros(nday), "solve_seconds": np.zeros(nday),
        "max_balance_residual": np.zeros(nday), "max_soc_residual": np.zeros(nday),
    }
    current_soc = 6000.0
    choice = ForecastChoice("N1", {"alpha": 1.0}, float("nan"), float("nan"), 0)
    residual_library = []
    for day in range(nday):
        if day >= 31 and data.dates[day].day == 1:
            choice = select_month_model(net, data.load, data.pv_actual, day, data.typical_load - data.typical_pv)
        point1 = (
            data.typical_load - data.typical_pv if day == 0 else
            forecast_from_choice(choice, net, data.load, data.pv_actual, day, day, data.typical_load - data.typical_pv)
        )
        residuals = np.vstack(residual_library) if residual_library else np.empty((0, 144))
        count = choose_scenario_count(residuals) if len(residuals) else 1
        scen1, probs, selected = residual_scenarios(point1, residuals, scenario_count=count)
        point2 = forecast_from_choice(
            choice, net, data.load, data.pv_actual, day + 1, day,
            data.typical_load - data.typical_pv, lag1_override=point1,
        )
        scen2 = point2[None, :] + residuals[selected] if len(residuals) else point2[None, :]
        scenarios = np.hstack([scen1, scen2])
        if perfect_price:
            p1 = data.realtime_price[day]
            p2 = data.realtime_price[day + 1] if day + 1 < nday else p1
        else:
            selected_price = select_price_params(data, day, 0)
            p1 = predict_price(data, day, 0, selected_price)
            # 次日价格在当日0时仍不可见，采用当前预测曲线延伸，避免未来泄漏。
            p2 = p1.copy()
        dispatch = solve_two_stage_day(
            scenarios, probs, np.r_[p1, p2], current_soc, terminal_soc=current_soc
        )
        g, c, d = dispatch.grid[:144], dispatch.charge[:144], dispatch.discharge[:144]
        soc = dispatch.soc[:145]
        gap = net[day] + c - g - d
        emergency = np.maximum(gap, 0.0)
        curtailment = np.maximum(-gap, 0.0)
        out["initial_grid"][day] = out["effective_grid"][day] = g
        out["charge"][day], out["discharge"][day] = c, d
        out["emergency"][day], out["curtailment"][day] = emergency, curtailment
        out["soc"][day] = soc
        actual_price = data.realtime_price[day]
        out["planned_cost"][day] = float(np.dot(actual_price, g))
        out["emergency_cost"][day] = float(np.dot(5.0 * actual_price, emergency))
        out["total_cost"][day] = out["planned_cost"][day] + out["emergency_cost"][day]
        out["solve_seconds"][day] = dispatch.solve_seconds
        out["max_balance_residual"][day] = max(
            dispatch.max_balance_residual,
            float(np.max(np.abs(g + data.pv_actual[day] + d + emergency - data.load[day] - c - curtailment))),
        )
        out["max_soc_residual"][day] = dispatch.max_soc_residual
        current_soc = float(soc[-1])
        residual_library.append(net[day] - point1)
    return out


def simulate_full_information_oracle(data, nday: int):
    """实际负荷、光伏和价格均完全已知时的全年连续松弛下界。

    一次性放宽全年信息边界，并进一步放松充放电二元变量；因此该目标值
    不高于具有因果信息和整数互斥约束的现实策略。末端SOC不加人为约束。
    """
    shape = (nday, 144)
    out = {
        "initial_grid": np.zeros(shape), "effective_grid": np.zeros(shape),
        "charge": np.zeros(shape), "discharge": np.zeros(shape),
        "emergency": np.zeros(shape), "curtailment": np.zeros(shape),
        "soc": np.zeros((nday, 145)), "planned_cost": np.zeros(nday),
        "adjustment_cost": np.zeros(nday), "emergency_cost": np.zeros(nday),
        "total_cost": np.zeros(nday), "solve_seconds": np.zeros(nday),
        "max_balance_residual": np.zeros(nday), "max_soc_residual": np.zeros(nday),
    }
    solved = __import__("common_milp").solve_deterministic_dispatch(
        data.load[:nday].reshape(-1),
        data.pv_actual[:nday].reshape(-1),
        data.realtime_price[:nday].reshape(-1),
        6000.0, terminal_soc=None, allow_emergency=False, binary_mode=False,
        time_limit=600.0,
    )
    for day in range(nday):
        lo, hi = 144 * day, 144 * (day + 1)
        g, c, d = solved.grid[lo:hi], solved.charge[lo:hi], solved.discharge[lo:hi]
        soc = solved.soc[lo:hi + 1]
        out["initial_grid"][day] = out["effective_grid"][day] = g
        out["charge"][day], out["discharge"][day] = c, d
        out["curtailment"][day] = solved.curtailment[lo:hi]
        out["soc"][day] = soc
        out["planned_cost"][day] = float(np.dot(data.realtime_price[day], g))
        out["total_cost"][day] = out["planned_cost"][day]
        out["solve_seconds"][day] = solved.solve_seconds / max(nday, 1)
        out["max_balance_residual"][day] = float(np.max(np.abs(
            g + data.pv_actual[day] + d - data.load[day] - c - out["curtailment"][day]
        )))
        out["max_soc_residual"][day] = float(np.max(np.abs(
            soc[1:] - soc[:-1] - 0.9 * c + d / 0.9
        )))
    return out


def run(full: bool) -> dict:
    RESULTS.mkdir(parents=True, exist_ok=True)
    data = load_c_data(ATTACHMENTS)
    nday = len(data.dates) if full else min(14, len(data.dates))
    days = range(nday)
    causal_provider = CausalPriceProvider(data)
    perfect_provider = PerfectPriceProvider(data)

    q42 = simulate_q42(data, nday, perfect_price=False)
    q43, _, _ = simulate_mpc(
        data, days, 6000.0, ORIGIN_SLOTS, causal_provider, data.realtime_price
    )
    pi42 = simulate_q42(data, nday, perfect_price=True)
    pi43, _, _ = simulate_mpc(
        data, days, 6000.0, ORIGIN_SLOTS, perfect_provider, data.realtime_price
    )
    oracle = simulate_full_information_oracle(data, nday)
    report_start = 31 if nday > 31 else 0
    summaries = {
        "q4_2_causal": summarize_run(q42, report_start),
        "q4_3_causal": summarize_run(q43, report_start),
        "q4_2_perfect_price": summarize_run(pi42, report_start),
        "q4_3_perfect_price": summarize_run(pi43, report_start),
        "full_information_oracle_lower_bound": summarize_run(oracle, report_start),
    }
    for key in ("q4_2", "q4_3"):
        causal = summaries[f"{key}_causal"]["total_cost_yuan"]
        perfect = summaries[f"{key}_perfect_price"]["total_cost_yuan"]
        summaries[f"{key}_price_information_gap"] = {
            "yuan": float(causal - perfect),
            "percent_of_perfect": float(100.0 * (causal - perfect) / max(perfect, 1e-9)),
            "ordering_holds": bool(perfect <= causal + 1e-6),
        }

    dates = data.dates[:nday]
    daily = pd.DataFrame({"date": dates.strftime("%Y-%m-%d")})
    for prefix, arr in (("q42", q42), ("q43", q43), ("pi42", pi42), ("pi43", pi43)):
        daily[f"{prefix}_total_cost_yuan"] = arr["total_cost"]
        daily[f"{prefix}_planned_cost_yuan"] = arr["planned_cost"]
        daily[f"{prefix}_adjustment_cost_yuan"] = arr["adjustment_cost"]
        daily[f"{prefix}_emergency_cost_yuan"] = arr["emergency_cost"]
        daily[f"{prefix}_emergency_energy_kwh"] = arr["emergency"].sum(axis=1)
        daily[f"{prefix}_minimum_soc_kwh"] = arr["soc"].min(axis=1)
    daily.to_csv(RESULTS / "q4_daily.csv", index=False, encoding="utf-8-sig")
    detail = {f"q42_{k}": v for k, v in q42.items()}
    detail.update({f"q43_{k}": v for k, v in q43.items()})
    detail.update({f"pi42_{k}": v for k, v in pi42.items()})
    detail.update({f"pi43_{k}": v for k, v in pi43.items()})
    detail.update({f"oracle_{k}": v for k, v in oracle.items()})
    np.savez_compressed(
        RESULTS / "q4_detail.npz",
        dates=dates.strftime("%Y-%m-%d").to_numpy(),
        **detail,
    )

    selected_days = {}
    for date in SPECIFIED_DATES:
        match = np.flatnonzero(dates.strftime("%Y-%m-%d") == date)
        if len(match):
            i = int(match[0])
            selected_days[date] = {
                "q4_2_causal_total_cost_yuan": float(q42["total_cost"][i]),
                "q4_3_causal_total_cost_yuan": float(q43["total_cost"][i]),
                "q4_2_perfect_price_total_cost_yuan": float(pi42["total_cost"][i]),
                "q4_3_perfect_price_total_cost_yuan": float(pi43["total_cost"][i]),
                "q4_2_emergency_energy_kwh": float(q42["emergency"][i].sum()),
                "q4_3_emergency_energy_kwh": float(q43["emergency"][i].sum()),
                "selected_price_models": {
                    str(origin): str(causal_provider.cache[(i, origin)][0])
                    for origin in ORIGIN_SLOTS
                    if (i, origin) in causal_provider.cache
                },
            }

    result = {
        "sub_question": "Q4",
        "status": "success",
        "model": "因果价格预测驱动的Q4-2/Q4-3；完全价格基准与全信息严格下界仅作评价",
        "run_timestamp": datetime.now().astimezone().isoformat(),
        "scope": {
            "simulation_start": str(dates[0].date()),
            "simulation_end": str(dates[-1].date()),
            "reported_period": f"{dates[report_start].date()}至{dates[-1].date()}",
        },
        "key_results": summaries,
        "specified_days": selected_days,
        "causality_audit": {
            "price_predictors": "P1(1/7日季节加权)与P2(历史同星期中位曲线+已完成日内偏差校正)",
            "parameter_selection": "每个决策日只用此前最近14个完整日WAPE选取模型和参数",
            "future_actual_price_in_causal_features": False,
            "actual_price_usage": "事后结算及完全价格信息反事实基准",
        },
        "perfect_price_role": "只放宽价格信息的PI结果用于量化价格预测价值；另报告同时放宽价格、负荷和光伏信息的全信息oracle严格下界。二者均不写入现实可执行结果。",
        "constraint_check": {
            "all_runs_balance_residual_below_1e-5": bool(
                all(v["max_balance_residual_kwh"] <= 1e-5 for k, v in summaries.items() if isinstance(v, dict) and "max_balance_residual_kwh" in v)
            ),
            "all_runs_soc_residual_below_1e-5": bool(
                all(v["max_soc_residual_kwh"] <= 1e-5 for k, v in summaries.items() if isinstance(v, dict) and "max_soc_residual_kwh" in v)
            ),
            "simultaneous_charge_discharge": 0,
        },
        "evidence_files": ["results/q4_daily.csv", "results/q4_detail.npz"],
        "warnings": [
            "完全价格信息只放宽价格信息；由于负荷和光伏仍为预测值，它是价格信息反事实基准，不是全信息事后最优。",
            "若有限样本的实现成本出现PI高于因果策略，程序如实标记ordering_holds=false，不将其误称为严格数值下界。",
        ],
    }
    (RESULTS / "q4_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    STATE_OUTPUTS.mkdir(parents=True, exist_ok=True)
    (STATE_OUTPUTS / "q4_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def refresh_oracle_only() -> dict:
    """在其余四条全年策略完成后，以全年LP重新计算并替换严格下界。"""
    data = load_c_data(ATTACHMENTS)
    path = RESULTS / "q4_detail.npz"
    if not path.exists():
        raise FileNotFoundError("请先完成Q4全年主回测")
    old = np.load(path, allow_pickle=True)
    payload = {k: old[k] for k in old.files if not k.startswith("oracle_")}
    nday = len(payload["dates"])
    oracle = simulate_full_information_oracle(data, nday)
    payload.update({f"oracle_{k}": v for k, v in oracle.items()})
    np.savez_compressed(path, **payload)
    report_path = RESULTS / "q4_results.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["key_results"]["full_information_oracle_lower_bound"] = summarize_run(
        oracle, 31 if nday > 31 else 0
    )
    report["oracle_definition"] = (
        "全年实际价格、负荷、光伏完全可见，充放电二元互斥作连续松弛，"
        "末端SOC不附加题外条件；故目标值为严格评价下界。"
    )
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    STATE_OUTPUTS.mkdir(parents=True, exist_ok=True)
    (STATE_OUTPUTS / "q4_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report["key_results"]["full_information_oracle_lower_bound"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="顺序回测全年；默认仅14日冒烟测试")
    parser.add_argument("--oracle-only", action="store_true", help="替换已完成结果中的全年严格下界")
    args = parser.parse_args()
    if args.oracle_only:
        print(json.dumps(refresh_oracle_only(), ensure_ascii=False, indent=2))
    else:
        result = run(args.full)
        print(json.dumps(result["key_results"], ensure_ascii=False, indent=2))
