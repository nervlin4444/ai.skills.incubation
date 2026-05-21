---
title: "Skill Improvement Scripts Usage Guide"
name: "agent-skill-improving"
description: "agent-skill-improving 腳本用法總覽：skill_improving.py + skill_validate.py"
version: "v1.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T15:28:00+08:00"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/scripts/USAGE.md"
    github_path: "agent-skill-improving/scripts/USAGE.md"
---

# scripts/USAGE.md — 技能改進與合規驗證腳本用法總覽

> 版本：v1.1.0（對齊 agent-skill-improving v1.2.4）
> 位置：`scripts/USAGE.md`

---

## 版本對齊表

| 文件 | 版本 | 用途 |
|------|------|------|
| skill_improving.py | v1.0.0 | 趨勢分析、patch 生成、回滾保護 |
| skill_validate.py | v1.0.0 | 技能合規檢查器（23 項問題 + 8 項架構紅線） |
| SKILL.md | v1.2.4 | Skill Improver 執行指令集（含驗證步驟） |
| README.md | v1.2.4 | 人類可讀解釋書 |
| USAGE.md | v1.1.0 | 本文件：雙腳本用法說明 |

---

# 第一部分：skill_improving.py

## 1. 讀取使用歷史

    from skill_improving import load_correction_history

    result = load_correction_history(
        correction_path=Path("assets/SKILL.CORRECTION.md"),
        skill_name="currency-exchange-tracker",
        limit=10
    )

    print(result)
    # {
    #     "records": [...],
    #     "total": 10,
    #     "success_count": 7,
    #     "failure_count": 3,
    #     "warning": None
    # }

## 2. 趨勢分析

    from skill_improving import analyze_trends

    result = analyze_trends(result["records"])

    print(result)
    # {
    #     "success_rate_trend": "下降",
    #     "error_distribution": {"計劃問題": 1, "評估問題": 0, "執行問題": 1, "技能自身問題": 1},
    #     "version_stability": "穩定",
    #     "coverage": "覆蓋",
    #     "flags": ["[DEGRADED]", "[SKILL-DEFECT]"],
    #     "warning": None
    # }

## 3. 生成 Patch

    from skill_improving import generate_patch

    result = generate_patch(
        skill_name="currency-exchange-tracker",
        current_version="v1.0.0",
        patch_type="Minor",
        trigger="連續 3 次 API 超時，成功率下降至 70%",
        changes=["增加超時重試機制（最多 3 次）", "增加備用數據源切換"],
        impact="僅影響 fetch_exchange_rate.py，不影響其他模組",
        rollback="刪除重試邏輯，恢復單次請求"
    )

    print(result)
    # {
    #     "success": True,
    #     "patch_content": "...",
    #     "new_version": "v1.1.0",
    #     "file_path": "improve/currency-exchange-tracker/PATCH_v1.0.0_to_v1.1.0.md",
    #     "timestamp": "2026-05-11T15:00:00",
    #     "warning": None
    # }

## 4. 應用 Patch（含備份）

    from skill_improving import apply_patch

    result = apply_patch(
        skill_path=Path("skills/currency-exchange-tracker/SKILL.md"),
        patch_file=Path("improve/currency-exchange-tracker/PATCH_v1.0.0_to_v1.1.0.md"),
        backup_dir=Path("improve/backups")
    )

    print(result)
    # {
    #     "success": True,
    #     "backup_path": "improve/backups/SKILL_20260511_150000.md",
    #     "applied": True,
    #     "timestamp": "2026-05-11T15:00:00",
    #     "warning": None
    # }

## 5. 回滾技能

    from skill_improving import rollback_skill

    result = rollback_skill(
        skill_path=Path("skills/currency-exchange-tracker/SKILL.md"),
        backup_path=Path("improve/backups/SKILL_20260511_150000.md")
    )

    print(result)
    # {
    #     "success": True,
    #     "rolled_back": True,
    #     "timestamp": "2026-05-11T15:05:00",
    #     "warning": None
    # }

## 6. 內容完整性預檢

    from skill_improving import check_content_integrity

    result = check_content_integrity(
        content="這是準備寫入的完整內容...",
        expected_length=500
    )

---

# 第二部分：skill_validate.py

## 7. 驗證改進後的技能合規性（新增）

在應用 Patch 後、交付前，必須調用 skill_validate.py 驗證改進後的技能是否符合 23 項已知問題與 8 項架構紅線。

### 7.1 驗證單一檔案

    import subprocess

    result = subprocess.run(
        ["python", "skill_validate.py", "--file", "./skills/currency-exchange-tracker/LLM/SKILL.md", "--strict"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("[VALIDATION-FAILED] 改進後的技能存在合規違規，禁止交付")
        print(result.stdout)
        # 觸發回滾
    else:
        print("[VALIDATION-PASSED] 合規檢查通過")

### 7.2 驗證整個技能目錄

    result = subprocess.run(
        ["python", "skill_validate.py",
         "--skill-dir", "./skills/currency-exchange-tracker/",
         "--strict",
         "--report-path", "./improve/currency-exchange-tracker/VALIDATION_REPORT.md"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("[VALIDATION-FAILED] 合規檢查失敗，查看 VALIDATION_REPORT.md")
        # 觸發回滾

### 7.3 在 Python 中直接調用

    from skill_validate import SkillValidator

    validator = SkillValidator(strict=True)
    validator.validate_directory(Path("./skills/currency-exchange-tracker/"))
    report = validator.generate_report(output_path=Path("./VALIDATION_REPORT.md"))

    if validator.violations:
        print(f"[VALIDATION-FAILED] 發現 {len(validator.violations)} 項違規")
        for v in validator.violations:
            print(f"  - {v['rule_id']}: {v['title']}")
    else:
        print("[VALIDATION-PASSED] 全部通過")

---

# 第三部分：標準整合模板（Agent 直接複用）

## 模板 A：純 skill_improving 流程（改進現有技能）

    from pathlib import Path
    from skill_improving import (
        load_correction_history,
        analyze_trends,
        generate_patch,
        apply_patch
    )

    # 步驟 1：讀取歷史
    history = load_correction_history(
        correction_path=Path("assets/SKILL.CORRECTION.md"),
        skill_name="currency-exchange-tracker",
        limit=10
    )

    if history["total"] < 5:
        print("[NO-DATA] 累積不足 5 次，建議延後分析")
        exit()

    # 步驟 2：趨勢分析
    trends = analyze_trends(history["records"])

    # 步驟 3：識別改進點
    for flag in trends["flags"]:
        if flag == "[DEGRADED]":
            patch_type = "Major"
        elif flag == "[SKILL-DEFECT]":
            patch_type = "Major"
        elif flag in ["[UNSTABLE]", "[INSUFFICIENT-COVERAGE]"]:
            patch_type = "Minor"
        else:
            patch_type = "Hotfix"

    # 步驟 4：生成 Patch
    patch = generate_patch(
        skill_name="currency-exchange-tracker",
        current_version="v1.0.0",
        patch_type=patch_type,
        trigger=f"趨勢分析標記: {', '.join(trends['flags'])}",
        changes=["根據趨勢分析結果調整"],
        impact="待評估",
        rollback="恢復上一版本"
    )

    # 步驟 5：審核分級
    if patch_type == "Major":
        print("[PENDING-APPROVAL] 等待主人確認")
    else:
        apply_patch(
            skill_path=Path("skills/currency-exchange-tracker/SKILL.md"),
            patch_file=Path(patch["file_path"])
        )
        print(f"[PATCH-APPLIED] 已更新至 {patch['new_version']}")

## 模板 B：改進 + 合規驗證完整流程（推薦）

    from pathlib import Path
    import subprocess
    from skill_improving import (
        load_correction_history,
        analyze_trends,
        generate_patch,
        apply_patch,
        rollback_skill
    )

    skill_name = "currency-exchange-tracker"
    skill_path = Path(f"skills/{skill_name}/SKILL.md")
    skill_dir = Path(f"skills/{skill_name}/")

    # ========== 改進階段 ==========
    history = load_correction_history(
        correction_path=Path("assets/SKILL.CORRECTION.md"),
        skill_name=skill_name,
        limit=10
    )

    trends = analyze_trends(history["records"])
    patch = generate_patch(
        skill_name=skill_name,
        current_version="v1.0.0",
        patch_type="Minor",
        trigger="趨勢分析結果",
        changes=["調整內容"],
        impact="影響範圍",
        rollback="恢復上一版本"
    )

    # 應用 Patch
    apply_result = apply_patch(
        skill_path=skill_path,
        patch_file=Path(patch["file_path"]),
        backup_dir=Path("improve/backups")
    )

    # ========== 合規驗證階段（新增） ==========
    print("[STEP-8.5] 執行合規驗證...")
    val_result = subprocess.run(
        ["python", "skill_validate.py", "--skill-dir", str(skill_dir), "--strict"],
        capture_output=True,
        text=True
    )

    if val_result.returncode != 0:
        print("[VALIDATION-FAILED] 改進後技能存在合規違規")
        print(val_result.stdout)
        # 立即回滾
        rollback_skill(skill_path, Path(apply_result["backup_path"]))
        print("[ROLLBACK-EXECUTED] 已回滾到改進前版本")
        print("[REPORT] 上報主人：改進方案導致合規違規，需重新評估")
        exit(1)
    else:
        print("[VALIDATION-PASSED] 合規檢查通過，允許交付")
        print(f"[PATCH-APPLIED] 技能已更新並通過驗證")

---

# 第四部分：輸出文件規範

| 文件類型 | 命名格式 | 存放位置 | 說明 |
|---------|---------|---------|------|
| Patch 方案 | `PATCH_{舊版本}_to_{新版本}.md` | `improve/{技能名}/` | 改進方案 |
| 備份檔案 | `{技能名}_{時間戳}.md` | `improve/backups/` | 舊版本備份 |
| 改進記錄 | `SKILL_CORRECTION.md` | `assets/` | 累積追加 |
| 合規報告 | `VALIDATION_REPORT_{時間戳}.md` | `improve/{技能名}/` | skill_validate 輸出 |

---

# 第五部分：常見問題

**Q：何時觸發 Skill Improving？**
A：累積 5-10 次使用記錄後，或主人主動要求分析時。

**Q：Patch 應用失敗怎麼辦？**
A：立即回滾到備份版本，輸出 [ROLLBACK-EXECUTED]，上報主人。

**Q：Major 級 patch 主人長時間不回覆？**
A：標記 [PENDING-APPROVAL]，繼續監控舊版本使用情況，不擅自應用。

**Q：skill_validate 何時調用？**
A：應用 Patch 後、交付前必須調用。若驗證失敗，立即回滾並上報，禁止交付不合規技能。

**Q：驗證失敗但改進內容正確怎麼辦？**
A：違規項可能涉及架構紅線（如檔案命名、frontmatter 格式）。先修復違規項，重新驗證通過後方可交付。禁止繞過驗證。

---

*最後更新：2026-05-21（v1.1.0 對齊 v1.2.4，更新 frontmatter 規範）*
