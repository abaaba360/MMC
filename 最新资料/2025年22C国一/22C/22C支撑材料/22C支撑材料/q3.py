import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sksurv.ensemble import GradientBoostingSurvivalAnalysis
from sksurv.util import Surv
from sksurv.metrics import concordance_index_censored, integrated_brier_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from functools import lru_cache

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class SurvivalAnalysisModel:
    def __init__(self, excel_path="./附件.xlsx", csv_path="./男胎_清洗标准化.csv", output_dir="./outputs_refactored"):
        self.excel_path = excel_path
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.threshold = 0.04
        self.week_range = np.arange(10.0, 26.4, 0.5)
        self.segments_count = 4
        self.protection_target = 0.90
        self.random_seed = 42
        
        os.makedirs(self.output_dir, exist_ok=True)
        np.random.seed(self.random_seed)
        
    def convert_gestational_weeks(self, week_str):
        if pd.isna(week_str):
            return np.nan
        if isinstance(week_str, (int, float, np.integer, np.floating)):
            return float(week_str)
        
        pattern = re.compile(r"(?P<w>\d+)\s*(w|W|周)?\s*\+?\s*(?P<d>\d+)?", re.UNICODE)
        match = pattern.match(str(week_str).strip())
        
        if match:
            weeks = float(match.group("w"))
            days = match.group("d")
            days = float(days) if days is not None else 0.0
            return weeks + days / 7.0
        
        try:
            return float(str(week_str).strip())
        except:
            return np.nan
    
    def load_and_preprocess_data(self):
        if os.path.exists(self.csv_path):
            data = pd.read_csv(self.csv_path)
        else:
            if not os.path.exists(self.excel_path):
                raise FileNotFoundError("数据文件未找到")
            
            data = pd.read_excel(self.excel_path, sheet_name="男胎检测数据")
            data.columns = [str(c).strip().replace(" ", "") for c in data.columns]
            
            column_mapping = {
                "孕妇代码": "pid",
                "孕妇本次检测时的孕周（周数+天数）": "gest_weeks_raw",
                "孕妇BMI指标": "BMI",
                "Y染色体浓度，即Y染色体游离DNA片段的比例（女胎数据此列为空白）": "Y_frac",
                "Y染色体的Z值（女胎数据此列为空白）": "Y_Z",
                "孕妇年龄": "age",
                "孕妇身高": "height",
                "孕妇体重": "weight",
                "GC含量，序列中碱基G（鸟嘌呤）和C（胞嘧啶）所占的比例，是测序数据质量评估中的一个重要指标，正常GC含量范围为40%~60%，GC含量过高、过低、或分布异常可能意味着测序质量存在问题": "GC_all",
                "在参考基因组上比对的比例": "map_ratio",
                "重复读段的比例": "dup_ratio",
                "被过滤掉的读段数占总读段数的比例": "filter_ratio",
                "X染色体的Z值": "Z_X",
                "13号染色体的Z值": "Z_13",
                "18号染色体的Z值": "Z_18",
                "21号染色体的Z值": "Z_21",
                "X染色体浓度（其数值是通过生物信息学在一定假设下通过数据分析估计得出，可能出现负值）": "X_frac",
                "原始测序数据的总读段数（个）": "reads_total",
                "总读段数中唯一比对的读段数（个）": "reads_unique"
            }
            
            for old_name, new_name in column_mapping.items():
                if old_name in data.columns:
                    data.rename(columns={old_name: new_name}, inplace=True)
        
        fallback_mapping = {
            "孕妇代码": "pid", "检测孕周": "gest_weeks_raw", "孕妇BMI": "BMI",
            "Y染色体浓度": "Y_frac", "Y染色体的Z值": "Y_Z", "年龄": "age",
            "身高": "height", "体重": "weight", "GC含量": "GC_all",
            "在参考基因组上比对的比例": "map_ratio", "重复读段的比例": "dup_ratio",
            "被过滤掉读段数的比例": "filter_ratio", "X染色体的Z值": "Z_X",
            "13号染色体的Z值": "Z_13", "18号染色体的Z值": "Z_18",
            "21号染色体的Z值": "Z_21", "X染色体浓度": "X_frac",
            "原始读段数": "reads_total", "唯一比对的读段数": "reads_unique"
        }
        
        for old_name, new_name in fallback_mapping.items():
            if old_name in data.columns:
                data.rename(columns={old_name: new_name}, inplace=True)
        
        required_columns = ["pid", "gest_weeks_raw", "BMI", "Y_frac", "Y_Z", "age", "height", "weight",
                           "GC_all", "map_ratio", "dup_ratio", "filter_ratio", "Z_X", "Z_13", "Z_18", "Z_21",
                           "X_frac", "reads_total", "reads_unique"]
        
        data = data[[col for col in required_columns if col in data.columns]].copy()
        data["gest_weeks"] = data["gest_weeks_raw"].apply(self.convert_gestational_weeks)
        
        if "Y_frac" in data.columns:
            data["Y_frac"] = pd.to_numeric(data["Y_frac"], errors="coerce")
            data["Y_frac"] = data["Y_frac"].clip(lower=0.0, upper=1.0)
        
        return self.handle_missing_values(data)
    
    def handle_missing_values(self, data):
        def interpolate_group(group):
            group = group.sort_values("gest_weeks")
            return group.interpolate(method="linear", limit_direction="both")
        
        numeric_columns = ["Y_frac", "Y_Z", "age", "height", "weight", "BMI", "GC_all",
                          "map_ratio", "dup_ratio", "filter_ratio", "Z_X", "Z_13", "Z_18",
                          "Z_21", "X_frac", "reads_total", "reads_unique", "gest_weeks"]
        
        data = data.sort_values(["pid", "gest_weeks"])
        data[numeric_columns] = data.groupby("pid")[numeric_columns].apply(
            lambda g: interpolate_group(g[numeric_columns])
        ).reset_index(level=0, drop=True)
        
        data[numeric_columns] = data[numeric_columns].fillna(data[numeric_columns].median())
        return data
    
    def calculate_penalty_weights(self, week):
        if week <= 12.0:
            return 1.0
        elif week <= 27.0:
            return 3.0
        else:
            return 10.0
    
    def calculate_early_failure_probability(self, week):
        gamma = 0.25
        delta = 0.35
        prob = gamma * np.exp(-delta * max(0.0, week - 10.0))
        return float(np.clip(prob, 0.0, 1.0))
    
    def create_subject_level_events(self, data):
        def process_subject(subject_data):
            subject_data = subject_data.sort_values("gest_weeks")
            achieved = subject_data[subject_data["Y_frac"] >= self.threshold]
            
            if len(achieved) > 0:
                event_time = float(achieved["gest_weeks"].iloc[0])
                return {"time": event_time, "event": True, "last_time": float(subject_data["gest_weeks"].iloc[-1])}
            else:
                censor_time = float(subject_data["gest_weeks"].iloc[-1])
                return {"time": censor_time, "event": False, "last_time": censor_time}
        
        subject_records = []
        for patient_id, group in data.groupby("pid", as_index=False):
            event_info = process_subject(group)
            
            features = {
                "pid": patient_id,
                "time": event_info["time"],
                "event": event_info["event"],
                "BMI": float(np.median(group["BMI"])),
                "age": float(np.median(group["age"])),
                "height": float(np.median(group["height"])),
                "weight": float(np.median(group["weight"])),
                "GC_all": float(np.median(group["GC_all"])),
                "map_ratio": float(np.median(group["map_ratio"])),
                "dup_ratio": float(np.median(group["dup_ratio"])),
                "filter_ratio": float(np.median(group["filter_ratio"])),
                "Z_X": float(np.median(group["Z_X"])),
                "Z_13": float(np.median(group["Z_13"])),
                "Z_18": float(np.median(group["Z_18"])),
                "Z_21": float(np.median(group["Z_21"])),
                "X_frac": float(np.median(group["X_frac"])),
                "reads_total": float(np.median(group["reads_total"])),
                "reads_unique": float(np.median(group["reads_unique"]))
            }
            subject_records.append(features)
        
        return pd.DataFrame(subject_records)
    
    def train_survival_model(self, subject_data):
        survival_target = Surv.from_arrays(
            event=subject_data["event"].astype(bool), 
            time=subject_data["time"].astype(float)
        )
        
        feature_columns = ["BMI", "age", "height", "weight", "GC_all",
                          "map_ratio", "dup_ratio", "filter_ratio",
                          "Z_X", "Z_13", "Z_18", "Z_21", "X_frac",
                          "reads_total", "reads_unique"]
        
        features = subject_data[feature_columns].copy()
        groups = subject_data["pid"].values
        
        group_kfold = GroupKFold(n_splits=5)
        train_indices, test_indices = list(group_kfold.split(features, survival_target, groups=groups))[0]
        
        X_train, X_test = features.iloc[train_indices], features.iloc[test_indices]
        y_train, y_test = survival_target[train_indices], survival_target[test_indices]
        
        scaler = StandardScaler()
        survival_model = GradientBoostingSurvivalAnalysis(
            learning_rate=0.05,
            n_estimators=600,
            max_depth=3,
            subsample=0.7,
            random_state=self.random_seed
        )
        
        pipeline = Pipeline(steps=[("scaler", scaler), ("gbdt", survival_model)])
        pipeline.fit(X_train, y_train)
        
        evaluation_times = np.linspace(
            np.percentile(subject_data["time"], 5), 
            np.percentile(subject_data["time"], 95), 
            64
        )
        
        c_train = concordance_index_censored(y_train["event"], y_train["time"], -pipeline.predict(X_train))[0]
        c_test = concordance_index_censored(y_test["event"], y_test["time"], -pipeline.predict(X_test))[0]
        
        test_survival_functions = pipeline.named_steps["gbdt"].predict_survival_function(
            pipeline.named_steps["scaler"].transform(X_test), return_array=False
        )
        
        test_survival_matrix = np.array([[sf(t) for t in evaluation_times] for sf in test_survival_functions])
        ibs_score = integrated_brier_score(y_train, y_test, test_survival_matrix, evaluation_times)
        
        return pipeline, (c_train, c_test, ibs_score), features
    
    def calculate_group_cost(self, indices, survival_matrix):
        if len(indices) == 0:
            return np.full_like(self.week_range, np.nan), np.nan, np.nan
        
        subset_survival = survival_matrix[indices, :]
        mean_survival = np.mean(subset_survival, axis=0)
        
        penalty_weights = np.array([self.calculate_penalty_weights(w) for w in self.week_range])
        failure_probs = np.array([self.calculate_early_failure_probability(w) for w in self.week_range])
        
        adjusted_survival = mean_survival + failure_probs - mean_survival * failure_probs
        total_cost = adjusted_survival + penalty_weights
        
        optimal_index = int(np.nanargmin(total_cost))
        return total_cost, float(self.week_range[optimal_index]), float(total_cost[optimal_index])
    
    def optimize_bmi_segments(self, subject_data, survival_matrix):
        bmi_order = np.argsort(subject_data["BMI"].values)
        sorted_bmi = subject_data["BMI"].values[bmi_order]
        n_subjects = len(bmi_order)
        
        segment_costs = np.full((n_subjects, n_subjects), np.nan)
        segment_weeks = np.full((n_subjects, n_subjects), np.nan)
        
        for i in range(n_subjects):
            current_indices = []
            for j in range(i, n_subjects):
                current_indices.append(bmi_order[j])
                cost_vector, optimal_week, min_cost = self.calculate_group_cost(current_indices, survival_matrix)
                segment_costs[i, j] = min_cost
                segment_weeks[i, j] = optimal_week
        
        dp_table = np.full((self.segments_count, n_subjects), np.inf)
        predecessor = np.full((self.segments_count, n_subjects), -1, dtype=int)
        
        for j in range(n_subjects):
            dp_table[0, j] = segment_costs[0, j]
            predecessor[0, j] = -1
        
        for k in range(1, self.segments_count):
            for j in range(k, n_subjects):
                best_value = np.inf
                best_predecessor = -1
                
                for t in range(k-1, j):
                    value = dp_table[k-1, t] + segment_costs[t+1, j]
                    if value < best_value:
                        best_value = value
                        best_predecessor = t
                
                dp_table[k, j] = best_value
                predecessor[k, j] = best_predecessor
        
        segment_boundaries = []
        k, j = self.segments_count-1, n_subjects-1
        
        while k >= 0:
            t = predecessor[k, j]
            left = 0 if t == -1 else t+1
            segment_boundaries.append((left, j))
            j = t
            k -= 1
        
        segment_boundaries = segment_boundaries[::-1]
        
        segments_info = []
        for left, right in segment_boundaries:
            bmi_min = sorted_bmi[left]
            bmi_max = sorted_bmi[right]
            optimal_week = float(segment_weeks[left, right])
            
            segments_info.append({
                "idx_l": int(left), "idx_r": int(right),
                "BMI_min": float(bmi_min), "BMI_max": float(bmi_max),
                "week_star": optimal_week
            })
        
        return pd.DataFrame(segments_info), segment_boundaries, bmi_order
    
    def calculate_protective_weeks(self, segment_boundaries, bmi_order, survival_matrix):
        def find_protective_week(indices, target_probability=None):
            if target_probability is None:
                target_probability = self.protection_target
            
            if len(indices) == 0:
                return np.nan
            
            subset_survival = survival_matrix[indices, :]
            mean_survival = np.mean(subset_survival, axis=0)
            achievement_prob = 1 - mean_survival
            
            valid_weeks = achievement_prob >= target_probability
            if np.any(valid_weeks):
                return float(self.week_range[np.argmax(valid_weeks)])
            else:
                return float(self.week_range[-1])
        
        protective_weeks = []
        for left, right in segment_boundaries:
            indices = [bmi_order[t] for t in range(left, right+1)]
            protective_week = find_protective_week(indices, self.protection_target)
            protective_weeks.append(protective_week)
        
        return protective_weeks
    
    def calculate_median_survival_time(self, survival_vector, time_grid=None):
        if time_grid is None:
            time_grid = self.week_range
        
        median_index = np.argmin(np.abs(survival_vector - 0.5))
        return float(time_grid[median_index])
    
    def create_visualizations(self, subject_data, survival_matrix, segments_df, metrics):
        c_train, c_test, ibs_score = metrics
        
        predicted_medians = np.array([
            self.calculate_median_survival_time(survival_matrix[i]) 
            for i in range(len(subject_data))
        ])
        
        plt.style.use('seaborn-v0_8-pastel')
        
        fig, ax = plt.subplots(figsize=(8, 6))
        event_mask = subject_data["event"].values.astype(bool)
        
        ax.scatter(subject_data.loc[event_mask, "time"], predicted_medians[event_mask],
                  s=30, c="#87CEEB", label="事件(首次达标)", alpha=0.8)
        ax.scatter(subject_data.loc[~event_mask, "time"], predicted_medians[~event_mask],
                  s=30, facecolors='none', edgecolors="#FFB6C1", label="右删失", alpha=0.8)
        ax.plot([self.week_range[0], self.week_range[-1]], [self.week_range[0], self.week_range[-1]], 
               'k--', lw=1, alpha=0.5)
        
        ax.set_title("预测中位达标时间 vs 实际(事件/删失)")
        ax.set_xlabel("实际时间/删失时间（周）")
        ax.set_ylabel("预测中位达标时间（周）")
        ax.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "prediction_vs_actual.png"), dpi=180)
        plt.close()
        
        quantiles = [0.1, 0.5, 0.9]
        bmi_quantiles = np.quantile(subject_data["BMI"], quantiles)
        selected_indices = []
        
        for qv in bmi_quantiles:
            idx = int(np.argmin(np.abs(subject_data["BMI"].values - qv)))
            selected_indices.append(idx)
        
        fig, ax = plt.subplots(figsize=(8, 6))
        colors = ["#98FB98", "#DDA0DD", "#F0E68C"]
        
        for i, color in zip(selected_indices, colors):
            survival_curve = survival_matrix[i]
            ax.plot(self.week_range, survival_curve, color=color, lw=2,
                   label=f"BMI≈{subject_data['BMI'].iloc[i]:.1f}, pid={subject_data['pid'].iloc[i]}")
        
        ax.set_title("不同 BMI 样本的生存曲线 S(t)")
        ax.set_xlabel("孕周（周）")
        ax.set_ylabel("S(t) = 未达标概率")
        ax.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "survival_curves_by_bmi.png"), dpi=180)
        plt.close()
        
        fig, ax = plt.subplots(figsize=(9, 5))
        x_labels = [f"[{segments_df.loc[i,'BMI_min']:.1f}, {segments_df.loc[i,'BMI_max']:.1f}]" 
                   for i in range(len(segments_df))]
        x_positions = np.arange(len(segments_df))
        bar_width = 0.35
        
        ax.bar(x_positions - bar_width/2, segments_df["week_star"].values, 
              width=bar_width, color="#B0E0E6", label="均衡型最优周数")
        ax.bar(x_positions + bar_width/2, 
              segments_df[f"week_protective_p{int(self.protection_target*100):02d}"].values, 
              width=bar_width, color="#FFDAB9", 
              label=f"保障型最优周数(P≥{int(self.protection_target*100)}%)")
        
        ax.set_xticks(x_positions)
        ax.set_xticklabels(x_labels, rotation=0)
        ax.set_xlabel("BMI 分组区间")
        ax.set_ylabel("推荐检测周数（周）")
        ax.set_title("BMI 分组方案：推荐 NIPT 检测周数（均衡型 vs 保障型）")
        ax.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "bmi_group_recommendations.png"), dpi=180)
        plt.close()
        
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.axis("off")
        
        summary_text = (
            f"GBDT-Survival（GradientBoostingSurvivalAnalysis）评估摘要\n\n"
            f"Harrell's C-index (Train): {c_train:.3f}\n"
            f"Harrell's C-index (Test) : {c_test:.3f}\n"
            f"Integrated Brier Score   : {ibs_score:.3f}\n\n"
            f"参数：learning_rate=0.05, n_estimators=600, max_depth=3, subsample=0.7\n"
            f"阈值: Y浓度≥{self.threshold*100:.1f}% 视为达标；时间网格: 10–30周, 步长0.5周\n"
            f"分组: K={self.segments_count} 段（动态规划）; 保障型分位: P≥{int(self.protection_target*100)}%"
        )
        
        ax.text(0.02, 0.98, summary_text, va="top", ha="left", fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "metrics_summary.png"), dpi=180)
        plt.close()
    
    def run_analysis(self):
        data = self.load_and_preprocess_data()
        subject_data = self.create_subject_level_events(data)
        
        pipeline, metrics, features = self.train_survival_model(subject_data)
        
        standardized_features = pipeline.named_steps["scaler"].transform(features)
        survival_functions = pipeline.named_steps["gbdt"].predict_survival_function(
            standardized_features, return_array=False
        )
        
        survival_matrix = np.vstack([sf(self.week_range) for sf in survival_functions])
        
        segments_df, segment_boundaries, bmi_order = self.optimize_bmi_segments(subject_data, survival_matrix)
        protective_weeks = self.calculate_protective_weeks(segment_boundaries, bmi_order, survival_matrix)
        
        segments_df[f"week_protective_p{int(self.protection_target*100):02d}"] = protective_weeks
        
        segments_df.to_csv(os.path.join(self.output_dir, "bmi_segments_optimal.csv"), 
                          index=False, encoding="utf-8-sig")
        segments_df.to_csv(os.path.join(self.output_dir, "bmi_segments_optimal_with_protective.csv"),
                          index=False, encoding="utf-8-sig")
        
        self.create_visualizations(subject_data, survival_matrix, segments_df, metrics)
        
        return segments_df, metrics

if __name__ == "__main__":
    analyzer = SurvivalAnalysisModel()
    results, performance_metrics = analyzer.run_analysis()
    print("分析完成，结果已保存到输出目录")