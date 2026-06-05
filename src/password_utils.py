"""Password utility functions for strength validation."""
import re


def validate_password_strength(password):
    """
    Validate password strength against security requirements.

    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: The password string to validate

    Returns:
        bool: True when the password meets all requirements.
    """
    errors = []

    # Check if password is None or not a string
    if password is None or not isinstance(password, str):
        return False

    # Check minimum length
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    # Check for uppercase
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")

    # Check for lowercase
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")

    # Check for digit
    if not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one digit")

    # Check for special character
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        errors.append("Password must contain at least one special character")

    is_valid = len(errors) == 0
    return is_valid


def get_password_strength_score(password):
    """
    Get a strength score for a password (0-100).

    Args:
        password: The password string to evaluate

    Returns:
        int: Strength score from 0 (weakest) to 100 (strongest)
    """
    if not password or not isinstance(password, str):
        return 0

    score = 0

    # Length score (up to 30 points)
    length = len(password)
    if length >= 12:
        score += 30
    elif length >= 10:
        score += 20
    elif length >= 8:
        score += 10

    # Character variety (up to 40 points)
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'[0-9]', password))
    has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password))

    variety_count = sum([has_upper, has_lower, has_digit, has_special])
    score += variety_count * 10

    # Complexity bonus (up to 30 points)
    if has_upper and has_lower:
        score += 10
    if has_digit and has_special:
        score += 10
    if variety_count == 4:
        score += 10

    return min(100, score)


def get_password_strength_label(password):
    """
    Get a human-readable strength label for a password.

    Args:
        password: The password string to evaluate

    Returns:
        str: Strength label (Very Weak, Weak, Fair, Strong, Very Strong)
    """
    score = get_password_strength_score(password)

    if score >= 80:
        return "Very Strong"
    elif score >= 60:
        return "Strong"
    elif score >= 40:
        return "Fair"
    elif score >= 20:
        return "Weak"
    else:
        return "Very Weak"
