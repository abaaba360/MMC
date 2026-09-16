from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r"D:\数模工作流")
OUT = ROOT / "results" / "matlab_plot_data"
OUT.mkdir(parents=True, exist_ok=True)


def export_q2() -> None:
    z = np.load(ROOT / "results" / "q2_detail.npz", allow_pickle=True)
    dates = pd.to_datetime(z["dates"])
    start = int(z["official_start_index"][0])
    soc_path = z["soc_start_kwh"][:, None] + np.cumsum(
        0.9 * z["planned_charge_kwh"] - z["planned_discharge_kwh"] / 0.9,
        axis=1,
    )
    daily = pd.DataFrame(
        {
            "date": dates[start:],
            "planned_cost_yuan": z["planned_cost_yuan"][start:],
            "emergency_cost_yuan": z["emergency_cost_yuan"][start:],
            "emergency_energy_kwh": z["actual_emergency_kwh"][start:].sum(axis=1),
            "soc_start_kwh": z["soc_start_kwh"][start:],
            "soc_end_kwh": z["soc_end_kwh"][start:],
            "soc_min_kwh": np.minimum(z["soc_start_kwh"], soc_path.min(axis=1))[start:],
            "soc_max_kwh": np.maximum(z["soc_start_kwh"], soc_path.max(axis=1))[start:],
            "soc_link_residual_kwh": np.r_[0.0, z["soc_start_kwh"][1:] - z["soc_end_kwh"][:-1]][start:],
        }
    )
    daily.to_csv(OUT / "q2_daily_summary.csv", index=False, encoding="utf-8-sig")
    monthly = daily.set_index("date").resample("ME").sum(numeric_only=True).reset_index()
    monthly.to_csv(OUT / "q2_monthly_summary.csv", index=False, encoding="utf-8-sig")

    chosen = ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"]
    parts = []
    for day in chosen:
        i = int(np.flatnonzero(dates.strftime("%Y-%m-%d") == day)[0])
        parts.append(
            pd.DataFrame(
                {
                    "date": day,
                    "interval": np.arange(144),
                    "hour": np.arange(144) / 6.0,
                    "actual_net_kw": z["actual_net_kwh"][i] * 6,
                    "forecast_net_kw": z["point_forecast_net_kwh"][i] * 6,
                    "planned_grid_kw": z["planned_grid_kwh"][i] * 6,
                    "emergency_kw": z["actual_emergency_kwh"][i] * 6,
                }
            )
        )
    pd.concat(parts, ignore_index=True).to_csv(
        OUT / "q2_representative_days.csv", index=False, encoding="utf-8-sig"
    )


def export_q3() -> None:
    report = json.loads((ROOT / "results" / "q3_results.json").read_text(encoding="utf-8"))
    order = ["0_only", "0_6", "0_6_12", "0_6_12_18"]
    labels = ["0:00", "0:00/6:00", "0:00/6:00/12:00", "0:00/6:00/12:00/18:00"]
    ab = report["update_ablation"]
    rows = []
    for key, label in zip(order, labels):
        row = dict(ab[key])
        row["key"] = key
        row["label"] = label
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUT / "q3_update_ablation.csv", index=False, encoding="utf-8-sig")

    z = np.load(ROOT / "results" / "q3_detail.npz", allow_pickle=True)
    dates = pd.to_datetime(z["dates"])
    chosen = ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"]
    origins = [0, 36, 72, 108]
    parts = []
    for day in chosen:
        i = int(np.flatnonzero(dates.strftime("%Y-%m-%d") == day)[0])
        actual_net = (
            z["effective_grid"][i]
            + z["emergency"][i]
            + z["discharge"][i]
            - z["charge"][i]
            - z["curtailment"][i]
        )
        frame = pd.DataFrame(
            {
                "date": day,
                "interval": np.arange(144),
                "hour": np.arange(144) / 6.0,
                "actual_net_kw": actual_net * 6,
                "emergency_kw": z["emergency"][i] * 6,
            }
        )
        for oi, origin in enumerate(origins):
            forecast = (z["load_forecasts"][i, oi] - z["pv_forecasts"][i, oi]) * 6
            forecast[:origin] = np.nan
            frame[f"forecast_{origin//6:02d}_kw"] = forecast
        parts.append(frame)
    pd.concat(parts, ignore_index=True).to_csv(
        OUT / "q3_representative_updates.csv", index=False, encoding="utf-8-sig"
    )


def export_q4() -> None:
    report = json.loads((ROOT / "results" / "q4_results.json").read_text(encoding="utf-8"))
    k = report["key_results"]
    rows = []
    for question, causal_key, price_key in (
        ("Q4-2", "q4_2_causal", "q4_2_perfect_price"),
        ("Q4-3", "q4_3_causal", "q4_3_perfect_price"),
    ):
        causal = float(k[causal_key]["total_cost_yuan"])
        perfect = float(k[price_key]["total_cost_yuan"])
        oracle = float(k["full_information_oracle_lower_bound"]["total_cost_yuan"])
        rows.append(
            {
                "question": question,
                "causal_cost_yuan": causal,
                "perfect_price_cost_yuan": perfect,
                "oracle_cost_yuan": oracle,
                "price_information_gap_yuan": causal - perfect,
                "price_information_gap_pct": (causal - perfect) / perfect * 100,
            }
        )
    pd.DataFrame(rows).to_csv(OUT / "q4_information_value.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    export_q2()
    export_q3()
    export_q4()
    print(OUT)


if __name__ == "__main__":
    main()
