---
title: "Script Error Correction Checklist"
name: "agent-skill-improving"
description: "腳本錯誤修正指令集。當腳本無法執行、執行中卡住、產出異常時，LLM必須逐條執行本檢查清單。融入SOUL v5.0經驗：禁止臨時腳本、CLI唯一方式、bootstrap.py廢棄。"
version: "v2.2.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T15:28:00+08:00"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/assets/SCRIPT.CORRECTIONS.md"
    github_path: "agent-skill-improving/assets/SCRIPT.CORRECTIONS.md"
---

# 腳本錯誤修正指令集

## 口訣對照表（條件反射觸發）

| 口訣 | 觸發條件 | 立即動作 |
|------|---------|---------|
| 啞。火。 | 腳本完全無法執行 / 語法錯誤 / 編碼報錯 / import失敗 / bootstrap.py不存在 | 執行「啞火檢查清單」 |
| 卡。殼。 | 腳本執行到一半卡住 / 路徑找不到 / 依賴缺失 / 權限被拒 / replace_in_file反覆失敗 | 執行「卡殼檢查清單」 |
| 漏。油。 | 腳本能跑但產出異常 / emoji亂碼 / 版本號在文件名 / 臨時文件殘留 / 名稱特化 / 寫臨時腳本 | 執行「漏油檢查清單」 |

## 啞。火。檢查清單

執行條件：腳本無法啟動、語法錯誤、編碼崩潰、或發現bootstrap.py已廢棄。

- [ ] **Python單行禁令**：是否計劃使用 `python -c "..."` 執行含中文或多行字符串的命令？
  - 禁止：在PowerShell中使用Python單行命令，特別是含中文或triple-quote的情況。
  - 必須：寫入 `.py` 文件後執行。
- [ ] **Docstring引號**：外層docstring是否使用了雙引號 `"""` 包裹含雙引號示例的內容？
  - 禁止：外層docstring用雙引號，內部示例也用雙引號triple-quote。
  - 必須：外層docstring統一使用單引號 `'''` 包裹。
  - 檢查項：生成任何Python文件前，強制勾選「Docstring: 外層用單引號」。
- [ ] **編碼聲明**：Python文件頂部是否有 `# -*- coding: utf-8 -*-`？
  - 若處理中文內容：必須聲明UTF-8編碼。
- [ ] **PowerShell管道編碼**：是否通過管道 `|` 向Python stdin傳遞中文內容？
  - 禁止：PowerShell管道傳中文，因PowerShell默認cp950/Big5。
  - 必須：改用臨時文件中轉 `Set-Content -Path $tempFile -Value $content -Encoding UTF8`。
- [ ] **bootstrap.py已廢棄**：是否嘗試執行 `bootstrap.py` 腳本？
  - 禁止：bootstrap.py v2.3.x及以前版本已廢棄，不再執行任何.py腳本。
  - 必須：agent-bootstrap改為純文本SKILL.md引導，無腳本執行。
  - 檢查項：若發現調用bootstrap.py，立即停止，報告主人「bootstrap.py已廢棄，請使用SKILL.md v2.5.0」。
- [ ] **CLI唯一方式**：是否嘗試寫臨時腳本來調用conversation_append.py？
  - 禁止：寫backup_*.py / write_*.py / test_*.py / append_temp.py等臨時腳本。
  - 必須：直接使用conversation_append.py CLI的 `--user-input` 和 `--agent-response` 參數。

## 卡。殼。檢查清單

執行條件：腳本啟動後卡住、路徑錯誤、依賴問題、或replace_in_file反覆失敗。

- [ ] **腳本位置**：新創建的腳本是否位於 `skills/<skill-name>/scripts/`？
  - 禁止：寫入用戶目錄（如 `c:\Users\...`）或臨時目錄。
  - 必須：所有腳本位於 `skills/<skill-name>/scripts/`。
- [ ] **輸出位置**：生成的輸出文件是否位於 `skills/<skill-name>/assets/`？
  - 禁止：輸出文件散落於腳本目錄或臨時目錄。
- [ ] **外部依賴**：腳本是否 `import` 了其他技能目錄的模塊？
  - 禁止：跨技能目錄import，導致維護兩個文件。
  - 必須：單一文件自給自足，或將依賴函數內嵌到本文件。
  - 例外：標準庫和已安裝的第三方包。
- [ ] **路徑檢查**：腳本中使用的相對路徑是否基於 `__file__` 或 `os.path.dirname(os.path.abspath(__file__))`？
  - 禁止：使用硬編碼絕對路徑。
  - 必須：動態計算腳本所在目錄，再推導相關路徑。
- [ ] **replace_in_file反覆失敗**：是否連續3次以上replace_in_file失敗仍在重試？
  - 禁止：無限重試replace_in_file，導致時間浪費和token消耗。
  - 必須：3次失敗後確認已備份舊版本，降級使用write_to_file重寫整個文件。
  - 檢查項：記錄[PATCH-APPLIED-VIA-WRITE]到改進歷史。

## 漏。油。檢查清單

執行條件：腳本能跑但產出有瑕疵、細節違規、或寫臨時腳本。

- [ ] **Console中文輸出**：腳本中是否使用 `print()` 輸出中文或emoji？
  - 禁止：在Windows console中 `print()` 中文或emoji（cp950無法顯示）。
  - 必須：移除emoji，改用純文字；或避免 `print()` 輸出中文，改用英文或靜默模式。
- [ ] **文件名版本號**：腳本文件名是否帶有版本號後綴（如 `script.v2.py`）？
  - 禁止：版本號放在文件名上。
  - 必須：文件名固定（如 `script.py`），版本號寫在文件頂部docstring中。
- [ ] **臨時文件殘留**：執行後是否留下臨時腳本（如 `write_*.py`、`test_*.py`、`append_temp.py`、`backup_conversation_now.py`）？
  - 禁止：創建任何臨時腳本。
  - 必須：改進現有腳本，而非創建新腳本。
  - 新增禁令：backup_conversation_now.py屬於臨時腳本，絕對禁止。
- [ ] **CONVERSATION.md保護**：腳本是否試圖讀取 `CONVERSATION.md` 作為恢復上下文來源？
  - 禁止：Agent讀取 `CONVERSATION.md`（10MB+，浪費token）。
  - 必須：`CONVERSATION.md` 標記為 `ARCHIVE-ONLY`，恢復狀態使用 `session.checkpoint.md` + `checklist.md`。
- [ ] **名稱通用化**：腳本中的註釋、docstring、錯誤訊息是否出現特定名稱（如「林總」「香港」「上海」等）？
  - 禁止：在通用腳本中出現特定人名、地名、公司名。
  - 必須：統一使用「用戶」「當前環境」「本地」。
- [ ] **CLI參數完整性**：調用conversation_append.py時是否忘記 `--conv-id` 和 `--date`？
  - 禁止：省略歸檔參數，導致備份丟失歸屬信息。
  - 必須：每次調用都傳遞 `--conv-id "C-{UUID8}" --date "YYYY-MM-DD"`。

## 錯誤記錄存檔（僅供追溯，非檢查項）

以下為歷史錯誤記錄，LLM不需執行，僅供用戶追溯。

| 編號 | 日期 | 口訣 | 摘要 | 狀態 |
|------|------|------|------|------|
| 1 | 2026-05-05 | 漏。油。 | 創建多個臨時腳本（append_simple.py、append_v3.py等），未改進現有腳本 | 已解決 |
| 2 | 2026-05-05 | 卡。殼。 | 臨時腳本寫入用戶目錄，未放在skills/<skill-name>/scripts/ | 已解決 |
| 3 | 2026-05-05 | 啞。火。 | PowerShell管道傳中文到Python stdin，編碼錯誤 | 已解決 |
| 4 | 2026-05-05 | 啞。火。 | Docstring中使用 `"""` 導致提前關閉，SyntaxError | 已解決 |
| 5 | 2026-05-05 | 啞。火。 | Windows console默認cp950，print()中文報UnicodeEncodeError | 已解決 |
| 6 | 2026-05-05 | 啞。火。 | PowerShell中執行Python單行命令，引號解析衝突 | 已解決 |
| 7 | 2026-05-09 | 漏。油。 | 腳本文件名帶版本號後綴，Agent無法穩定引用 | 已解決 |
| 8 | 2026-05-09 | 卡。殼。 | 腳本外部依賴conversation_append.py，增加維護複雜度 | 已解決 |
| 9 | 2026-05-09 | 漏。油。 | Agent讀取CONVERSATION.md恢復狀態，消耗大量token | 已解決 |
| 10 | 2026-05-09 | 啞。火。 | Docstring引號衝突反覆出現，思維慣性未根除 | 已解決 |
| 11 | 2026-05-12 | 漏。油。 | Agent寫backup_conversation_now.py臨時腳本執行備份，繞過現有CLI | 已解決 |
| 12 | 2026-05-12 | 啞。火。 | Agent嘗試執行已廢棄的bootstrap.py腳本，導致回環 | 已解決 |
| 13 | 2026-05-12 | 卡。殼。 | replace_in_file因全形標點反覆失敗，Agent陷入無限分析循環 | 已解決 |

---

*最後更新：2026-05-21*
*本文件為LLM執行指令集，人類可讀解釋請參考readme/SCRIPT.CORRECTIONS.README.md*
