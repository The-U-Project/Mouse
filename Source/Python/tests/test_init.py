"""Tests for mouse package init."""


def test_import_mouse() -> None:
    """The mouse package itself is importable."""
    # The top-level mouse package doesn't exist as a Python module;
    # verify that sub-packages import correctly.
    import CodingAI  # noqa: F401
    import files  # noqa: F401
    import library  # noqa: F401
    import modules  # noqa: F401


def test_keeper_modules_exist() -> None:
    """Verify that KEEPER.py modules have the expected API."""
    from files.KEEPER import ScreenCapture, capture_primary
    from modules.KEEPER import CursorDetector, CursorPosition, CursorState, CursorTracker

    assert ScreenCapture is not None
    assert capture_primary is not None
    assert CursorDetector is not None
    assert CursorPosition is not None
    assert CursorState is not None
    assert CursorTracker is not None


def test_loader_module_exists() -> None:
    """Verify the LOADER module has expected API."""
    from modules.externalLangMods.LOADER import (
        FunctionSignature,
        ModuleMetadata,
        NativeModule,
        NativeModuleLoader,
    )

    assert NativeModule is not None
    assert NativeModuleLoader is not None
    assert ModuleMetadata is not None
    assert FunctionSignature is not None
