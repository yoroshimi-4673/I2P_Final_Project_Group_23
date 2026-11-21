import unittest

from managers.game_manager import GameManager
from managers.interaction_manager import inspect_object


class InspectionTests(unittest.TestCase):
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
