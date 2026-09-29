from copy import deepcopy

import keywords
from replies import snarky_replies


def take(current_location, command, inventory):
    if not isinstance(command, (list, tuple)) or len(command) < 2:
        snarky_replies.print_snarky_reply_bad_action()
        return False

    item_name = command[1]
    location_items = current_location.get(keywords.General.ITEMS) if isinstance(current_location, dict) else None

    if (
        not isinstance(inventory, dict)
        or not isinstance(location_items, dict)
        or not isinstance(item_name, str)
        or item_name in inventory
        or item_name not in location_items
    ):
        snarky_replies.print_snarky_reply_no_such_item(item_name)
        return False

    item = location_items[item_name]
    location_snapshot = deepcopy(current_location)
    inventory_snapshot = deepcopy(inventory)

    try:
        inventory[item_name] = deepcopy(item)
        del location_items[item_name]
        print(f"\n---> you take the {item_name} and it is added to your inventory\n")
    except Exception:
        current_location.clear()
        current_location.update(location_snapshot)
        inventory.clear()
        inventory.update(inventory_snapshot)
        raise

    return True
