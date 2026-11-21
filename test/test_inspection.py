import json
from pathlib import Path
import unittest

from managers.game_manager import GameManager
from managers.interaction_manager import inspect_object


class InspectionTests(unittest.TestCase):
    def test_chapter_two_furniture_is_registered_for_inspection(self):
        data = Path(__file__).resolve().parents[1] / "data"
        objects = json.loads((data / "objects.json").read_text(encoding="utf-8"))
        spaces = json.loads((data / "ui_layout.json").read_text(encoding="utf-8"))["spaces"]
        for space, object_id, name in (
            ("T0", "t0_wardrobe", "衣櫃"),
            ("T7", "t7_safe", "保險箱"),
            ("T7", "t7_bedside_table", "床頭櫃"),
            ("T7", "t7_wardrobe", "衣櫃"),
            ("T3", "t3_safe", "保險箱"),
            ("T3", "t3_bedside_table", "床頭櫃"),
        ):
            with self.subTest(object_id=object_id):
                self.assertEqual(objects[object_id], {
                    "name": name, "type": "inspectable", "space": space,
                })
                room = spaces[space]
                self.assertNotIn(object_id, room.get("decorations", {}))
                self.assertEqual(room["objects"][object_id]["label"], name)
                self.assertEqual(room["objects"][object_id]["interaction_padding"], 40)
                self.assertEqual(
                    inspect_object(GameManager(), object_id, objects)["description"],
                    f"這就是一個普通{name}。"
                )

    def test_fallback_uses_furniture_name(self):
        for object_id, name, expected in (
            ("normal_wardrobe", "衣櫃", "這就是一個普通衣櫃。"),
            ("normal_bedside_table", "床頭櫃", "這就是一個普通床頭櫃。"),
        ):
            with self.subTest(object_id=object_id):
                game = GameManager()
                objects = {object_id: {"name": name, "type": "inspectable"}}
                result = inspect_object(game, object_id, objects)
                self.assertEqual(result["name"], name)
                self.assertEqual(result["description"], expected)
                self.assertTrue(result["first_inspection"])
                self.assertTrue(game.is_object_inspected(object_id))
                self.assertFalse(inspect_object(game, object_id, objects)["first_inspection"])

    def test_existing_description_takes_precedence(self):
        objects = {
            "story_wardrobe": {
                "name": "衣櫃",
                "type": "inspectable",
                "description": "衣櫃裡沒有找到要找的東西。",
            }
        }
        result = inspect_object(GameManager(), "story_wardrobe", objects)
        self.assertEqual(result["description"], "衣櫃裡沒有找到要找的東西。")
