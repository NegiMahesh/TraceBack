"""Utility functions — additional buggy code for TraceBack demos."""


def format_currency(amount, currency_data):
    """Format a currency amount.

    Bug: Accessing nested key without checking → TypeError.
    """
    symbol = currency_data["symbol"]
    precision = currency_data["precision"]
    formatted = f"{symbol}{amount:.{precision}f}"
    return formatted


def get_item_at_index(items, index):
    """Get an item from a list by index.

    Bug: No bounds checking → IndexError.
    """
    return items[index]


def process_config(config_path):
    """Load and process a configuration file.

    Bug: File may not exist → FileNotFoundError.
    """
    with open(config_path, "r") as f:
        return f.read()
