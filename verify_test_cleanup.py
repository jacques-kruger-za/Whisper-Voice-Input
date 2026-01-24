"""Verification script for test_cleanup.py imports and basic functionality."""

import sys

# Test imports
try:
    from src.recognition.cleanup import cleanup_text, add_punctuation, _convert_spoken_punctuation
    from src.config.constants import FILLER_WORDS
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test basic functionality
try:
    # Test 1: Spoken punctuation before filler removal
    result = cleanup_text("um hello period how are you")
    assert "." in result, "Period not converted"
    assert "um" not in result.lower(), "Filler not removed"
    assert "period" not in result.lower(), "Punctuation word not converted"
    print("✓ Test 1: Spoken punctuation before filler removal - PASS")

    # Test 2: Multiple transformations
    result = cleanup_text("  um  hello  comma   world period  ")
    assert "," in result, "Comma not converted"
    assert "." in result, "Period not converted"
    assert "um" not in result.lower(), "Filler not removed"
    assert result[0].isupper(), "First letter not capitalized"
    print("✓ Test 2: Multiple transformations - PASS")

    # Test 3: Empty string handling
    result = cleanup_text("")
    assert result == "", "Empty string not handled"
    print("✓ Test 3: Empty string handling - PASS")

    # Test 4: Capitalization after punctuation
    result = cleanup_text("first sentence period second sentence")
    assert "First" in result, "First word not capitalized"
    assert "Second" in result, "Word after period not capitalized"
    print("✓ Test 4: Capitalization after punctuation - PASS")

    # Test 5: Helper function
    result = _convert_spoken_punctuation("hello period world")
    assert result == "hello. world", "Helper function failed"
    print("✓ Test 5: Helper function - PASS")

    # Test 6: Add punctuation function
    result = add_punctuation("hello world")
    assert result == "hello world.", "Period not added"
    result = add_punctuation("hello world.")
    assert result == "hello world.", "Extra period added"
    print("✓ Test 6: Add punctuation function - PASS")

    # Test 7: Real-world scenario
    result = cleanup_text("um hello comma my name is John period uh I like programming exclamation mark")
    assert "Hello" in result, "Capitalization failed"
    assert "," in result, "Comma not converted"
    assert "." in result, "Period not converted"
    assert "!" in result, "Exclamation not converted"
    assert "um" not in result.lower(), "Filler 'um' not removed"
    assert "uh" not in result.lower(), "Filler 'uh' not removed"
    print("✓ Test 7: Real-world scenario - PASS")

    print("\n✓✓✓ All verification tests passed! ✓✓✓")

except AssertionError as e:
    print(f"✗ Test failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
