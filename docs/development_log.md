# Development Log

本文件用來記錄 Group 23 專案的開發進度、問題、修正方式與下一步工作。

---

## 專案資訊

- 專案名稱：數到100
- 類型：2D劇情向解謎遊戲
- 開發工具：Python / pygame-ce
- 專案入口：`game_home.py`
- GitHub Repository：`I2P_Final_Project_Group_23`
- First Pitch: 2026/11/24
- Final Presentstion：2026/12/27

---

## 開發日誌格式

每次更新程式時，建議依照以下格式新增一筆。

### YYYY-MM-DD — 負責人

#### 今日完成
- 
#### 修改檔案
- 
#### 遇到的問題
- 
#### 解決方式
- 
#### 尚未解決
- 
#### 下一步
- 

---

# 開發紀錄

## 2026/10/31 — 張語恩

### 完成項目
- 將 UI 相關檔案整理到 `ui/` 資料夾。
- 新增 `ui/__init__.py`。
- 更新 `game_home.py` 的 UI import 路徑。
- 修正 `interaction_ui.py` 與 `codex_ui.py` 的 import。
- 將舊版 `game_extra.py` 封存至 `archive/`。
- 將 `game_extra.py` 改為 `game_extra.txt`，避免 Pylance 繼續分析。
- 修正 Hotbar 回傳資料格式問題。
- 修正密碼剩餘次數相關函式名稱。

### 修改檔案
- `game_home.py`
- `interaction_manager.py`
- `main.py`
- `ui/game_ui.py`
- `ui/dialogue_ui.py`
- `ui/interaction_ui.py`
- `ui/codex_ui.py`
- `ui/__init__.py`
- `archive/game_extra.txt`

### 遇到的問題
- Hotbar 點擊物品時曾出現：
  - `TypeError: tuple indices must be integers or slices, not str`
  - `KeyError: 'slots'`
- `game_extra.py` 內出現大量未定義變數與函式。
- 組員執行遊戲時出現：
  - `ModuleNotFoundError: No module named 'ui'`

### 解決方式
- 將 `draw_hotbar()` 的回傳值改為包含固定 key 的 dictionary：
  - `slots`
  - `visible_items`
  - `left`
  - `right`
- 將舊版 `game_extra.py` 移出正式程式架構。
- 確認 UI 檔案已移入 `ui/` package。
- 確認正式遊戲入口為 `game_home.py`。
- 組員需確認已 pull 最新版本，且從專案根目錄執行遊戲。

### 尚未解決
- 玩家角色移動系統尚未完成。
- 場景 collision 尚未完成。
- 物件互動距離判斷尚未完成。
- `map_manager.py` 功能仍待開發。
- Save / Load 尚未完整整合。

### 下一步
- 建立玩家 movement。
- 建立 collision。
- 建立互動距離判斷。
- 將目前的滑鼠互動逐步改為玩家靠近物件後按鍵互動。
- 開始整合正式場景與素材。

---

## 簡易Timeline

### 2026-11-06
目標：
- 玩家可移動(wasd, 滑鼠點擊)。
- 基本碰撞判定。
- 可靠近物件並互動。
- 劇情、關卡設計(二、三章)、結局、美術

    <!-- ### 2026-11-20
    目標：
    - 完成第一個可以從 New Game 玩到 Ending 的完整 MVP。

    ### 2026-12-04
    目標：
    - Content Complete。
    - 主要劇情、謎題、場景與素材全部整合。

    ### 2026-12-18
    目標：
    - Feature Freeze。
    - 不再加入大型新功能，只處理 Bug 與 polish。

    ### 2026-12-23
    目標：
    - Final Release Candidate。
    - 完成跨電腦測試與展示準備。

    ### 2026-12-27
    目標：
    - Final Version。
    - 完成展示、簡報與備援版本。 -->