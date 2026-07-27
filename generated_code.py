```python
import pytest

# Assuming `is_palindrome` is imported or defined in the scope.
# from utils import is_palindrome 

def test_odd_length_palindrome():
    assert is_palindrome("racecar") is True

def test_even_length_palindrome():
    assert is_palindrome("abba") is True

def test_single_character():
    assert is_palindrome("a") is True

def test_empty_string():
    assert is_palindrome("") is True

def test_case_insensitive():
    assert is_palindrome("RaceCar") is True

def test_with_spaces():
    assert is_palindrome("A man a plan a canal Panama") is True

def test_with_punctuation():
    assert is_palindrome("Was it a car or a cat I saw?") is True

def test_mixed_case_punctuation():
    assert is_palindrome("No 'x' in Nixon") is True

def test_non_palindrome_basic():
    assert is_palindrome("hello") is False

def test_non_palindrome_mixed_case():
    assert is_palindrome("Python") is False

def test_numeric_palindrome():
    assert is_palindrome("12321") is True

def test_numeric_non_palindrome():
    assert is_palindrome("12345") is False

def test_only_punctuation():
    # Depending on implementation, stripping non-alphanumeric from "!!!" leaves "", which is a palindrome
    assert is_palindrome("!!!") is True

def test_palindrome_with_numbers_and_letters():
    assert is_palindrome("1a2b2a1") is True
```