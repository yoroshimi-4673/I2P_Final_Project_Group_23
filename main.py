import json
from pathlib import Path  # 匯入Path建立穩定可靠的專案檔案路徑

from game_manager import GameManager
from game_states import GAME_OVER


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


# ======== 以下處理巢狀容器互動 ======== #

def interact_with_container(game, object_id, objects):  # 顯示容器內部可進一步探索的物件
    container_object = objects[object_id]

    print("\n", container_object["name"])
    print(container_object["description"])

    contents = container_object.get("contents", [])

    while True:
        print()

        for index, child_id in enumerate(contents, start=1):
            print(f"{index}. {objects[child_id]['name']}")

        print("0. 返回")

        try:
            choice = int(input("Choose: "))

        except ValueError:
            print("Please enter a number.")
            continue

        if choice == 0:
            return

        if choice < 1 or choice > len(contents):
            print("Invalid choice.")
            continue

        selected_child_id = contents[choice - 1]

        interact_with_nested_object(
            game,
            selected_child_id,
            objects
        )


# ======== 以下處理巢狀子物件 ======== #

def interact_with_nested_object(game, object_id, objects):  # 處理容器內部搜尋與其他子物件互動
    current_object = objects[object_id]
    object_type = current_object["type"]

    print("\n", current_object["name"])
    print(current_object["description"])

    if object_type == "searchable":
        interact_with_searchable(
            game,
            object_id,
            objects
        )

    elif object_type == "inspectable":
        print(current_object["description"])

    else:
        print("This nested object cannot be interacted with.")


# ======== 以下處理搜尋型物件 ======== #

def interact_with_searchable(game, object_id, objects):  # 詢問玩家是否要進一步搜尋目前指定區域
    searchable_object = objects[object_id]

    while True:
        print()
        print(searchable_object["search_prompt"])
        print("1. 是")
        print("2. 否")

        choice = input("Choose: ")

        if choice == "2":
            return

        if choice != "1":
            print("Invalid choice.")
            continue

        item_id = searchable_object.get("item")

        if item_id is None:
            print("裡面沒有任何東西。")
            return

        if game.has_item(item_id):
            print(searchable_object["empty_text"])
            return

        item = objects[item_id]

        game.add_item(item_id)  # 將搜尋發現的指定物品加入玩家目前背包

        print()
        print(item["description"])
        print()
        print("獲得：", item["name"])

        return


# ======== 以下處理密碼成功後的照片 ======== #

def inspect_photo(game, photo_id, objects):  # 密碼解開後進入照片正面與背面的特殊劇情模式
    photo = objects[photo_id]

    while True:
        print("\n======== 照片 ========")
        print("1. 照片正面")
        print("2. 照片背面")

        choice = input("Choose: ")

        if choice == "1":
            print()
            print("特寫：照片")
            print(photo["description"])

        elif choice == "2":
            print()
            print("照片背面：")
            print(f"「{photo['back_text']}」")
            print()

            print("黎琛（翻看背面）")
            print()
            print("空間D……還有？")
            print()

            print("牆上顯示器突然亮起：")
            print("收斂率更新：")
            print("空間A: 81%")
            print("空間B: 55%")
            print("空間C: 37%")
            print()

            print("黎琛")
            print()
            print("收斂率在漲……這個房間在消失。我得走。")

            game.complete_event("photo_back_seen")  # 照片背面查看完成後記錄關鍵劇情事件

            return

        else:
            print("Invalid choice.")


# ======== 以下處理物件互動 ======== #

def interact_with_object(game, object_id, objects, levels):  # 統一處理主場景不同類型物件的互動行為
    current_object = objects[object_id]
    object_type = current_object["type"]

    print("\n", current_object["name"])


    # ======== Container ======== #

    if object_type == "container":  # 容器會進入自己的下一層探索介面
        interact_with_container(
            game,
            object_id,
            objects
        )


    # ======== Inspectable ======== #

    elif object_type == "inspectable":  # 一般可調查物件直接顯示目前描述文字
        print(current_object["description"])

        if not game.is_object_inspected(object_id):
            game.inspect_object(object_id)  # 保留首次調查紀錄供未來章節使用


    # ======== Rift ======== #

    elif object_type == "rift":  # 裂隙物件會將玩家傳送到指定空間
        print(current_object["description"])

        target_space = current_object["target_space"]

        if target_space not in levels:
            print("Target space does not exist.")
            return

        game.enter_space(target_space)

        print("Moved to:", levels[target_space]["name"])


    # ======== Puzzle ======== #

    elif object_type == "puzzle":  # 處理密碼以及其他需要答案的謎題物件

        if game.is_puzzle_solved(object_id):
            print("面板已經滑開，暗格裡現在是空的。")
            return

        print(current_object["description"])

        password = input("Password: ")

        correct_password = current_object["correct_password"]
        max_attempts = current_object.get("max_attempts", 3)

        if game.check_password(
            object_id,
            password,
            correct_password,
            max_attempts
        ):
            print()
            print("正確輸入。")
            print()
            print("面板滑開。")
            print("暗格裡一個透明小盒——裡面放著一張照片。")

            game.solve_puzzle(object_id)  # 將目前密碼謎題正式記錄成已經完成

            reward_item = current_object.get("reward_item")

            if reward_item is not None:
                game.add_item(reward_item)  # 密碼成功後將照片直接加入玩家背包

                inspect_photo(
                    game,
                    reward_item,
                    objects
                )

        else:
            remaining_attempts = game.get_puzzle_attempts(
                object_id,
                max_attempts
            )

            print("Wrong password.")
            print("Attempts left:", remaining_attempts)

            if game.game_state == GAME_OVER:
                print()
                print("空間C已封鎖。")
                print("你將永遠被困在這個空間。")


    # ======== Door ======== #

    elif object_type == "door":  # 出口門依照指定劇情事件判斷目前是否能開啟
        required_event = current_object.get("required_event")

        if (
            required_event is not None
            and not game.has_event(required_event)
        ):
            print(current_object["locked_description"])
            return

        print(current_object["description"])

        target_scene = current_object.get("target_scene")

        if target_scene == "chapter_1_end":
            game.current_scene = "chapter_1_end"
            game.complete_chapter(1)  # 玩家推開出口門時正式完成第一章內容

            print()
            print("【互動】走向門口 → 門未鎖 → 推開")
            print()
            print("外面不是醫院走廊——")
            print("是一條無限延伸的白色通道。")
            print("兩側有無數扇門，每一扇都標著不同的座標編號。")
            print()
            print("畫面逐漸淡出。")
            print()
            print("「你只解開了一把鎖。但你還沒解開自己。」")


    # ======== Item ======== #

    elif object_type == "item":  # 一般道具若直接互動則嘗試加入玩家背包
        if game.add_item(object_id):
            print(current_object["description"])
            print("獲得：", current_object["name"])

        else:
            print("你已經擁有這個物品。")


    # ======== Unknown ======== #

    else:
        print("Unknown object type.")


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