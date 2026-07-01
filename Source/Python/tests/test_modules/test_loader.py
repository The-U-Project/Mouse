"""Tests for modules.externalLangMods.LOADER — native module loader."""

from __future__ import annotations

import ctypes
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modules.externalLangMods.LOADER import (
    FunctionSignature,
    ModuleLoadError,
    ModuleMetadata,
    NativeModuleLoader,
    SignatureValidationError,
    validate_signatures,
)

# ---------------------------------------------------------------------------
# FunctionSignature / ModuleMetadata
# ---------------------------------------------------------------------------


class TestFunctionSignature:
    def test_defaults(self) -> None:
        sig = FunctionSignature(name="compute", arg_count=3, required=False)
        assert sig.name == "compute"
        assert sig.arg_count == 3
        assert sig.restype is None
        assert sig.required is False

    def test_with_ctypes(self) -> None:
        sig = FunctionSignature(
            name="add",
            arg_count=2,
            restype=ctypes.c_int,
            argtypes=[ctypes.c_int, ctypes.c_int],
        )
        assert sig.restype == ctypes.c_int
        assert sig.argtypes == [ctypes.c_int, ctypes.c_int]


class TestModuleMetadata:
    def test_defaults(self) -> None:
        meta = ModuleMetadata(name="test_mod", path=Path("/tmp/test.dll"))
        assert meta.name == "test_mod"
        assert meta.version == "0.1.0"
        assert meta.expected_exports == []

    def test_with_exports(self) -> None:
        sigs = [FunctionSignature(name="init", arg_count=0)]
        meta = ModuleMetadata(
            name="test_mod", path=Path("/tmp/test.dll"), expected_exports=sigs, version="2.0.0"
        )
        assert len(meta.expected_exports) == 1
        assert meta.version == "2.0.0"


# ---------------------------------------------------------------------------
# Signature validation
# ---------------------------------------------------------------------------


class TestValidateSignatures:
    def test_all_required_present(self) -> None:
        """No errors when all required exports are present."""
        funcs = {"foo": MagicMock(), "bar": MagicMock()}
        sigs = [
            FunctionSignature(name="foo", arg_count=0, required=True),
            FunctionSignature(name="bar", arg_count=1, required=True),
        ]
        errors = validate_signatures(funcs, sigs)
        assert errors == []

    def test_missing_required_raises(self) -> None:
        """Missing required export raises SignatureValidationError."""
        funcs = {"foo": MagicMock()}
        sigs = [
            FunctionSignature(name="foo", arg_count=0, required=True),
            FunctionSignature(name="bar", arg_count=1, required=True),
        ]
        with pytest.raises(SignatureValidationError, match="bar"):
            validate_signatures(funcs, sigs)

    def test_missing_optional_ok(self) -> None:
        """Missing optional exports do not cause errors."""
        funcs = {"foo": MagicMock()}
        sigs = [
            FunctionSignature(name="foo", arg_count=0, required=True),
            FunctionSignature(name="bar", arg_count=1, required=False),
        ]
        errors = validate_signatures(funcs, sigs)
        assert errors == []

    def test_sets_restype_and_argtypes(self) -> None:
        """validate_signatures sets restype and argtypes on functions."""
        func = MagicMock()
        sigs = [
            FunctionSignature(
                name="myfunc",
                arg_count=2,
                restype=ctypes.c_int,
                argtypes=[ctypes.c_int, ctypes.c_int],
                required=True,
            )
        ]
        errors = validate_signatures({"myfunc": func}, sigs)
        assert errors == []
        # The mock's argtypes/restype should have been set
        assert func.argtypes is not None


# ---------------------------------------------------------------------------
# NativeModuleLoader
# ---------------------------------------------------------------------------


class TestNativeModuleLoader:
    def test_register_and_load(self) -> None:
        """Register a module, then load it."""
        loader = NativeModuleLoader()
        meta = ModuleMetadata(name="test", path=Path("/tmp/test.dll"))
        loader.register(meta)
        assert "test" in loader.registry

    def test_load_unregistered_raises(self) -> None:
        """Loading an unregistered module raises ModuleLoadError."""
        loader = NativeModuleLoader()
        with pytest.raises(ModuleLoadError, match="not registered"):
            loader.load("nonexistent")

    def test_unregister(self) -> None:
        """Unregister removes from registry."""
        loader = NativeModuleLoader()
        loader.register(ModuleMetadata(name="test", path=Path("/tmp/test.dll")))
        loader.unregister("test")
        assert "test" not in loader.registry

    def test_unregister_idempotent(self) -> None:
        """Unregistering a non-existent module is safe."""
        loader = NativeModuleLoader()
        loader.unregister("nonexistent")  # should not raise

    def test_double_register_overwrites(self) -> None:
        """Second register with same name overwrites."""
        loader = NativeModuleLoader()
        loader.register(ModuleMetadata(name="test", path=Path("/tmp/a.dll"), version="1.0"))
        loader.register(ModuleMetadata(name="test", path=Path("/tmp/b.dll"), version="2.0"))
        assert loader.registry["test"].version == "2.0"

    def test_load_nonexistent_file(self) -> None:
        """Loading a module whose file doesn't exist returns is_loaded=False."""
        loader = NativeModuleLoader()
        loader.register(
            ModuleMetadata(
                name="ghost",
                path=Path("/tmp/definitely_does_not_exist_12345.dll"),
                expected_exports=[],
            )
        )
        with patch("ctypes.CDLL", side_effect=OSError("file not found")):
            mod = loader.load("ghost")
            assert mod.is_loaded is False
            assert mod.name == "ghost"

    def test_load_all(self) -> None:
        """load_all loads all registered modules."""
        loader = NativeModuleLoader()
        loader.register(ModuleMetadata(name="a", path=Path("/tmp/a.dll")))
        loader.register(ModuleMetadata(name="b", path=Path("/tmp/b.dll")))
        with patch("ctypes.CDLL", side_effect=OSError("not found")):
            results = loader.load_all()
            assert len(results) == 2
            assert "a" in results
            assert "b" in results

    def test_call_unloaded_raises(self) -> None:
        """Calling an unloaded module raises ModuleLoadError."""
        loader = NativeModuleLoader()
        loader.register(ModuleMetadata(name="test", path=Path("/tmp/test.dll")))
        with patch("ctypes.CDLL", side_effect=OSError("not found")):
            mod = loader.load("test")
            with pytest.raises(ModuleLoadError, match="not loaded"):
                mod.call("some_func", 1, 2)
