import copy
import io
import unittest
from contextlib import redirect_stdout

import keywords
from take import take
from world.items import items as item_registry


def make_room(item_names):
    return {
        keywords.General.DESCRIPTION: "test room",
        keywords.General.ITEMS: {name: item_registry[name] for name in item_names},
        keywords.Direction.NORTH: "elsewhere",
    }


class TakeTests(unittest.TestCase):

    TABLE_CASES = [
        # (name, initial_room_items, initial_inventory, command, expected_ok)
        ("take_present_item",            ["map"],         [],
         ["take", "map"],                 True),
        ("take_first_of_two",            ["map", "ball"], [],
         ["take", "map"],                 True),
        ("take_second_of_two",           ["map", "ball"], [],
         ["take", "ball"],                True),
        ("take_with_synonym",            ["globe"],       [],
         ["grab", "globe"],               True),
        ("take_with_pick_up_synonym",    ["compass"],     [],
         ["pick-up", "compass"],          True),
        ("take_missing_arg",             ["map"],         [],
         ["take"],                        False),
        ("take_empty_command",           ["map"],         [],
         [],                              False),
        ("take_nonexistent_item",        ["map"],         [],
         ["take", "sword"],               False),
        ("take_item_already_inventory",  ["map"],         ["compass"],
         ["take", "compass"],             False),
        ("take_from_empty_room",         [],              [],
         ["take", "map"],                 False),
        ("take_extra_args_uses_second",  ["map", "ball"], [],
         ["take", "ball", "now"],         True),
        ("take_unknown_item_two_items",  ["map", "ball"], [],
         ["take", "knife"],               False),
        ("take_present_with_full_pack",  ["map"],         ["compass", "knife", "ruler"],
         ["take", "map"],                 True),
        ("take_empty_string_item_name",  ["map"],         [],
         ["take", ""],                    False),
        ("take_none_command",            ["map"],         [],
         None,                            False),
        ("take_tuple_command",           ["map"],         [],
         ("take", "map"),                 True),
    ]

    def test_table_driven_cases_with_snapshots(self):
        self.assertGreaterEqual(len(self.TABLE_CASES), 12)
        for (name, room_items, pack_items, command, expected_ok) in self.TABLE_CASES:
            with self.subTest(case=name):
                room = make_room(room_items)
                inventory = {n: item_registry[n] for n in pack_items}
                room_before = copy.deepcopy(room)
                inventory_before = copy.deepcopy(inventory)

                buf = io.StringIO()
                with redirect_stdout(buf):
                    result = take(room, command, inventory)

                self.assertEqual(result, expected_ok, name)

                if expected_ok:
                    item_name = command[1]
                    expected_room = copy.deepcopy(room_before)
                    expected_pack = copy.deepcopy(inventory_before)
                    expected_pack[item_name] = copy.deepcopy(
                        expected_room[keywords.General.ITEMS].pop(item_name)
                    )
                    self.assertEqual(copy.deepcopy(room), expected_room, name)
                    self.assertEqual(copy.deepcopy(inventory), expected_pack, name)
                    self.assertNotIn(item_name, room[keywords.General.ITEMS], name)
                    self.assertIn(item_name, inventory, name)
                    self.assertIn("you take the", buf.getvalue(), name)
                else:
                    self.assertEqual(copy.deepcopy(room), room_before, name)
                    self.assertEqual(copy.deepcopy(inventory), inventory_before, name)
                    self.assertNotIn("Traceback", buf.getvalue(), name)

    def test_repeat_take_same_item_is_consistent(self):
        room = make_room(["map"])
        inventory = {}
        before_room = copy.deepcopy(room)
        before_pack = copy.deepcopy(inventory)
        with redirect_stdout(io.StringIO()):
            first = take(room, ["take", "map"], inventory)
            second = take(room, ["take", "map"], inventory)
            third = take(room, ["take", "map"], inventory)
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertFalse(third)
        self.assertEqual(set(inventory.keys()), {"map"})
        self.assertEqual(room[keywords.General.ITEMS], {})
        self.assertNotEqual(copy.deepcopy(room), before_room)
        self.assertNotEqual(copy.deepcopy(inventory), before_pack)

    def test_failure_does_not_poison_next_success(self):
        room = make_room(["map", "ball"])
        inventory = {"compass": item_registry["compass"]}
        with redirect_stdout(io.StringIO()):
            self.assertFalse(take(room, ["take"], inventory))
            self.assertFalse(take(room, ["take", "sword"], inventory))
            self.assertFalse(take(room, ["take", "compass"], inventory))
            self.assertTrue(take(room, ["take", "map"], inventory))
            self.assertTrue(take(room, ["take", "ball"], inventory))
        self.assertEqual(set(inventory.keys()), {"compass", "map", "ball"})
        self.assertEqual(room[keywords.General.ITEMS], {})
        self.assertEqual(room[keywords.General.DESCRIPTION], "test room")
        self.assertEqual(room[keywords.Direction.NORTH], "elsewhere")

    def test_result_independent_of_iteration_order(self):
        outcomes = set()
        for _ in range(20):
            room = make_room(["map", "ball", "globe"])
            inventory = {}
            with redirect_stdout(io.StringIO()):
                take(room, ["take", "ball"], inventory)
            outcomes.add((
                tuple(sorted(room[keywords.General.ITEMS].keys())),
                tuple(sorted(inventory.keys())),
            ))
        self.assertEqual(outcomes, {(("globe", "map"), ("ball",))})

    def test_rollback_when_inventory_assignment_fails(self):
        room = make_room(["map"])
        room_before = copy.deepcopy(room)

        class ExplodingDict(dict):
            def __setitem__(self, key, value):
                raise RuntimeError("inventory storage broken")

        with redirect_stdout(io.StringIO()):
            result = take(room, ["take", "map"], ExplodingDict())
        self.assertFalse(result)
        self.assertEqual(copy.deepcopy(room), room_before)
        self.assertIn("map", room[keywords.General.ITEMS])

    def test_rollback_when_location_delete_fails(self):
        class ExplodingItems(dict):
            def __delitem__(self, key):
                raise RuntimeError("floor is locked")

        room = {keywords.General.ITEMS: ExplodingItems({"map": item_registry["map"]})}
        inventory = {}
        room_before = copy.deepcopy(room)
        with redirect_stdout(io.StringIO()):
            result = take(room, ["take", "map"], inventory)
        self.assertFalse(result)
        self.assertEqual(inventory, {})
        self.assertEqual(set(room[keywords.General.ITEMS].keys()), {"map"})
        self.assertEqual(copy.deepcopy(room), room_before)

    def test_take_does_not_mutate_world_or_item_registry(self):
        from world.locations import locations as world_locations
        world_before = copy.deepcopy(world_locations)
        registry_before = copy.deepcopy(item_registry)
        room = make_room(["map"])
        inventory = {}
        with redirect_stdout(io.StringIO()):
            take(room, ["take", "map"], inventory)
            take(room, ["take"], {})
            take(room, ["take", "map"], inventory)
        self.assertEqual(copy.deepcopy(world_locations), world_before)
        self.assertEqual(copy.deepcopy(item_registry), registry_before)

    def test_room_without_items_key_does_not_crash(self):
        room = {keywords.General.DESCRIPTION: "bare room"}
        before = copy.deepcopy(room)
        with redirect_stdout(io.StringIO()):
            self.assertFalse(take(room, ["take", "map"], {}))
            self.assertFalse(take(room, ["take"], {}))
        self.assertEqual(copy.deepcopy(room), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
