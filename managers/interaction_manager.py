from game_states import (
    DIALOGUE,
    SPACE,
    PASSWORD,
    SUCCESS,
    GAME_OVER
)


# ============================================================
# 核心互動邏輯
#
# 這一區的函式：
# 1. 不使用 print()
# 2. 不使用 input()
# 3. 不依賴 pygame
# 4. 只負責遊戲規則與 GameManager 狀態
#
# 未來 Pygame UI 與文字 UI 都會共用這些函式。
# ============================================================


# ======== 一般物品核心邏輯 ======== #

def collect_item(game, item_id, objects):
    """取得指定道具並回傳互動結果。"""

    current_object = objects[item_id]  # 取得目前指定物品完整資料

    if game.add_item(item_id):  # 將物品加入背包並同步圖鑑紀錄
        return {
            "status": "item_found",
            "object_id": item_id,
            "item_id": item_id,
            "name": current_object["name"],
            "description": current_object["description"]
        }

    return {
        "status": "already_owned",
        "object_id": item_id,
        "item_id": item_id,
        "name": current_object["name"]
    }


# ======== Inspectable 核心邏輯 ======== #

def inspect_object(game, object_id, objects):
    """調查指定物件並回傳其顯示內容。"""

    current_object = objects[object_id]  # 讀取目前可調查物件完整資料

    first_inspection = not game.is_object_inspected(
        object_id
    )  # 判斷是否為第一次調查物件

    if first_inspection:
        game.inspect_object(
            object_id
        )  # 第一次調查時寫入已檢查紀錄

    object_name = current_object["name"]
    description = current_object.get(
        "description",
        f"這就是一個普通{object_name}。"
    )

    return {
        "status": "inspected",
        "object_id": object_id,
        "name": object_name,
        "description": description,
        "first_inspection": first_inspection
    }


# ======== Searchable 核心邏輯 ======== #

def search_object(game, object_id, objects):
    """搜尋指定物件並回傳搜尋結果。"""

    searchable_object = objects[object_id]  # 取得搜尋型物件完整資料
    item_id = searchable_object.get("item")  # 取得搜尋後可能發現的物品

    if item_id is None:
        return {
            "status": "nothing_found",
            "object_id": object_id,
            "name": searchable_object["name"],
            "description": "裡面沒有任何東西。"
        }

    # 這裡檢查 discovered_items，而不是 inventory。
    # 未來即使物品被使用掉，也不能再次從原地取得。
    if game.has_discovered_item(item_id):
        return {
            "status": "empty",
            "object_id": object_id,
            "item_id": item_id,
            "name": searchable_object["name"],
            "description": searchable_object["empty_text"]
        }

    item_result = collect_item(
        game,
        item_id,
        objects
    )  # 實際取得搜尋位置中的指定道具

    return {
        "status": "item_found",
        "object_id": object_id,
        "item_id": item_id,
        "name": item_result["name"],
        "description": item_result["description"]
    }


# ======== Container 核心邏輯 ======== #

def get_container_info(game, object_id, objects):
    """取得容器本身與內部物件資料。"""

    container_object = objects[object_id]  # 讀取指定容器完整物件資料

    contents = container_object.get(
        "contents",
        []
    )  # 取得容器目前包含的子物件清單

    content_data = []

    for child_id in contents:
        child_object = objects[child_id]
        hide_item_id = child_object.get("hide_after_discovered")
        if hide_item_id is not None and game.has_discovered_item(hide_item_id):
            continue

        content_data.append(
            {
                "object_id": child_id,
                "name": child_object["name"],
                "type": child_object["type"]
            }
        )  # 整理成UI能直接使用的物件資料

    return {
        "status": "container",
        "object_id": object_id,
        "name": container_object["name"],
        "description": container_object["description"],
        "contents": content_data
    }


# ======== Rift 核心邏輯：取得裂隙資訊 ======== #

def get_rift_info(game, object_id, objects, levels):
    """取得裂隙目的地資訊，但尚未真正切換空間。"""

    current_object = objects[object_id]  # 讀取目前指定裂隙完整資料

    target_space = current_object.get(
        "target_space"
    )  # 取得目前裂隙所連接的空間ID

    if target_space not in levels:
        return {
            "status": "invalid_target",
            "object_id": object_id,
            "name": current_object["name"],
            "description": current_object["description"],
            "target_space": target_space
        }

    return {
        "status": "rift_available",
        "object_id": object_id,
        "name": current_object["name"],
        "description": current_object["description"],
        "target_space": target_space,
        "target_name": levels[target_space]["name"]
    }


# ======== Rift 核心邏輯：正式進入裂隙 ======== #

def enter_rift(game, object_id, objects, levels):
    """玩家確認後才真正切換所在空間。"""

    rift_result = get_rift_info(
        game,
        object_id,
        objects,
        levels
    )  # 再次確認目前裂隙目標是否合法

    if rift_result["status"] != "rift_available":
        return rift_result

    target_space = rift_result["target_space"]

    game.enter_space(
        target_space
    )  # 玩家確認後才正式更新目前空間

    return {
        "status": "space_changed",
        "object_id": object_id,
        "target_space": target_space,
        "target_name": rift_result["target_name"]
    }


# ============================================================
# Photo 核心邏輯
# ============================================================


# ======== 取得照片檢視資訊 ======== #

def get_photo_view(game, photo_id, objects, mode="inventory"):
    """取得照片檢視資料，不直接觸發任何劇情。"""

    photo = objects[photo_id]  # 取得目前指定照片完整資料

    return {
        "status": "photo_view",
        "photo_id": photo_id,
        "mode": mode,
        "name": photo["name"],
        "front_text": photo["description"],
        "back_text": photo.get("back_text", "")
    }


# ======== 查看照片正面 ======== #

def view_photo_front(game, photo_id, objects, mode="inventory"):
    """查看照片正面，不改變任何劇情事件。"""

    photo = objects[photo_id]  # 取得照片正面描述文字

    return {
        "status": "photo_front",
        "photo_id": photo_id,
        "mode": mode,
        "name": photo["name"],
        "description": photo["description"]
    }


# ======== 查看照片背面 ======== #

def view_photo_back(game, photo_id, objects, mode="inventory"):
    """查看照片背面，Story模式下觸發關鍵劇情。"""

    photo = objects[photo_id]  # 取得照片背面相關劇情資料

    # 如果只是從背包或圖鑑重新查看，
    # 不再次觸發 photo_back_seen。
    if mode != "story":
        return {
            "status": "photo_back",
            "photo_id": photo_id,
            "mode": mode,
            "back_text": photo.get("back_text", ""),
            "story_triggered": False
        }

    first_time = not game.has_event(
        "photo_back_seen"
    )  # 判斷是否第一次完成照片背面劇情

    if first_time:
        game.complete_event(
            "photo_back_seen"
        )  # 第一次查看背面後正式寫入劇情事件

    game.game_state = DIALOGUE  # 照片背面之後切換到劇情對話狀態

    return {
        "status": "photo_story_triggered",
        "photo_id": photo_id,
        "mode": mode,
        "back_text": photo.get("back_text", ""),
        "story_triggered": first_time,

        # 這些內容之後可再移入 dialogue.json。
        # 現階段保留在結果中，方便文字版與Pygame共用。
        "dialogue": [
            {
                "speaker": "黎琛",
                "text": "空間D……還有？"
            },
            {
                "speaker": "",
                "text": "牆上顯示器突然亮起。"
            },
            {
                "speaker": "黎琛",
                "text": "收斂率在漲……這個房間在消失。我得走。"
            }
        ],

        "system_message": {
            "title": "收斂率更新",
            "values": {
                "A": 81,
                "B": 55,
                "C": 37
            }
        }
    }


# ======== 完成照片後續 Dialogue ======== #

def finish_photo_story_dialogue(game):
    """照片劇情對話播放完後回到目前探索空間。"""

    if game.current_space is not None:
        game.game_state = SPACE  # 照片後續對話結束後回探索狀態

    return {
        "status": "photo_story_finished",
        "current_space": game.current_space
    }


# ============================================================
# Door / Ending 核心邏輯
# ============================================================


# ======== 取得門目前狀態 ======== #

def get_door_info(game, object_id, objects):
    """取得出口門目前是否可以進入。"""

    door = objects[object_id]  # 取得目前指定出口門完整資料

    required_event = door.get(
        "required_event"
    )

    if (
        required_event is not None
        and not game.has_event(required_event)
    ):
        return {
            "status": "door_locked",
            "object_id": object_id,
            "name": door["name"],
            "description": door["locked_description"],
            "required_event": required_event
        }

    return {
        "status": "door_available",
        "object_id": object_id,
        "name": door["name"],
        "description": door["description"],
        "target_scene": door.get("target_scene")
    }


# ======== 正式進入出口門 ======== #

def enter_door(game, object_id, objects):
    """確認出口門狀態並回傳門後的場景。"""

    door_result = get_door_info(
        game,
        object_id,
        objects
    )  # 玩家確認進入前再次檢查出口門狀態

    if door_result["status"] != "door_available":
        return door_result

    target_scene = door_result.get(
        "target_scene"
    )

    if target_scene == "chapter_1_end":
        game.current_scene = "chapter_1_end"
        game.complete_chapter(1)  # 玩家正式進入結尾後完成第一章
        game.game_state = SUCCESS  # 第一章結束時切換到成功狀態

        return {
            "status": "chapter_end",
            "object_id": object_id,
            "chapter": 1,
            "target_scene": target_scene,

            "dialogue": [
                {
                    "speaker": "",
                    "text": "你伸手握住門把。這一次，門沒有鎖。"
                },
                {
                    "speaker": "",
                    "text": "門板中央有一道細長的信封口。那讓你想起剛才得到的那張照片。"
                },
                {
                    "speaker": "",
                    "text": "你推開門。"
                },
                {
                    "speaker": "",
                    "text": "外面不是醫院走廊——是一條無限延伸的白色通道。"
                },
                {
                    "speaker": "",
                    "text": "兩側有無數扇門，每一扇都標著不同的座標編號。"
                }
            ],

            "ending_text": "你只解開了一把鎖。但你還沒解開自己。"
        }

    return {
        "status": "scene_transition" if target_scene else "door_entered",
        "object_id": object_id,
        "target_scene": target_scene
    }


# ============================================================
# 以下暫時保留文字版 UI Wrapper
#
# main.py 目前仍是文字介面，所以先繼續使用。
# 未來 Pygame 版本會直接呼叫上面的核心函式。
# ============================================================


# ======== Container 文字版 Wrapper ======== #

def interact_with_container(game, object_id, objects):
    """文字版容器介面。"""

    result = get_container_info(
        game,
        object_id,
        objects
    )  # 取得不依賴UI的容器內容資料

    print()
    print(result["name"])
    print(result["description"])

    contents = result["contents"]

    while True:
        print()

        for index, child in enumerate(contents, start=1):
            print(f"{index}. {child['name']}")

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

        selected_child_id = contents[
            choice - 1
        ]["object_id"]

        interact_with_nested_object(
            game,
            selected_child_id,
            objects
        )


# ======== 巢狀子物件文字版 Wrapper ======== #

def interact_with_nested_object(game, object_id, objects):
    """文字版容器子物件分派介面。"""

    current_object = objects[object_id]
    object_type = current_object["type"]

    print()
    print(current_object["name"])

    if object_type == "searchable":
        interact_with_searchable(
            game,
            object_id,
            objects
        )

    elif object_type == "inspectable":
        interact_with_inspectable(
            game,
            object_id,
            objects
        )

    elif object_type == "item":
        interact_with_item(
            game,
            object_id,
            objects
        )

    else:
        print("This nested object cannot be interacted with.")


# ======== Searchable 文字版 Wrapper ======== #

def interact_with_searchable(game, object_id, objects):
    """文字版搜尋介面。"""

    searchable_object = objects[object_id]

    item_id = searchable_object.get(
        "item"
    )

    # 如果以前已經取得過物品，就直接顯示空白結果。
    if (
        item_id is not None
        and game.has_discovered_item(item_id)
    ):
        result = search_object(
            game,
            object_id,
            objects
        )

        print(result["description"])
        return

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

        result = search_object(
            game,
            object_id,
            objects
        )  # 玩家確認後才執行真正搜尋邏輯

        if result["status"] == "item_found":
            print()
            print(result["description"])
            print()
            print("獲得：", result["name"])

        else:
            print(result["description"])

        return


# ======== Inspectable 文字版 Wrapper ======== #

def interact_with_inspectable(game, object_id, objects):
    """文字版一般物件調查介面。"""

    result = inspect_object(
        game,
        object_id,
        objects
    )  # 呼叫不依賴任何UI的調查核心

    print(result["description"])


# ======== Rift 文字版 Wrapper ======== #

def interact_with_rift(game, object_id, objects, levels):
    """文字版裂隙介面。"""

    result = get_rift_info(
        game,
        object_id,
        objects,
        levels
    )  # 取得裂隙描述與目的空間資料

    print(result["description"])

    if result["status"] == "invalid_target":
        print("Target space does not exist.")
        return

    while True:
        print()
        print(f"是否進入{result['target_name']}？")
        print("1. 是")
        print("2. 否")

        choice = input("Choose: ")

        if choice == "2":
            return

        if choice != "1":
            print("Invalid choice.")
            continue

        travel_result = enter_rift(
            game,
            object_id,
            objects,
            levels
        )  # 玩家確認後才真正執行空間切換

        if travel_result["status"] == "space_changed":
            print(
                "Moved to:",
                travel_result["target_name"]
            )

        return


# ============================================================
# Password 文字版 Wrapper
# ============================================================

def interact_with_puzzle(game, object_id, objects, puzzle_manager):
    """文字版謎題介面，共用正式謎題規則與完成設定。"""

    from controllers.puzzle_controller import PuzzleController

    controller = PuzzleController(puzzle_manager)
    current_object = objects[object_id]
    result = controller.open_puzzle(current_object.get("puzzle_id"))

    if result["status"] != "input_required":
        print(result.get("message", ""))
        controller.close_puzzle()
        return

    print(current_object.get("description", ""))

    while True:
        remaining = controller.remaining_attempts
        if remaining is not None:
            print("Attempts left:", remaining)

        answer = input("Answer (輸入0返回): ")
        if answer == "0":
            controller.close_puzzle()
            return

        # 原始輸入直接交由核心驗證避免截斷答案
        result = puzzle_manager.submit_answer(controller.current_puzzle_id, answer)
        print(result.get("message", ""))
        status = result["status"]

        if status in ("invalid_input", "incomplete_input", "wrong"):
            continue

        controller.close_puzzle()
        if status == "correct":
            for reward in result.get("rewards", []):
                if reward["type"] == "item" and reward["result"]["status"] == "item_found":
                    print("獲得：", reward["result"]["name"])

            completion = result.get("on_complete") or {}
            if completion.get("type") == "open_photo":
                item_id = completion.get("item_id")
                if item_id in objects:
                    interact_with_photo(
                        game, item_id, objects,
                        mode=completion.get("mode", "inventory")
                    )  # 完成後的顯示流程完全依照謎題設定
        return


# ============================================================
# Photo 文字版 Wrapper
# ============================================================

def interact_with_photo(
    game,
    photo_id,
    objects,
    mode="inventory"
):
    """文字版照片正面與背面檢視介面。"""

    photo_view = get_photo_view(
        game,
        photo_id,
        objects,
        mode
    )

    while True:
        print()
        print("======== 照片 ========")
        print("1. 照片正面")
        print("2. 照片背面")

        # Story Mode 必須查看背面才能離開。
        if mode != "story":
            print("0. 返回")

        choice = input("Choose: ")

        if choice == "0" and mode != "story":
            return

        if choice == "1":
            result = view_photo_front(
                game,
                photo_id,
                objects,
                mode
            )

            print()
            print("特寫：照片")
            print(result["description"])

        elif choice == "2":
            result = view_photo_back(
                game,
                photo_id,
                objects,
                mode
            )

            print()
            print("照片背面：")
            print(
                f"「{result['back_text']}」"
            )

            # 背包或圖鑑重新查看照片時，不重新觸發劇情。
            if result["status"] == "photo_back":
                continue

            if result["status"] == "photo_story_triggered":
                print()

                dialogue = result["dialogue"]

                print("黎琛")
                print()
                print(dialogue[0]["text"])
                print()

                print(dialogue[1]["text"])
                print()

                system_message = result[
                    "system_message"
                ]

                print(system_message["title"] + "：")

                for space_name, rate in system_message[
                    "values"
                ].items():
                    print(
                        f"空間{space_name}: {rate}%"
                    )

                print()

                print("黎琛")
                print()
                print(dialogue[2]["text"])

                finish_photo_story_dialogue(
                    game
                )  # 文字版播放完劇情後恢復探索狀態

                return

        else:
            print("Invalid choice.")


# 為了暫時相容先前程式可能使用的函式名稱，
# 保留 inspect_photo 作為舊名稱的轉接入口。
def inspect_photo(game, photo_id, objects):
    """舊照片函式名稱的相容入口。"""

    interact_with_photo(
        game,
        photo_id,
        objects,
        mode="story"
    )


# ============================================================
# Door 文字版 Wrapper
# ============================================================

def interact_with_door(game, object_id, objects):
    """文字版出口門互動介面。"""

    result = get_door_info(
        game,
        object_id,
        objects
    )  # 取得目前出口門是否已經解鎖

    print(result["description"])

    if result["status"] == "door_locked":
        return

    while True:
        print()
        print("是否進入？")
        print("1. 進入")
        print("2. 取消")

        choice = input("Choose: ")

        if choice == "2":
            return

        if choice != "1":
            print("Invalid choice.")
            continue

        ending_result = enter_door(
            game,
            object_id,
            objects
        )  # 玩家確認後正式開始章節結尾

        if ending_result["status"] == "chapter_end":
            print()

            for line in ending_result["dialogue"]:
                print(line["text"])
                print()

            print("畫面逐漸淡出。")
            print()
            print(
                f"「{ending_result['ending_text']}」"
            )

        return


# ============================================================
# Item 文字版 Wrapper
# ============================================================

def interact_with_item(game, object_id, objects):
    """文字版一般物品取得介面。"""

    result = collect_item(
        game,
        object_id,
        objects
    )  # 呼叫不依賴任何UI的物品取得核心

    if result["status"] == "item_found":
        print(result["description"])
        print("獲得：", result["name"])

    else:
        print("你已經擁有這個物品。")


# ============================================================
# 統一文字版物件分派入口
# ============================================================

def interact_with_object(
    game,
    object_id,
    objects,
    levels,
    puzzle_manager
):
    """文字版入口，依照物件種類分派互動。"""

    current_object = objects[object_id]
    object_type = current_object["type"]

    print()
    print(current_object["name"])

    if object_type == "container":
        interact_with_container(
            game,
            object_id,
            objects
        )

    elif object_type == "inspectable":
        interact_with_inspectable(
            game,
            object_id,
            objects
        )

    elif object_type == "rift":
        interact_with_rift(
            game,
            object_id,
            objects,
            levels
        )

    elif object_type == "puzzle":
        interact_with_puzzle(
            game,
            object_id,
            objects,
            puzzle_manager
        )

    elif object_type == "door":
        interact_with_door(
            game,
            object_id,
            objects
        )

    elif object_type == "item":
        interact_with_item(
            game,
            object_id,
            objects
        )

    else:
        print("Unknown object type.")
