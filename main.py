import json
from pathlib import Path  # 匯入Path建立穩定可靠的專案檔案路徑

from game_manager import GameManager
from game_states import CHOICE, SUCCESS, GAME_OVER
from save_manager import save_game, load_game

#========以下讀取遊戲資料========#

BASE_DIR = Path(__file__).resolve().parent  # 取得目前main.py所在的專案根目錄位置

LEVELS_PATH = BASE_DIR / "data" / "levels.json"  # 建立關卡資料檔案的完整路徑
CHARACTERS_PATH = BASE_DIR / "data" / "characters.json"  # 建立角色資料檔案的完整路徑
OBJECTS_PATH = BASE_DIR / "data" / "objects.json"  # 建立物件資料檔案的完整路徑


with open(LEVELS_PATH, "r", encoding="utf-8") as file:
    levels = json.load(file)

with open(CHARACTERS_PATH, "r", encoding="utf-8") as file:  # 開啟並讀取角色JSON資料檔案
    characters = json.load(file)  # 將角色JSON轉換成Python字典資料

with open(OBJECTS_PATH, "r", encoding="utf-8") as file:  # 開啟並讀取物件JSON資料檔案
    objects = json.load(file)  # 將物件JSON轉換成Python字典資料

# ======== 以下處理物件互動 ======== #

def interact_with_object(game, object_id, objects, levels):  # 統一處理不同類型物件的互動行為
    current_object = objects[object_id]  # 依照物件ID取得完整的物件資料
    object_type = current_object["type"]  # 取得物件類型以決定後續互動方式

    print("\n", current_object["name"])

    if object_type == "item":  # 玩家互動物品時嘗試加入背包
        if game.add_item(object_id):
            print(current_object["description"])
            print("Item obtained:", current_object["name"])

            if "back_text" in current_object:  # 若物件具有背面文字則一併顯示
                print(current_object["back_text"])

            save_game(game)

        else:
            print("You already have this item.")

    elif object_type == "inspectable":  # 檢查環境物件時只顯示相關描述內容
        print(current_object["description"])

    elif object_type == "rift":  # 裂隙物件會將玩家傳送到指定空間
        print(current_object["description"])

        target_space = current_object["target_space"]

        if target_space not in levels:  # 避免裂隙指向不存在的關卡資料
            print("Target space does not exist.")
            return

        game.enter_space(target_space)

        print("Moved to:", levels[target_space]["name"])
        save_game(game)

    elif object_type == "puzzle":  # 解謎物件會進入密碼輸入與判定流程
        print(current_object["description"])

        password = input("Password: ")

        if game.check_password(password):
            print("Correct password!")

            current_level = levels[game.current_space]  # 取得目前解謎所在空間的關卡資料

            for unlocked_id in current_level.get("unlock_objects", []):  # 逐一解鎖此謎題完成後出現的物件
                game.unlock_object(unlocked_id)

            save_game(game)

        else:
            print("Wrong password.")
            print("Attempts left:", game.password_attempts)
            save_game(game)

    else:
        print("Unknown object type.")

#以下建立並載入遊戲環境

game = GameManager()

loaded = load_game(game)

if loaded:
    print("Save loaded.")

else:
    print("No valid save found.")
    game.game_state = CHOICE

if game.current_space is None:  # 新遊戲尚未設定位置時先從空間A開始
    game.enter_space("A")

print("Game started")

#========以下開始遊戲========#

while game.game_state not in [SUCCESS, GAME_OVER]:

    current_level = levels[game.current_space]  # 根據目前位置取得對應關卡資料

    print("\nEntered:", current_level["name"])

    level_objects = current_level.get("objects", []).copy()  # 取得目前關卡一開始就存在的物件清單

    for object_id in current_level.get("unlock_objects", []):  # 檢查目前關卡中的特殊解鎖物件
        if game.is_object_unlocked(object_id):
            level_objects.append(object_id)

    print("\nObjects:")

    for index, object_id in enumerate(level_objects, start=1):  # 將關卡物件依序加上玩家可選擇的編號
        print(index, objects[object_id]["name"])

    #========以下只是文字版UI介面的防呆機制，Pygame版本可刪除========#
    
    try:  # 嘗試將玩家輸入轉換成整數編號
        object_choice = int(input("Choose an object: "))
    except ValueError:  # 輸入不是整數時避免程式直接中斷
        print("Please enter a number.")
        continue

    if object_choice < 1 or object_choice > len(level_objects):  # 確認玩家輸入落在有效物件範圍
        print("Invalid object choice.")
        continue

    #=============================================================#

    selected_object_id = level_objects[object_choice - 1]  # 將玩家輸入編號轉換成對應物件ID

    interact_with_object(
        game,
        selected_object_id,
        objects,
        levels
    )  # 根據物件類型執行對應的互動功能


# ======== 遊戲結束 ======== #

print("Game state:", game.game_state)
print("Play time:", game.get_play_time())  # 顯示目前累積的遊玩秒數供測試使用