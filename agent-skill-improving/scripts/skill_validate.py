#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
---
title: "Skill Compliance Validator"
name: "agent-skill-improving"
description: "Agent Swarm 技能合規檢查器。檢查新技能是否違反 23 項已知問題，並提供解決策略。"
version: "v1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-22T01:02:00+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
file_mapping:
  - local_path: "{baseDir}/scripts/skill_validate.py"
    github_path: "agent-skill-improving/scripts/skill_validate.py"
---

skill_validate.py v1.0.0
Agent Swarm 技能合規檢查器
檢查「新技能」是否違反 23 項已知問題，並提供解決策略

用法:
    python skill_validate.py --skill-dir ./agent-xxx/ [--strict] [--report-path ./report.md]
    python skill_validate.py --file ./SKILL.md [--strict]

作者: Kevin Lin (Agent Swarm Architecture)
版本: v1.0.0
日期: 2026-05-22
"""

import os
import sys
import re
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

__version__ = "1.0.0"

# ============================================================
# 23 項已知問題規則庫（對齊 AGENT_SWARM_SUMMARY_20260511）
# ============================================================

RULES = [
    {
        "id": "AGENT-001",
        "ref": "#1",
        "severity": "CRITICAL",
        "category": "conversation-mode",
        "title": "對話記錄遺漏",
        "description": "畫面顯示內容未完整記錄到 conversation.md",
        "fix": "在技能中強制引用 agent-conversation-mode，每次動作後執行對話備份。腳本必須調用 conversation_append.py。",
    },
    {
        "id": "AGENT-002",
        "ref": "#2",
        "severity": "CRITICAL",
        "category": "planning",
        "title": "輸出路徑錯誤",
        "description": "檔案輸出使用家目錄（~ / /home/）而非 user skill assets 目錄",
        "fix": "統一使用相對路徑 `user skill assets/` 或 `./assets/`，禁止絕對路徑。腳本必須接收 `--output-dir` 參數。",
    },
    {
        "id": "AGENT-003",
        "ref": "#3",
        "severity": "CRITICAL",
        "category": "coordination-mode",
        "title": "P0 禁止清單來源不明",
        "description": "P0 禁止清單未從 SKILL.CORRECTIONS.md 提取，來源不明",
        "fix": "委任書必須引用 SKILL.CORRECTIONS.md 作為 P0 禁止清單來源。腳本 create_appointment.py 必須讀取該檔案。",
    },
    {
        "id": "AGENT-004",
        "ref": "#4",
        "severity": "CRITICAL",
        "category": "planning",
        "title": "checklist 未累積追加",
        "description": "checklist.md 非單一累積檔案，每次覆蓋而非追加",
        "fix": "checklist 必須採用追加模式（a+），新舊版本共存。腳本 generate_checklist.py 必須使用追加寫入。",
    },
    {
        "id": "AGENT-005",
        "ref": "#5",
        "severity": "CRITICAL",
        "category": "coordination-mode",
        "title": "任命書過於簡陋",
        "description": "任命書缺少專家模擬、驗察需求、注意事項等欄位",
        "fix": "任命書必須包含 8 個欄位：原始需求、任務性質、目標、P0 禁止清單、專家模擬、驗察需求、注意事項、家族手冊。",
    },
    {
        "id": "AGENT-006",
        "ref": "#6",
        "severity": "CRITICAL",
        "category": "conversation-mode",
        "title": "誤寫入 memory.md",
        "description": "對話內容誤寫入 memory.md 而非 conversation.md",
        "fix": "嚴格區分：memory.md = 長期記憶（用戶偏好），conversation.md = 對話記錄（每次互動）。禁止混用。",
    },
    {
        "id": "AGENT-007",
        "ref": "#7",
        "severity": "CRITICAL",
        "category": "planning",
        "title": "子任務描述過籠統",
        "description": "子任務描述未達 30 字，未使用腳本生成",
        "fix": "子任務描述必須 ≥30 字，且必須通過 generate_checklist.py 腳本生成，禁止手寫。",
    },
    {
        "id": "AGENT-008",
        "ref": "#8",
        "severity": "CRITICAL",
        "category": "planning",
        "title": "未引用 skill-acquiring",
        "description": "計劃階段未查詢現有成熟技能，憑空創造",
        "fix": "計劃階段步驟 3 必須強制調用 agent-skill-acquiring，查詢現有技能後才允許創建新技能。",
    },
    {
        "id": "AGENT-009",
        "ref": "#9",
        "severity": "CRITICAL",
        "category": "coordination-mode",
        "title": "委任素材不足",
        "description": "委任時缺少 P0 清單、專家模擬、驗察需求等素材",
        "fix": "委任必須附帶 8 項素材：原始需求、任務性質、目標、P0 清單、專家模擬、驗察需求、注意事項、家族手冊。",
    },
    {
        "id": "AGENT-010",
        "ref": "#10",
        "severity": "LOW",
        "category": "通用",
        "title": "累積追加機制未聲明",
        "description": "累積型追加機制未在文件中明確聲明",
        "fix": "在 README.md 中明確聲明「本技能採用累積追加機制，新舊版本共存，禁止覆蓋」。",
    },
    {
        "id": "AGENT-011",
        "ref": "#11",
        "severity": "CRITICAL",
        "category": "conversation-mode",
        "title": "誤會記憶與對話",
        "description": "誤將「記憶」理解為需要匯報的內容",
        "fix": "記憶（memory）= 內部狀態，不用匯報。對話（conversation）= 外部記錄，必須備份。禁止混淆。",
    },
    {
        "id": "AGENT-012",
        "ref": "#12",
        "severity": "CRITICAL",
        "category": "conversation-mode",
        "title": "更新工作記憶混淆",
        "description": "「更新工作記憶」被誤解為「記錄對話」",
        "fix": "「更新工作記憶」= 更新 memory.md（長期偏好）。「記錄對話」= 追加 conversation.md（每次互動）。術語必須精確。",
    },
    {
        "id": "AGENT-013",
        "ref": "#13",
        "severity": "CRITICAL",
        "category": "coordination-mode",
        "title": "委任流程混亂",
        "description": "無腳本銜接委任流程，產出文件散落各處",
        "fix": "委任流程必須腳本化：create_appointment.py（發起）→ 執行 → complete_appointment.py（收尾）。產出統一放到 skill assets/。",
    },
    {
        "id": "AGENT-014",
        "ref": "#14",
        "severity": "MEDIUM",
        "category": "planning / evaluating",
        "title": "缺少 SUGGESTION.md",
        "description": "缺少下一步具體框架的 SUGGESTION.md 雙向累積機制",
        "fix": "每個 Mission 節點必須配備 SUGGESTION.md：Planner/Evaluator/Generator/Finishing 四向累積，自己不建議自己。",
    },
    {
        "id": "AGENT-015",
        "ref": "#15",
        "severity": "MEDIUM",
        "category": "evaluating",
        "title": "無問題分類 column",
        "description": "評估報告無問題分類欄位（計劃/評估/執行問題）",
        "fix": "EVALUATOR_REPORT 必須包含三欄問題分類：計劃問題（Planner）、評估問題（Evaluator）、執行問題（Generator）。",
    },
    {
        "id": "AGENT-016",
        "ref": "#16",
        "severity": "MEDIUM",
        "category": "evaluating",
        "title": "evaluator.md 臨時創造物",
        "description": "評估報告使用臨時名稱 evaluator.md，未使用 EVALUATOR_REPORT 規範",
        "fix": "統一命名為 EVALUATOR_REPORT_{時間戳}.md，8 個強制欄位。禁止臨時命名 evaluator.md。",
    },
    {
        "id": "AGENT-017",
        "ref": "#17",
        "severity": "MEDIUM",
        "category": "crafting",
        "title": "未強制載入 skill-acquiring/improving",
        "description": "Generator 執行前未查詢 skill-acquiring 或 skill-improving",
        "fix": "家族手冊必須包含 5 項：SOUL.md、agent-bootstrap、agent-conversation-mode、agent-coordination-mode、agent-skill-acquiring。",
    },
    {
        "id": "AGENT-018",
        "ref": "#18",
        "severity": "MEDIUM",
        "category": "crafting",
        "title": "委任素材不足（任務性質/目標）",
        "description": "委任書缺少任務性質與目標描述欄位",
        "fix": "委任書必須包含「任務性質」（新增/修改/優化/調查/整合）與「目標描述」（可驗證標準）。",
    },
    {
        "id": "AGENT-019",
        "ref": "#19",
        "severity": "MEDIUM",
        "category": "crafting",
        "title": "技術錯誤未標記於 checklist",
        "description": "執行階段發現的技術錯誤未標記在 checklist 中",
        "fix": "發現技術錯誤時，必須在 checklist 標記「執行問題」，記錄 CORRECTION.md，輸出 [EXECUTION-ISSUE] 標籤。",
    },
    {
        "id": "AGENT-020",
        "ref": "#20",
        "severity": "MEDIUM",
        "category": "finishing",
        "title": "路徑侵入家目錄",
        "description": "輸出文件寫入家目錄而非 user skill assets",
        "fix": "統一使用 `user skill assets/` 相對路徑，禁止絕對路徑。腳本必須驗證輸出路徑。",
    },
    {
        "id": "AGENT-021",
        "ref": "#21",
        "severity": "CRITICAL",
        "category": "planning",
        "title": "六欄位未下沉到子任務",
        "description": "最終六個欄位未下沉到每個子任務層級",
        "fix": "最終六欄（狀態/負責人/產出/驗收標準/風險/備註）必須下沉到每個子任務，不能只在頂層出現。",
    },
    {
        "id": "AGENT-022",
        "ref": "#22",
        "severity": "MEDIUM",
        "category": "finishing",
        "title": "無相對路徑約束",
        "description": "檔案名稱大小寫不一致，無相對路徑約束",
        "fix": "統一小寫命名（checklist.md 而非 CHECKLIST.md），使用相對路徑，macOS/Linux/Windows 大小寫敏感統一。",
    },
    {
        "id": "AGENT-023",
        "ref": "#23",
        "severity": "MEDIUM",
        "category": "finishing",
        "title": "下載連結失效",
        "description": "提供檔案路徑文字而非可下載連結",
        "fix": "平台檢測後提供可點擊連結：Kimi 用 sandbox:///，OpenClaw 用 deliver_attachments。禁止只給路徑文字。",
    },
]

# ============================================================
# 架構決策紅線（不可動搖）
# ============================================================

ARCHITECTURE_RULES = [
    {
        "id": "ARCH-001",
        "title": "SKILL.md 定位錯誤",
        "description": "SKILL.md 必須是給 LLM 直接執行的指令檔案，非人類說明書",
        "fix": "README.md = 人類可讀說明書。SKILL.md = LLM 執行指令集。禁止混用。",
    },
    {
        "id": "ARCH-002",
        "title": "frontmatter 多行折疊",
        "description": "frontmatter description 使用 > 多行折疊語法",
        "fix": "frontmatter description 強制單行，禁止 > 多行折疊。WorkBuddy 不解析 > 語法。",
    },
    {
        "id": "ARCH-003",
        "title": "檔案命名違規",
        "description": "檔案名稱使用中劃線或下劃線分隔",
        "fix": "統一使用點號分隔（xxx.yyy.zzz.ext），禁止中劃線（-）或下劃線（_）。",
    },
    {
        "id": "ARCH-004",
        "title": "身份分流缺失",
        "description": "frontmatter 後第一行未進行身份硬分流（主/僕/用戶）",
        "fix": "frontmatter 後第一行必須硬分流身份：「主。」= 主人視角，「僕。」= 僕人視角，「用戶」= 通用技能。",
    },
    {
        "id": "ARCH-005",
        "title": "層級限制違反",
        "description": "未聲明硬性兩層限制，第三層需申請",
        "fix": "必須聲明「硬性兩層，第三層需申請，禁止第四層」。",
    },
    {
        "id": "ARCH-006",
        "title": "家族手冊缺失",
        "description": "未強制載入 agent-harness-engineering 技能包",
        "fix": "Sub-Agent 必須強制載入完整 agent-harness-engineering 技能包。",
    },
    {
        "id": "ARCH-007",
        "title": "口訣條件反射缺失",
        "description": "未包含口訣條件反射機制",
        "fix": "必須包含對應口訣：Planner=拆評委迭，Evaluator=評記委迭，Generator=想批執記，Finishing=收尾交付。",
    },
    {
        "id": "ARCH-008",
        "title": "防呆機制缺失",
        "description": "未包含 8 條紅線 + 6 種異常 + 版本鎖定",
        "fix": "必須包含防呆機制：8 條紅線 + 6 種異常處理 + LOCK PERMANENT 版本鎖定。",
    },
]

# ============================================================
# 核心類別
# ============================================================

class SkillValidator:
    """技能合規檢查器"""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.violations = []
        self.warnings = []
        self.passed = []

    def validate_file(self, filepath):
        """驗證單一檔案"""
        content = filepath.read_text(encoding="utf-8")
        meta = self._extract_frontmatter(content)

        # 檢查 23 項問題
        for rule in RULES:
            try:
                violated = rule["check"](content, meta)
            except Exception as e:
                violated = False
                self.warnings.append({"rule_id": rule["id"], "message": f"規則檢查異常: {e}"})

            if violated:
                self.violations.append({
                    "rule_id": rule["id"],
                    "ref": rule["ref"],
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "title": rule["title"],
                    "description": rule["description"],
                    "fix": rule["fix"],
                    "file": str(filepath),
                })
            else:
                self.passed.append(rule["id"])

        # 檢查架構紅線
        for rule in ARCHITECTURE_RULES:
            try:
                violated = rule["check"](content)
            except Exception:
                violated = False

            if violated:
                self.violations.append({
                    "rule_id": rule["id"],
                    "ref": "ARCH",
                    "severity": "CRITICAL",
                    "category": "架構",
                    "title": rule["title"],
                    "description": rule["description"],
                    "fix": rule["fix"],
                    "file": str(filepath),
                })

        # 檔名檢查（ARCH-003）
        filename = filepath.name
        if "_" in filename or "-" in filename:
            self.violations.append({
                "rule_id": "ARCH-003",
                "ref": "ARCH",
                "severity": "CRITICAL",
                "category": "架構",
                "title": "檔案命名違規",
                "description": f"檔案名稱 '{filename}' 使用中劃線或下劃線分隔",
                "fix": "統一使用點號分隔（xxx.yyy.zzz.ext），禁止中劃線（-）或下劃線（_）。",
                "file": str(filepath),
            })

        return self.violations, self.warnings

    def validate_directory(self, skill_dir):
        """驗證技能目錄"""
        if not skill_dir.exists():
            raise FileNotFoundError(f"技能目錄不存在: {skill_dir}")

        # 檢查必要檔案結構
        required_files = [
            "README.md",
            "SKILL.md",
        ]
        for req in required_files:
            req_path = skill_dir / req
            if not req_path.exists():
                self.violations.append({
                    "rule_id": "STRUCT-001",
                    "ref": "STRUCT",
                    "severity": "CRITICAL",
                    "category": "結構",
                    "title": f"缺少必要檔案: {req}",
                    "description": f"技能目錄必須包含 {req}",
                    "fix": f"建立 {req} 檔案。",
                    "file": str(req_path),
                })

        # 檢查 scripts 目錄（可選但建議）
        scripts_dir = skill_dir / "scripts"
        if scripts_dir.exists():
            for py_file in scripts_dir.glob("*.py"):
                self.validate_file(py_file)

        # 檢查 SKILL.md 檔案
        for skill_md in skill_dir.rglob("SKILL.md"):
            self.validate_file(skill_md)

        # 檢查 SUGGESTION.md（Mission 節點必須有）
        if re.search(r'mission-(planning|evaluating|crafting|finishing)', str(skill_dir), re.I):
            suggestion = skill_dir / "assets" / "SUGGESTION.md"
            if not suggestion.exists():
                self.violations.append({
                    "rule_id": "AGENT-014-B",
                    "ref": "#14",
                    "severity": "MEDIUM",
                    "category": "Mission Pipeline",
                    "title": "缺少 SUGGESTION.md",
                    "description": "Mission 節點必須配備 SUGGESTION.md 雙向累積機制",
                    "fix": "建立 assets/SUGGESTION.md，實現四向累積（P/E/G/F）。",
                    "file": str(skill_dir / "assets/SUGGESTION.md"),
                })

        return self.violations, self.warnings

    def _extract_frontmatter(self, content):
        """提取 frontmatter"""
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not match:
            return {}
        fm_text = match.group(1)
        meta = {}
        for line in fm_text.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                meta[key.strip()] = val.strip()
        return meta

    def generate_report(self, output_path=None):
        """生成檢查報告（Markdown 格式）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        lines = [
            f"# SKILL VALIDATION REPORT — {timestamp}",
            "",
            f"**檢查器版本**: skill_validate.py v{__version__}",
            f"**檢查時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**嚴格模式**: {'啟用' if self.strict else '未啟用'}",
            "",
            "---",
            "",
            "## 一、檢查摘要",
            "",
            "| 項目 | 數量 |",
            "|:---|---:|",
            f"| 違規總數 | {len(self.violations)} |",
            f"| 警告總數 | {len(self.warnings)} |",
            f"| 通過規則 | {len(self.passed)} |",
            "",
            "---",
            "",
            "## 二、違規明細",
            "",
        ]

        if not self.violations:
            lines.append("✅ **無違規項目。技能通過合規檢查。**")
        else:
            for v in self.violations:
                lines.append(f"### {v['rule_id']} ({v['ref']}) — {v['title']}")
                lines.append("")
                lines.append(f"- **嚴重度**: {v['severity']}")
                lines.append(f"- **分類**: {v['category']}")
                lines.append(f"- **描述**: {v['description']}")
                lines.append(f"- **檔案**: `{v['file']}`")
                lines.append(f"- **解決策略**: {v['fix']}")
                lines.append("")

        lines.extend(["", "---", "", "## 三、警告明細", ""])
        if not self.warnings:
            lines.append("✅ **無警告。**")
        else:
            for w in self.warnings:
                lines.append(f"- **{w['rule_id']}**: {w['message']}")

        lines.extend(["", "---", "", "## 四、通過規則清單", ""])
        for p in self.passed:
            lines.append(f"- ✅ {p}")

        lines.extend(["", "---", "", "*報告由 skill_validate.py 自動生成*"])

        report = '\n'.join(lines)

        if output_path:
            output_path = Path(output_path)
            output_path.write_text(report, encoding="utf-8")
            print(f"報告已儲存: {output_path}")

        return report

# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Agent Swarm 技能合規檢查器")
    parser.add_argument("--skill-dir", type=str, help="技能目錄路徑")
    parser.add_argument("--file", type=str, help="單一檔案路徑")
    parser.add_argument("--strict", action="store_true", help="嚴格模式（將 LOW 視為違規）")
    parser.add_argument("--report-path", type=str, default=None, help="報告輸出路徑")
    args = parser.parse_args()

    if not args.skill_dir and not args.file:
        parser.print_help()
        sys.exit(1)

    validator = SkillValidator(strict=args.strict)

    if args.skill_dir:
        skill_dir = Path(args.skill_dir)
        validator.validate_directory(skill_dir)
    elif args.file:
        filepath = Path(args.file)
        validator.validate_file(filepath)

    report = validator.generate_report(output_path=args.report_path)
    print(report)

    # 返回碼：有違規則非零
    sys.exit(1 if validator.violations else 0)

if __name__ == "__main__":
    main()
