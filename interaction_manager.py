from game_states import GAME_OVER  # 匯入遊戲失敗狀態供密碼機制判斷使用


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


# ======== 以下處理一般可調查物件 ======== #

def interact_with_inspectable(game, object_id, objects):  # 處理一般場景中可直接調查的物件
    current_object = objects[object_id]

    print(current_object["description"])

    if not game.is_object_inspected(object_id):
        game.inspect_object(object_id)  # 第一次調查時保留物件已檢查紀錄


# ======== 以下處理裂隙 ======== #

def interact_with_rift(game, object_id, objects, levels):  # 處理裂隙與不同空間之間的移動
    current_object = objects[object_id]

    print(current_object["description"])

    target_space = current_object["target_space"]

    if target_space not in levels:
        print("Target space does not exist.")
        return

    game.enter_space(target_space)  # 將玩家目前所在位置切換至裂隙目標空間

    print("Moved to:", levels[target_space]["name"])


# ======== 以下處理謎題 ======== #

def interact_with_puzzle(game, object_id, objects):  # 處理密碼輸入與謎題成功失敗流程
    current_object = objects[object_id]

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

        return

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


# ======== 以下處理門 ======== #

def interact_with_door(game, object_id, objects):  # 依照劇情事件判斷目前出口門是否可以使用
    current_object = objects[object_id]

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


# ======== 以下處理一般物品 ======== #

def interact_with_item(game, object_id, objects):  # 處理玩家直接取得場景中一般物品的情況
    current_object = objects[object_id]

    if game.add_item(object_id):
        print(current_object["description"])
        print("獲得：", current_object["name"])

    else:
        print("你已經擁有這個物品。")


# ======== 以下統一分派物件互動 ======== #

def interact_with_object(game, object_id, objects, levels):  # 根據物件類型交由對應互動函式進行處理
    current_object = objects[object_id]
    object_type = current_object["type"]

    print("\n", current_object["name"])

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
            objects
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