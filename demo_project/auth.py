"""Authentication module — deliberately buggy for TraceBack demo.

This module demonstrates a realistic ZeroDivisionError that TraceBack
will detect, diagnose, fix, and verify.
"""


def login_user(user_data):
    """Authenticate a user and calculate risk score.

    Bug: trust_level defaults to 0, causing ZeroDivisionError.
    """
    username = user_data.get("username", "unknown")
    trust_level = user_data.get("trust_level", 0)
    risk_score = 100 / trust_level
    return {
        "status": "success",
        "username": username,
        "risk": risk_score,
        "trust_level": trust_level,
    }


def get_user_profile(user_id):
    """Retrieve a user profile.

    Bug: Missing key access without .get() → KeyError.
    """
    profiles = {
        1: {"name": "Alice", "role": "admin"},
        2: {"name": "Bob", "role": "user"},
    }
    profile = profiles[user_id]  # KeyError if user_id not in dict
    return profile


def calculate_score(values):
    """Calculate average score.

    Bug: Empty list → ZeroDivisionError.
    """
    total = sum(values)
    average = total / len(values)
    return average


if __name__ == "__main__":
    # This will crash with ZeroDivisionError
    print("Attempting login...")
    result = login_user({"username": "admin"})
    print(f"Login result: {result}")
