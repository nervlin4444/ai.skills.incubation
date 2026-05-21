---
title: "Script Corrections Reference Guide"
name: "agent-skill-improving"
description: "SCRIPT.CORRECTIONS.md v2.2.0 的人類可讀解釋書。記載口訣含義與觸發時機，融入SOUL v5.0新經驗：bootstrap.py廢棄、CLI唯一方式、禁止臨時腳本。供主人參考。"
version: "v1.2.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T15:28:00+08:00"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/readme/SCRIPT.CORRECTIONS.README.md"
    github_path: "agent-skill-improving/readme/SCRIPT.CORRECTIONS.README.md"
---

# SCRIPT.CORRECTIONS 解釋書

## 文件定位

| 檔案 | 讀者 | 用途 |
|------|------|------|
| SCRIPT.CORRECTIONS.md v2.2.0 | LLM | 執行指令集，條件反射觸發 |
| SCRIPT.CORRECTIONS.README.md（本檔） | 主人 | 口訣含義解釋、觸發時機參考、新經驗說明 |

LLM不讀取本檔案。本檔案僅供主人理解口訣設計與錯誤分類邏輯。

## 口訣設計原理

口訣採用「兩個字+句號」結構，目的是讓LLM經過百幾次查看後能條件反射理解，無需逐字閱讀上下文。

| 口訣 | 字面含義 | 對應錯誤類型 | 為何這樣設計 |
|------|---------|------------|------------|
| 啞。火。 | 槍啞火，打不出子彈 | 腳本完全無法執行、語法錯誤、編碼崩潰、bootstrap.py已廢棄 | 扣下扳機沒反應，連第一步都走不出去 |
| 卡。殼。 | 槍卡殼，子彈上膛失敗 | 腳本啟動後卡住、路徑錯誤、依賴缺失、replace_in_file反覆失敗 | 能扣扳機但子彈卡在中間，進退兩難 |
| 漏。油。 | 機器漏油，還能動但損耗大 | 腳本能跑但產出異常、emoji亂碼、版本號在文件名、臨時文件殘留、寫臨時腳本 | 機器還在運轉，但每轉一圈都在浪費資源 |

## 三類錯誤的區分標準

### 啞火（P0 致命）

當腳本根本無法啟動，或發現已廢棄的bootstrap.py時觸發。

典型場景：
- PowerShell中執行python -c "含中文代碼"，引號解析衝突導致SyntaxError
- Docstring外層用 `"""`，內部示例也用 `"""`，Python提前關閉docstring
- Windows console默認cp950，腳本print("已完成")報UnicodeEncodeError
- 通過管道傳中文到Python stdin，PowerShell用Big5編碼導致亂碼
- **Agent嘗試執行已廢棄的bootstrap.py腳本，導致回環（v2.2.0 新增）**
- **Agent用python -c執行多行備份命令，引號地獄（v2.2.0 新增）**

為何致命：腳本連啟動都做不到，後續所有邏輯都是空談。

### 卡殼（P1 嚴重）

當腳本能啟動，但執行到一半卡住時觸發。

典型場景：
- 臨時腳本寫入c:\Users\...，下次執行時路徑不存在或權限不足
- 腳本A import腳本B，腳本B被修改後腳本A行為異常
- 使用硬編碼絕對路徑，換一台機器路徑不同導致FileNotFoundError
- 輸出文件寫入腳本目錄而非assets/，造成目錄混亂
- **replace_in_file因全形標點反覆失敗，Agent陷入無限分析循環（v2.2.0 新增）**

為何嚴重：能啟動但走不完，數據可能寫到一半，產生髒數據。

### 漏油（P2 拖慢）

當腳本能完整執行，但產出有瑕疵時觸發。

典型場景：
- 腳本輸出含emoji，在Windows console顯示為亂碼方塊
- 文件名帶版本號後綴script.v2.py，Agent每次引用都要改路徑
- 執行後留下write_final.py、test_v2_5_0.py等臨時文件
- Agent讀取CONVERSATION.md（10MB+）恢復狀態，浪費token
- 腳本註釋中出現「林總」「香港」等特定名稱，導致LLM綁定特定環境
- **Agent寫backup_conversation_now.py臨時腳本執行備份，繞過現有CLI（v2.2.0 新增）**
- **Agent忘記--conv-id和--date，導致備份丟失歸屬信息（v2.2.0 新增）**

為何不致命：不會導致任務失敗，但會累積技術債，長期拖慢效率。

## 新經驗說明（v2.2.0 新增）

### 1. bootstrap.py 已廢棄

**問題**：Agent反覆嘗試執行bootstrap.py腳本，輸出被平台發送→Connector捕獲→回環。

**解決**：bootstrap.py v2.3.x及以前版本全部廢棄。agent-bootstrap改為純文本SKILL.md引導，無腳本執行。對話開始時只注入SOUL.md + IDENTITY.md。

### 2. CLI 唯一方式

**問題**：Agent覺得conversation_append.py的--content參數複雜，於是寫backup_conversation_now.py臨時腳本來「簡化」。

**解決**：conversation_append.py v1.3.0新增--user-input和--agent-response參數，一行命令即可完成備份。禁止寫任何臨時腳本，禁止用python -c執行多行命令。

### 3. replace_in_file 降級機制

**問題**：Agent因全形標點差異導致replace_in_file反覆失敗，陷入「分析為什麼失敗」的無限循環，花了幾十分鐘。

**解決**：3次失敗後直接降級write_to_file，禁止無限分析。但必須先備份舊版本。

## 錯誤記錄存檔說明

SCRIPT.CORRECTIONS.md底部的「錯誤記錄存檔」表格僅供主人追溯歷史，LLM在執行檢查清單時不會讀取這些記錄。這是刻意的設計——避免歷史噪音干擾LLM的當前判斷。

若主人需要LLM參考歷史錯誤，應改為讀取MEMORY.md或CONVERSATION.md。

## 與SKILL.CORRECTIONS.md的區別

| 維度 | SKILL.CORRECTIONS | SCRIPT.CORRECTIONS |
|------|-------------------|--------------------|
| 口訣 | 斷鏈 / 偏軌 / 絆腳 | 啞火 / 卡殼 / 漏油 |
| 內容 | 技能載入、工作流、版本號、記憶管理 | 編碼、亂碼、emoji、路徑、權限 |
| 觸發時機 | use_skill失敗 / 階段偏離 | 生成腳本前 / 腳本執行失敗 |
| 讀者 | LLM（執行）+ 主人（本檔參考） | LLM（執行）+ 主人（本檔參考） |

簡單記憶法：
- SKILL.CORRECTIONS管「流程」——技能怎麼載、階段怎麼走、版本怎麼升
- SCRIPT.CORRECTIONS管「代碼」——腳本怎麼寫、路徑怎麼放、編碼怎麼設

## 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|---------|
| v1.0.0 | 2026-05-09 | 初始版本，從SCRIPT.CORRECTIONS.md分家 |
| v1.1.0 | 2026-05-10 | 補充口訣設計原理與三類錯誤區分標準，名稱通用化修正 |
| **v1.2.0** | **2026-05-13** | **融入SOUL v5.0經驗：bootstrap.py廢棄、CLI唯一方式、replace_in_file降級機制** |

---

*最後更新：2026-05-21*
*本檔案為人類可讀解釋書，LLM執行指令請參考assets/SCRIPT.CORRECTIONS.md*
