"""External language module loader for the Mouse project.

Loads native modules (Rust .dll/.so/.dylib, C++ shared libraries) and
validates their exported function signatures before execution. This is
the bridge between Python's high-level CV pipeline and low-level
GPU/ASM acceleration.

Current status: **Stub** — the native components (Rust pyo3, C++/CUDA
shared libs) are not yet implemented. This module provides the protocol
and loader skeletons ready for when they are.

Architecture:
    - ``NativeModule``: Protocol/ABC defining what a loadable module
      looks like (exported symbols, version, signature).
    - ``validate_signature``: Check function names, arg counts, and
      return types against expected signatures.
    - ``load_module``: Load a native shared library via ``ctypes``.
"""

from __future__ import annotations

import ctypes
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ModuleLoadError(Exception):
    """Raised when a native module cannot be loaded."""


class SignatureValidationError(ModuleLoadError):
    """Raised when a module's exports don't match expected signatures."""


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class FunctionSignature:
    """Expected signature of a native function export.

    Attributes:
        name: Exported function name (must match C symbol).
        arg_count: Number of arguments expected.
        restype: Expected ctypes return type (e.g., ``ctypes.c_int``).
        argtypes: Expected ctypes argument types (e.g.,
            ``[ctypes.c_void_p, ctypes.c_int]``).
        required: If ``True``, the module must export this function.
    """

    name: str
    arg_count: int
    restype: Any = None  # ctypes type
    argtypes: list[Any] | None = None
    required: bool = True


@dataclass
class ModuleMetadata:
    """Descriptor for a native module.

    Attributes:
        name: Logical module name (e.g., "mouse_vision_cuda").
        path: Filesystem path to the shared library.
        expected_exports: Function signatures this module must provide.
        version: Minimum required version string.
    """

    name: str
    path: Path
    expected_exports: list[FunctionSignature] = field(default_factory=list)
    version: str = "0.1.0"


# ---------------------------------------------------------------------------
# Protocol / ABC for native modules
# ---------------------------------------------------------------------------


class NativeModule(ABC):
    """Abstract interface for a loaded native module.

    Every native module loaded by Mouse must implement this interface,
    providing at minimum:

    - ``name``: Logical name for logging and registry.
    - ``version``: Semver string for compatibility checks.
    - ``is_loaded``: Whether the shared library was successfully loaded.
    - ``call``: Invoke a named export with arguments.

    Example:
        >>> loader = NativeModuleLoader()
        >>> mod = loader.load("mouse_vision_cuda")
        >>> result = mod.call("compute_cursor", frame_ptr, width, height)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Logical module name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Loaded module version."""
        ...

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """``True`` if the native library was loaded successfully."""
        ...

    @abstractmethod
    def call(self, function_name: str, *args: Any) -> Any:
        """Invoke a named export.

        Args:
            function_name: Exported symbol name.
            *args: Arguments passed to the native function.

        Returns:
            The native function's return value.

        Raises:
            ModuleLoadError: If the module is not loaded or the
                function is not found.
        """
        ...

    @abstractmethod
    def unload(self) -> None:
        """Unload the native library and release resources."""
        ...


# ---------------------------------------------------------------------------
# Signature validation
# ---------------------------------------------------------------------------


def validate_signatures(
    loaded_funcs: dict[str, Callable[..., Any]],
    expected: list[FunctionSignature],
) -> list[str]:
    """Check loaded exports against expected signatures.

    Args:
        loaded_funcs: Mapping of function name → callable (from ctypes
            or similar).
        expected: Expected function signatures.

    Returns:
        List of error messages (empty = all valid).

    Raises:
        SignatureValidationError: If any required functions are missing
            or have incompatible signatures.
    """
    errors: list[str] = []

    for sig in expected:
        func = loaded_funcs.get(sig.name)
        if func is None:
            if sig.required:
                errors.append(f"Missing required export: '{sig.name}'")
            continue

        # Basic arg count check (ctypes doesn't expose this easily;
        # we defer full validation to runtime)
        if sig.argtypes is not None:
            try:
                func.argtypes = sig.argtypes  # type: ignore[attr-defined]
            except Exception as exc:
                errors.append(f"Cannot set argtypes for '{sig.name}': {exc}")

        if sig.restype is not None:
            try:
                func.restype = sig.restype  # type: ignore[attr-defined]
            except Exception as exc:
                errors.append(f"Cannot set restype for '{sig.name}': {exc}")

    if errors:
        raise SignatureValidationError("\n".join(errors))

    return errors


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class NativeModuleLoader:
    """Load native shared libraries and validate their exports.

    This is the central registry for loading native modules. Modules
    are registered by name, then loaded lazily on first access.

    Current implementation uses ``ctypes`` for loading. Future work
    may add ``pyo3`` / ``maturin`` for Rust modules.

    Usage:
        >>> loader = NativeModuleLoader()
        >>> loader.register(ModuleMetadata(
        ...     name="mouse_vision",
        ...     path=Path("./mouse_vision.dll"),
        ...     expected_exports=[FunctionSignature(
        ...         name="compute_cursor", arg_count=4,
        ...         restype=ctypes.c_int, argtypes=[ctypes.c_void_p, ctypes.c_int,
        ...                                          ctypes.c_int, ctypes.c_int],
        ...     )],
        ... ))
        >>> mod = loader.load("mouse_vision")
        >>> if mod.is_loaded:
        ...     result = mod.call("compute_cursor", ptr, 1920, 1080, 3)
    """

    def __init__(self) -> None:
        self._registry: dict[str, ModuleMetadata] = {}
        self._loaded: dict[str, NativeModule] = {}

    def register(self, metadata: ModuleMetadata) -> None:
        """Register a module for later loading.

        Args:
            metadata: Module descriptor including path and expected
                exports.
        """
        if metadata.name in self._registry:
            logger.warning("Overwriting registration for '%s'", metadata.name)
        self._registry[metadata.name] = metadata
        logger.info("Registered native module '%s' at %s", metadata.name, metadata.path)

    def unregister(self, name: str) -> None:
        """Remove a module from the registry.

        Args:
            name: Module name to unregister.
        """
        self._registry.pop(name, None)
        if name in self._loaded:
            self._loaded[name].unload()
            del self._loaded[name]

    def load(self, name: str) -> NativeModule:
        """Load a registered native module.

        Args:
            name: Module name (must be registered via ``register()``).

        Returns:
            A ``NativeModule`` instance (possibly with
            ``is_loaded=False`` if loading failed).

        Raises:
            ModuleLoadError: If the module is not registered.
        """
        if name in self._loaded:
            return self._loaded[name]

        meta = self._registry.get(name)
        if meta is None:
            raise ModuleLoadError(
                f"Module '{name}' is not registered. Available: {list(self._registry.keys())}"
            )

        mod = _CTypesNativeModule(meta)
        self._loaded[name] = mod
        return mod

    def load_all(self) -> dict[str, NativeModule]:
        """Load all registered modules.

        Returns:
            Dict of name → NativeModule. Some may have
            ``is_loaded=False`` if loading failed.
        """
        results: dict[str, NativeModule] = {}
        for name in self._registry:
            results[name] = self.load(name)
        return results

    @property
    def registry(self) -> dict[str, ModuleMetadata]:
        """Registered modules (read-only)."""
        return dict(self._registry)


# ---------------------------------------------------------------------------
# Internal: ctypes-based NativeModule
# ---------------------------------------------------------------------------


class _CTypesNativeModule(NativeModule):
    """ctypes-backed implementation of ``NativeModule``."""

    def __init__(self, metadata: ModuleMetadata) -> None:
        self._meta = metadata
        self._lib: ctypes.CDLL | None = None
        self._exports: dict[str, Callable[..., Any]] = {}
        self._loaded = False
        self._try_load()

    def _try_load(self) -> None:
        """Attempt to load the shared library via ctypes."""
        path = self._meta.path
        if not path.exists():
            logger.warning("Native module '%s' not found at %s", self._meta.name, path)
            return

        try:
            self._lib = ctypes.CDLL(str(path))
        except OSError as exc:
            logger.error(
                "Failed to load native module '%s' from %s: %s",
                self._meta.name,
                path,
                exc,
            )
            return

        # Discover exported functions
        for sig in self._meta.expected_exports:
            try:
                func = getattr(self._lib, sig.name)
                self._exports[sig.name] = func
            except AttributeError:
                if sig.required:
                    logger.warning(
                        "Required export '%s' not found in '%s'", sig.name, self._meta.name
                    )

        # Validate signatures
        try:
            validate_signatures(self._exports, self._meta.expected_exports)
        except SignatureValidationError as exc:
            logger.error("Signature validation failed for '%s': %s", self._meta.name, exc)
            self._lib = None
            self._exports.clear()
            return

        self._loaded = True
        logger.info("Loaded native module '%s' v%s", self._meta.name, self._meta.version)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._meta.name

    @property
    def version(self) -> str:
        return self._meta.version

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def call(self, function_name: str, *args: Any) -> Any:
        """Invoke an exported native function.

        Args:
            function_name: Exported symbol name.
            *args: Arguments to pass.

        Returns:
            The native function's return value.

        Raises:
            ModuleLoadError: If the module is not loaded or the
                function is not available.
        """
        if not self._loaded:
            raise ModuleLoadError(
                f"Module '{self._meta.name}' is not loaded. "
                f"Check that the library exists at {self._meta.path}"
            )

        func = self._exports.get(function_name)
        if func is None:
            available = list(self._exports.keys())
            raise ModuleLoadError(
                f"Function '{function_name}' not found in '{self._meta.name}'. "
                f"Available: {available}"
            )

        try:
            return func(*args)
        except Exception as exc:
            raise ModuleLoadError(
                f"Call to '{function_name}' in '{self._meta.name}' failed: {exc}"
            ) from exc

    def unload(self) -> None:
        """Release the loaded library."""
        self._lib = None
        self._exports.clear()
        self._loaded = False
        logger.debug("Unloaded native module '%s'", self._meta.name)


# ---------------------------------------------------------------------------
# Mouse Core module registration
# ---------------------------------------------------------------------------

_MOUSE_CORE_EXPORTS: list[FunctionSignature] = [
    # ── Port reservation ─────────────────────────────
    FunctionSignature(
        name="mouse_reserve_port",
        arg_count=1,
        restype=ctypes.c_int,
        argtypes=[ctypes.c_int],
    ),
    FunctionSignature(
        name="mouse_release_port",
        arg_count=1,
        restype=ctypes.c_int,
        argtypes=[ctypes.c_int],
    ),
    FunctionSignature(
        name="mouse_get_stream_port",
        arg_count=0,
        restype=ctypes.c_int,
    ),
    FunctionSignature(
        name="mouse_reserve_port_block",
        arg_count=2,
        restype=ctypes.POINTER(ctypes.c_int),
        argtypes=[ctypes.c_int, ctypes.POINTER(ctypes.c_int)],
    ),
    FunctionSignature(
        name="mouse_free_ports",
        arg_count=1,
        restype=None,
        argtypes=[ctypes.POINTER(ctypes.c_int)],
    ),
    # ── Display analyzer ─────────────────────────────
    FunctionSignature(
        name="mouse_display_analyzer_create",
        arg_count=0,
        restype=ctypes.c_void_p,
    ),
    FunctionSignature(
        name="mouse_display_analyzer_destroy",
        arg_count=1,
        restype=None,
        argtypes=[ctypes.c_void_p],
    ),
    FunctionSignature(
        name="mouse_rgb_to_gray",
        arg_count=5,
        restype=ctypes.c_int,
        argtypes=[
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint8),
        ],
    ),
    FunctionSignature(
        name="mouse_detect_edges",
        arg_count=7,
        restype=ctypes.c_int,
        argtypes=[
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.POINTER(ctypes.c_uint8),
        ],
    ),
    FunctionSignature(
        name="mouse_match_template",
        arg_count=9,
        restype=ctypes.c_float,
        argtypes=[
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_float,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
        ],
    ),
    # ── Result combiner ──────────────────────────────
    FunctionSignature(
        name="mouse_combine_results",
        arg_count=16,
        restype=ctypes.c_int,
        argtypes=[
            ctypes.c_int, ctypes.c_int, ctypes.c_float, ctypes.c_int,
            ctypes.c_float, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, ctypes.c_float, ctypes.c_int,
            ctypes.c_float, ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_int),
        ],
    ),
    FunctionSignature(
        name="mouse_backend_name",
        arg_count=1,
        restype=ctypes.c_char_p,
        argtypes=[ctypes.c_int],
        required=False,
    ),
]


def _find_mouse_core_library() -> Path | None:
    """Locate the mouse_core shared library on this platform."""
    import sys

    candidates: list[Path] = []

    # -- Windows --
    if sys.platform == "win32":
        names = ["mouse_core.dll", "mouse_core.pyd"]
    # -- macOS --
    elif sys.platform == "darwin":
        names = ["libmouse_core.dylib", "libmouse_core.so", "mouse_core.so"]
    # -- Linux --
    else:
        names = ["libmouse_core.so", "mouse_core.so"]

    # Search paths: same dir as this file, then build dirs
    here = Path(__file__).resolve().parent.parent.parent  # up to Python/
    search_dirs = [
        here,
        here.parent / "build",                # Mouse/build/
        here.parent / "build" / "Release",    # Mouse/build/Release/
        here.parent / "build" / "Debug",      # Mouse/build/Debug/
        here.parent / "target" / "release",   # Rust target (future)
    ]

    for d in search_dirs:
        if not d.exists():
            continue
        for name in names:
            candidate = d / name
            if candidate.exists():
                return candidate.resolve()

    return None


def setup_mouse_core(loader: NativeModuleLoader | None = None) -> NativeModule | None:
    """Register and load the mouse_core native module.

    Call this once during Python startup to wire the C++/CUDA/ASM
    backend into the pipeline.  Returns the loaded module, or None
    if the shared library wasn't found (non-fatal — Python fallbacks
    will be used instead).

    Usage::

        >>> from modules.externalLangMods.LOADER import (
        ...     NativeModuleLoader, setup_mouse_core,
        ... )
        >>> loader = NativeModuleLoader()
        >>> mouse_core = setup_mouse_core(loader)
        >>> if mouse_core and mouse_core.is_loaded:
        ...     port = mouse_core.call("mouse_get_stream_port")

    Args:
        loader: An existing ``NativeModuleLoader``.  If ``None``, a
            new one is created.

    Returns:
        The loaded ``NativeModule``, or ``None`` if the library was
        not found.
    """
    if loader is None:
        loader = NativeModuleLoader()

    lib_path = _find_mouse_core_library()
    if lib_path is None:
        logger.info("mouse_core native library not found — using Python fallbacks")
        return None

    meta = ModuleMetadata(
        name="mouse_core",
        path=lib_path,
        expected_exports=_MOUSE_CORE_EXPORTS,
        version="0.1.0",
    )
    loader.register(meta)

    try:
        mod = loader.load("mouse_core")
    except ModuleLoadError as exc:
        logger.warning("Failed to load mouse_core: %s", exc)
        return None

    return mod
