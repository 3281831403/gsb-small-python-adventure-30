import builtins
import copy
import io
import unittest
from contextlib import redirect_stdout

import keywords
from take import take


ITEMS = keywords.General.ITEMS

SUCCESS_MESSAGE = (
    "\n---> you take the map and it is added to your inventory\n\n"
)
BAD_ACTION_MESSAGE = (
    f"legal command actions begin with one of the following: {keywords.allowed_actions}\n"
)
NO_MAP_MESSAGE = (
    "That's funny, I don't see map anywhere in this location.\n"
)


def map_item():
    return {"description": "map", "marks": ["town"]}


def compass_item():
    return {"description": "compass"}


def two_item_world():
    return {
        "room": {ITEMS: {"map": map_item(), "compass": compass_item()}},
        "inventory": {},
    }


def reversed_item_world():
    return {
        "room": {ITEMS: {"compass": compass_item(), "map": map_item()}},
        "inventory": {},
    }


def duplicate_item_world():
    return {
        "room": {ITEMS: {"map": map_item(), "compass": compass_item()}},
        "inventory": {"map": map_item()},
    }


def other_room_world():
    world = two_item_world()
    world["other_room"] = {ITEMS: {"map": map_item()}}
    return world


def room_without_items_mapping():
    return {"room": {}, "inventory": {}}


def room_with_invalid_items_mapping():
    return {"room": {ITEMS: []}, "inventory": {}}


def invalid_inventory_world():
    return {"room": {ITEMS: {"map": map_item()}}, "inventory": []}


TAKE_CASES = [
    {
        "name": "success moves requested item",
        "setup": two_item_world,
        "command": ["take", "map"],
        "result": True,
        "output": SUCCESS_MESSAGE,
    },
    {
        "name": "success is stable with reverse item order",
        "setup": reversed_item_world,
        "command": ["take", "map"],
        "result": True,
        "output": SUCCESS_MESSAGE,
    },
    {
        "name": "success leaves unrelated item in place",
        "setup": two_item_world,
        "command": ["take", "map"],
        "result": True,
        "output": SUCCESS_MESSAGE,
    },
    {
        "name": "success only changes current room",
        "setup": other_room_world,
        "command": ["take", "map"],
        "result": True,
        "output": SUCCESS_MESSAGE,
    },
    {
        "name": "tuple command is accepted",
        "setup": two_item_world,
        "command": ("take", "map"),
        "result": True,
        "output": SUCCESS_MESSAGE,
    },
    {
        "name": "extra arguments do not hide requested item",
        "setup": two_item_world,
        "command": ["take", "map", "quickly"],
        "result": True,
        "output": SUCCESS_MESSAGE,
    },
    {
        "name": "missing item argument does not crash",
        "setup": two_item_world,
        "command": ["take"],
        "result": False,
        "output": BAD_ACTION_MESSAGE,
        "follow_up": ["take", "map"],
    },
    {
        "name": "empty command does not crash",
        "setup": two_item_world,
        "command": [],
        "result": False,
        "output": BAD_ACTION_MESSAGE,
        "follow_up": ["take", "map"],
    },
    {
        "name": "non-sequence command does not crash",
        "setup": two_item_world,
        "command": "take map",
        "result": False,
        "output": BAD_ACTION_MESSAGE,
        "follow_up": ["take", "map"],
    },
    {
        "name": "none command does not crash",
        "setup": two_item_world,
        "command": None,
        "result": False,
        "output": BAD_ACTION_MESSAGE,
    },
    {
        "name": "unknown item fails without mutation",
        "setup": two_item_world,
        "command": ["take", "compass-that-broke"],
        "result": False,
        "output": "That's funny, I don't see compass-that-broke anywhere in this location.\n",
        "follow_up": ["take", "map"],
    },
    {
        "name": "duplicate item is not taken again",
        "setup": duplicate_item_world,
        "command": ["take", "map"],
        "result": False,
        "output": NO_MAP_MESSAGE,
        "follow_up": ["take", "compass"],
    },
    {
        "name": "duplicate item leaves room copy untouched",
        "setup": duplicate_item_world,
        "command": ["take", "map"],
        "result": False,
        "output": NO_MAP_MESSAGE,
    },
    {
        "name": "missing items mapping fails safely",
        "setup": room_without_items_mapping,
        "command": ["take", "map"],
        "result": False,
        "output": NO_MAP_MESSAGE,
    },
    {
        "name": "invalid items mapping fails safely",
        "setup": room_with_invalid_items_mapping,
        "command": ["take", "map"],
        "result": False,
        "output": NO_MAP_MESSAGE,
    },
    {
        "name": "invalid inventory fails safely",
        "setup": invalid_inventory_world,
        "command": ["take", "map"],
        "result": False,
        "output": NO_MAP_MESSAGE,
    },
    {
        "name": "non-string item name fails safely",
        "setup": two_item_world,
        "command": ["take", 7],
        "result": False,
        "output": "That's funny, I don't see 7 anywhere in this location.\n",
    },
    {
        "name": "unhashable item name fails safely",
        "setup": two_item_world,
        "command": ["take", ["map"]],
        "result": False,
        "output": "That's funny, I don't see ['map'] anywhere in this location.\n",
    },
]


class TakeTests(unittest.TestCase):

    def test_table_driven_take_behaviour(self):
        for case in TAKE_CASES:
            with self.subTest(case["name"]):
                world = case["setup"]()
                before = copy.deepcopy(world)
                output = io.StringIO()

                with redirect_stdout(output):
                    result = take(
                        world["room"],
                        case["command"],
                        world["inventory"],
                    )

                expected_world = self.expected_world_after(before, case)
                self.assertEqual(result, case["result"])
                self.assertEqual(world, expected_world)
                self.assertEqual(output.getvalue(), case["output"])

                if "follow_up" in case:
                    follow_up_output = io.StringIO()
                    with redirect_stdout(follow_up_output):
                        follow_up_result = take(
                            world["room"],
                            case["follow_up"],
                            world["inventory"],
                        )
                    follow_up_name = case["follow_up"][1]
                    self.assertTrue(follow_up_result)
                    self.assertEqual(
                        follow_up_output.getvalue(),
                        f"\n---> you take the {follow_up_name} and it is added to your inventory\n\n",
                    )

    def expected_world_after(self, before, case):
        expected = copy.deepcopy(before)
        if not case["result"]:
            return expected

        item_name = case["command"][1]
        item = expected["room"][ITEMS].pop(item_name)
        expected["inventory"][item_name] = item
        return expected

    def test_successful_take_deep_copies_item(self):
        world = two_item_world()
        source_item = world["room"][ITEMS]["map"]
        before = copy.deepcopy(world)

        result = self.run_quietly(world, ["take", "map"])

        self.assertTrue(result)
        taken_item = world["inventory"]["map"]
        self.assertEqual(taken_item, before["room"][ITEMS]["map"])
        self.assertIsNot(taken_item, source_item)

        taken_item["marks"].append("forest")
        self.assertEqual(source_item["marks"], ["town"])

    def test_repeated_take_is_consistent(self):
        world = two_item_world()

        first = self.run_quietly(world, ["take", "map"])
        first_duplicate = copy.deepcopy(world)
        second = self.run_quietly(world, ["take", "map"])

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(world, first_duplicate)
        self.assertEqual(list(world["inventory"]), ["map"])
        self.assertNotIn("map", world["room"][ITEMS])

    def test_extra_arguments_do_not_break_later_take(self):
        world = two_item_world()

        self.assertTrue(self.run_quietly(world, ["take", "map", "extra"]))
        self.assertTrue(self.run_quietly(world, ["take", "compass"]))

    def test_print_failure_rolls_back_both_states(self):
        world = two_item_world()
        before = copy.deepcopy(world)
        original_print = builtins.print

        def failing_print(*args, **kwargs):
            raise RuntimeError("output failed")

        builtins.print = failing_print
        try:
            with self.assertRaises(RuntimeError):
                take(world["room"], ["take", "map"], world["inventory"])
        finally:
            builtins.print = original_print

        self.assertEqual(world, before)
        self.assertTrue(self.run_quietly(world, ["take", "map"]))

    def test_result_does_not_depend_on_item_mapping_order(self):
        forward = two_item_world()
        reverse = reversed_item_world()

        self.assertTrue(self.run_quietly(forward, ["take", "compass"]))
        self.assertTrue(self.run_quietly(reverse, ["take", "compass"]))

        self.assertEqual(
            forward["room"][ITEMS],
            reverse["room"][ITEMS],
        )
        self.assertEqual(
            forward["inventory"],
            reverse["inventory"],
        )

    def run_quietly(self, world, command):
        with redirect_stdout(io.StringIO()):
            return take(world["room"], command, world["inventory"])


if __name__ == "__main__":
    unittest.main()
