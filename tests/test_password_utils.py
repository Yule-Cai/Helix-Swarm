import pytest
from password_utils import validate_password_strength


def test_valid_password():
    """Test password that meets all requirements"""
    assert validate_password_strength("MyPass123!") == True


def test_too_short():
    """Test password shorter than 8 characters"""
    assert validate_password_strength("Pass1!") == False


def test_missing_uppercase():
    """Test password without uppercase letter"""
    assert validate_password_strength("mypass123!") == False


def test_missing_lowercase():
    """Test password without lowercase letter"""
    assert validate_password_strength("MYPASS123!") == False


def test_missing_digit():
    """Test password without digit"""
    assert validate_password_strength("MyPassword!") == False


def test_missing_special_char():
    """Test password without special character"""
    assert validate_password_strength("MyPass123") == False


def test_empty_string():
    """Test empty password"""
    assert validate_password_strength("") == False


def test_none_input():
    """Test None input"""
    assert validate_password_strength(None) == False
