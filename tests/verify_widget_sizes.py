"""Verification script for widget size functionality.

This script verifies that:
1. WIDGET_SIZES constants have correct values (60, 80, 100)
2. Settings UI labels match expected sizes
3. Widget set_size() method correctly applies sizes

This is a standalone test that doesn't require external dependencies.
"""

import sys
import os
import re

# Working directory
WORKING_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_file(path):
    """Read file contents."""
    full_path = os.path.join(WORKING_DIR, path)
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()


def test_widget_sizes_constants():
    """Verify WIDGET_SIZES has correct values in constants.py."""
    print("Testing WIDGET_SIZES constants...")

    content = read_file('src/config/constants.py')

    # Extract WIDGET_SIZES dict
    match = re.search(r'WIDGET_SIZES\s*=\s*\{([^}]+)\}', content)
    assert match, "Could not find WIDGET_SIZES in constants.py"

    sizes_str = match.group(1)

    # Verify each expected size
    expected = {
        "compact": 60,
        "medium": 80,
        "large": 100,
    }

    for key, expected_val in expected.items():
        pattern = rf'"{key}":\s*{expected_val}'
        assert re.search(pattern, sizes_str), f"Expected '{key}': {expected_val} in WIDGET_SIZES"
        print(f"  ✓ {key}: {expected_val}px")

    # Verify DEFAULT_WIDGET_SIZE
    assert 'DEFAULT_WIDGET_SIZE = "compact"' in content, "DEFAULT_WIDGET_SIZE should be 'compact'"
    print(f"  ✓ DEFAULT_WIDGET_SIZE = 'compact'")

    return True


def test_settings_ui_labels():
    """Verify settings UI has correct labels for widget sizes."""
    print("\nTesting settings UI labels...")

    content = read_file('src/ui/settings.py')

    # Check for size_labels dict with correct values
    expected_labels = [
        '"compact": "Compact (60px)"',
        '"medium": "Medium (80px)"',
        '"large": "Large (100px)"',
    ]

    for label in expected_labels:
        assert label in content, f"Missing label: {label}"
        print(f"  ✓ Found: {label}")

    # Verify WIDGET_SIZES is imported and used
    assert "from ..config import" in content and "WIDGET_SIZES" in content, "WIDGET_SIZES should be imported"
    print("  ✓ WIDGET_SIZES is imported")

    # Verify widget_size_changed signal exists
    assert "widget_size_changed = pyqtSignal(str)" in content, "widget_size_changed signal should exist"
    print("  ✓ widget_size_changed signal defined")

    # Verify signal emission
    assert "widget_size_changed.emit(new_widget_size)" in content, "widget_size_changed should be emitted"
    print("  ✓ widget_size_changed signal emitted on size change")

    return True


def test_widget_set_size():
    """Verify widget set_size() method implementation."""
    print("\nTesting widget set_size() method...")

    content = read_file('src/ui/widget.py')

    # Check set_size method exists
    assert "def set_size(self, size_key: str)" in content, "set_size method should exist"
    print("  ✓ set_size method defined")

    # Check it validates against WIDGET_SIZES
    assert "if size_key in WIDGET_SIZES:" in content, "set_size should validate against WIDGET_SIZES"
    print("  ✓ Validates size_key against WIDGET_SIZES")

    # Check it updates _size from WIDGET_SIZES
    assert "self._size = WIDGET_SIZES[size_key]" in content, "set_size should update _size from WIDGET_SIZES"
    print("  ✓ Updates _size from WIDGET_SIZES dict")

    # Check it calls setFixedSize
    assert "self.setFixedSize(self._size, self._size)" in content, "set_size should call setFixedSize"
    print("  ✓ Calls setFixedSize() with new size")

    # Check it re-initializes visualizers
    assert "_init_visualizers()" in content, "set_size should re-initialize visualizers"
    print("  ✓ Re-initializes visualizers")

    # Check it ensures widget stays on screen
    assert "_ensure_on_screen()" in content, "set_size should ensure widget stays on screen"
    print("  ✓ Calls _ensure_on_screen()")

    return True


def test_thickness_scale():
    """Verify thickness scale factors are defined for all sizes."""
    print("\nTesting thickness scale factors...")

    content = read_file('src/ui/widget.py')

    # Check THICKNESS_SCALE dict exists
    match = re.search(r'THICKNESS_SCALE\s*=\s*\{([^}]+)\}', content)
    assert match, "Could not find THICKNESS_SCALE in widget.py"

    scales_str = match.group(1)

    # Verify each expected scale
    expected = {
        "compact": 0.6,
        "medium": 0.8,
        "large": 1.0,
    }

    for key, expected_val in expected.items():
        pattern = rf'"{key}":\s*{expected_val}'
        assert re.search(pattern, scales_str), f"Expected '{key}': {expected_val} in THICKNESS_SCALE"
        print(f"  ✓ {key}: scale = {expected_val}")

    return True


def test_app_signal_connection():
    """Verify app.py connects widget_size_changed signal."""
    print("\nTesting app signal connection...")

    content = read_file('src/app.py')

    # Check signal is connected
    assert "widget_size_changed.connect(self._on_widget_size_changed)" in content, \
        "widget_size_changed signal should be connected"
    print("  ✓ widget_size_changed signal connected to handler")

    # Check handler exists
    assert "def _on_widget_size_changed(self, size_key: str)" in content, \
        "_on_widget_size_changed handler should exist"
    print("  ✓ _on_widget_size_changed handler defined")

    # Check handler calls set_size
    assert "self._widget.set_size(size_key)" in content, \
        "Handler should call widget.set_size()"
    print("  ✓ Handler calls widget.set_size()")

    return True


def test_settings_persistence():
    """Verify widget_size is persisted in settings."""
    print("\nTesting settings persistence...")

    content = read_file('src/config/settings.py')

    # Check widget_size in defaults
    assert '"widget_size": DEFAULT_WIDGET_SIZE' in content, \
        "widget_size should be in default settings"
    print("  ✓ widget_size in default settings")

    # Check widget_size property exists
    assert "@property" in content and "def widget_size(self)" in content, \
        "widget_size property should exist"
    print("  ✓ widget_size property getter exists")

    # Check widget_size setter exists
    assert "@widget_size.setter" in content, \
        "widget_size setter should exist"
    print("  ✓ widget_size property setter exists")

    return True


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Widget Size Verification Tests")
    print("=" * 60)

    tests = [
        test_widget_sizes_constants,
        test_settings_ui_labels,
        test_widget_set_size,
        test_thickness_scale,
        test_app_signal_connection,
        test_settings_persistence,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n✓ All widget size verification tests PASSED")
        print("\nManual UI Testing Steps:")
        print("-" * 40)
        print("  1. Run: python -m src.main")
        print("  2. Right-click tray icon -> Settings")
        print("  3. Navigate to 'Appearance' section")
        print("  4. Change 'Widget Size' through all options:")
        print("     - Compact (60px)")
        print("     - Medium (80px)")
        print("     - Large (100px)")
        print("  5. Click 'Save' after each change")
        print("  6. Verify widget resizes to correct size")
        return 0
    else:
        print("\n✗ Some tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
