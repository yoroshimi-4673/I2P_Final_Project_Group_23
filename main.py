import json
from pathlib import Path  # 匯入Path建立穩定可靠的專案檔案路徑

from game_manager import GameManager
from game_states import CHOICE, SUCCESS, GAME_OVER
from save_manager import save_game, load_game


BASE_DIR = Path(__file__).resolve().parent  # 取得目前main.py所在的專案根目錄位置
LEVELS_PATH = BASE_DIR / "data" / "levels.json"  # 建立不受執行位置影響的關卡資料路徑

with open(LEVELS_PATH, "r", encoding="utf-8") as file:  # 使用完整路徑開啟關卡JSON資料檔案
    levels = json.load(file)


game = GameManager()

loaded = load_game(game)

if loaded:
    print("Save loaded.")
else:
    print("No valid save found.")
    game.game_state = CHOICE


print("Game started")


while game.game_state not in [SUCCESS, GAME_OVER]:

    choice = input("Choose A, B, or C: ").upper()

    if choice not in levels:
        print("Invalid choice.")
        continue

    game.enter_space(choice)
    save_game(game)

    current_level = levels[choice]

    print(current_level["name"])
    print(current_level["description"])

    if "item" in current_level:
        item_name = current_level["item"]

        if game.add_item(item_name):
            print(current_level["clue"])
            save_game(game)

        else:
            print("There is nothing new here.")

    if current_level.get("password_required", False):
        password = input("Password: ")

        if game.check_password(password):
            print("Correct password!")
            save_game(game)

        else:
            print("Wrong password.")
            print("Attempts left:", game.password_attempts)
            save_game(game)


print("Game state:", game.game_state)