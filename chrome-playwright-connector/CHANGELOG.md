---
title: "Chrome Playwright Connector - CHANGELOG"
name: "chrome-playwright-connector"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T18:15:00+08:00"
fixes: []
---

# Chrome Playwright Connector - CHANGELOG

## v1.0.0 (2026-05-21)

### Added
- F-001: browser_connector.py - 瀏覽器連接器核心（啟動、導航、操作、關閉）
- F-002: profile_manager.py - Profile 管理（創建、驗證、清理、多網站隔離）
- F-003: diagnostic_kit.py - 診斷工具包（HTML dump、截圖、元素列舉、日誌）
- 完整 SKILL.md 執行指令檔案
- README.md 人類可讀說明書
- .env.example 環境變數模板

### Notes
- 初始版本，所有接口定義視為 LOCK PERMANENT
- 不依賴特定網站，供上游技能調用
- Profile 命名規範：網址 `https://www.kimi.com/` → `kimi_com`
