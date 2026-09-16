"""记录参赛队对AI工具使用详情的真实性确认。

本脚本只写入队伍明确授权的确认；confirmed_at 取实际执行时刻。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "state" / "agent_outputs" / "ai_usage_summary.json"


def main() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    truth = summary.setdefault("truthfulness_confirmation", {})
    truth["confirmed_by_team"] = True
    truth["confirmed_at"] = datetime.now().astimezone().isoformat()
    truth["statement"] = (
        "参赛队已核对AI工具使用台账与实际使用过程，确认所列工具名称、版本、"
        "使用目的与环节、交互方式、采纳与核验情况真实完整，无隐瞒、无虚假陈述。"
    )
    truth["confirmed_via"] = "队伍成员在正式赛题工作流中明确确认并授权记录"
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(truth, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
