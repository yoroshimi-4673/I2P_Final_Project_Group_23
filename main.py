import json
from pathlib import Path  # 匯入Path建立穩定可靠的專案檔案路徑

from game_manager import GameManager
from game_states import GAME_OVER
from interaction_manager import interact_with_object  # 匯入統一的場景物件互動處理函式


# ======== 以下讀取遊戲資料 ======== #

BASE_DIR = Path(__file__).resolve().parent  # 取得目前main.py所在的專案根目錄位置

LEVELS_PATH = BASE_DIR / "data" / "levels.json"  # 建立關卡資料檔案的完整路徑
CHARACTERS_PATH = BASE_DIR / "data" / "characters.json"  # 建立角色資料檔案的完整路徑
OBJECTS_PATH = BASE_DIR / "data" / "objects.json"  # 建立物件資料檔案的完整路徑
DIALOGUE_PATH = BASE_DIR / "data" / "dialogue.json"  # 建立劇情對話資料檔案的完整路徑


with open(LEVELS_PATH, "r", encoding="utf-8") as file:
    levels = json.load(file)

with open(CHARACTERS_PATH, "r", encoding="utf-8") as file:
    characters = json.load(file)

with open(OBJECTS_PATH, "r", encoding="utf-8") as file:
    objects = json.load(file)

with open(DIALOGUE_PATH, "r", encoding="utf-8") as file:
    dialogues = json.load(file)


# ======== 以下處理簡化版序章 ======== #

def play_intro(game, dialogues):  # 依照dialogue.json播放Prototype簡化序章內容
    game.current_scene = "intro"

    intro_dialogues = dialogues.get("intro", [])

    print("\n======== 序章：最後一次呼吸 ========\n")

    for dialogue in intro_dialogues:
        speaker = dialogue.get("speaker", "")
        text = dialogue.get("text", "")

        if speaker:
            print(f"{speaker}：{text}")
        else:
            print(text)

        input("\n[Enter 繼續] ")

    play_first_choice(game, dialogues)


def play_first_choice(game, dialogues):  # 顯示Scene04，進行首次事件三選一，並決定起始空間
    game.current_scene = "scene_04_choice"

    choice_data = dialogues["scene_04_choice"]

    print("\n======== Scene 04｜307房 ========\n")
    print(choice_data["prompt"])
    print()

    options = choice_data["options"]

    for option_id, option in options.items():
        print(f"{option_id}. {option['text']}")

    while True:
        choice = input("\nChoose A, B, or C: ").upper()

        if choice not in options:
            print("Invalid choice.")
            continue

        selected_option = options[choice]

        print()
        print(selected_option["result_text"])

        target_space = selected_option["target_space"]

        game.current_scene = "exploration"  # 第一次選擇完成後正式進入探索階段
        game.enter_space(target_space)  # 根據玩家第一次選擇決定起始探索空間

        break


# ======== 以下建立全新遊戲環境 ======== #

game = GameManager()

game.reset_game()  # Prototype目前沒有存檔功能，每次執行都建立全新遊戲

play_intro(
    game,
    dialogues
)  # 遊戲啟動後固定先播放簡化序章與第一次選擇


# ======== 以下開始遊戲 ======== #

while game.game_state != GAME_OVER and game.chapter < 1:

    current_level = levels[game.current_space]  # 根據目前所在位置取得對應關卡資料

    print("\n========", current_level["name"], "========")

    if "convergence_rate" in current_level:
        print(
            "收斂率:",
            str(current_level["convergence_rate"]) + "%"
        )

    if "warning" in current_level:
        print("警告:", current_level["warning"])


    # ======== 建立目前主場景物件清單 ======== #

    level_objects = current_level.get("objects", []).copy()  # 主場景只顯示levels.json指定的平級物件


    # ======== 顯示目前可互動物件 ======== #

    print("\nObjects:")

    for index, object_id in enumerate(level_objects, start=1):
        print(index, objects[object_id]["name"])


    # ======== 以下只是文字版UI介面的防呆機制，Pygame版本可刪除 ======== #

    if not level_objects:
        print("There is nothing to interact with here.")
        break

    try:
        object_choice = int(input("Choose an object: "))

    except ValueError:
        print("Please enter a number.")
        continue

    if object_choice < 1 or object_choice > len(level_objects):
        print("Invalid object choice.")
        continue

    # ================================================================= #


    selected_object_id = level_objects[object_choice - 1]  # 將玩家輸入的編號轉換成真正物件ID

    interact_with_object(
        game,
        selected_object_id,
        objects,
        levels
    )  # 根據玩家選取物件執行對應互動流程


# ======== 遊戲結束 ======== #

if game.game_state == GAME_OVER:

    print("\n======== GAME OVER ========")

    if game.game_over_reason == "space_c_locked":
        print("空間C已永久封鎖。")

elif game.chapter >= 1:
    print("\n======== 第一章結束 ========")


print(
    "累積遊玩時間:",
    game.get_formatted_play_time()
)  # 顯示本次Prototype從開始到結束的累積遊玩時間

print("Inventory:", game.inventory)
print("Solved puzzles:", game.solved_puzzles)
print("Story events:", game.story_events)
print("Unlocked objects:", game.unlocked_objects)
print("Inspected objects:", game.inspected_objects)