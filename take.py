import copy

import keywords
from replies import snarky_replies


def take(current_location, command, inventory):

    location_snapshot = copy.deepcopy(current_location)
    inventory_snapshot = copy.deepcopy(inventory)

    try:
        if not isinstance(command, (list, tuple)) or len(command) < 2:
            snarky_replies.print_snarky_reply_bad_look_command()
            return False

        item_name = command[1]
        location_items = current_location.get(keywords.General.ITEMS)

        if not isinstance(location_items, dict) or item_name not in location_items:
            snarky_replies.print_snarky_reply_no_such_item(item_name)
            return False

        item = location_items[item_name]
        inventory[item_name] = item
        del location_items[item_name]

    except Exception:
        _restore_dict(current_location, location_snapshot)
        _restore_dict(inventory, inventory_snapshot)
        return False

    print(f"\n---> you take the {item_name} and it is added to your inventory\n")
    return True


def _restore_dict(target, snapshot):
    if not isinstance(target, dict):
        return
    dict.clear(target)
    dict.update(target, snapshot)
