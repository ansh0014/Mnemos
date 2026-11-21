"""Isolated Python Code Execution Sandbox with a hard 1.5s Watchdog."""

from __future__ import annotations

import builtins
import multiprocessing as mp
import time
from typing import Any, Callable

ALLOWED_IMPORTS = frozenset({"math", "bisect", "zlib", "hashlib", "collections", "heapq"})


def _safe_import(name: str, globals: Any = None, locals: Any = None, fromlist: Any = (), level: int = 0) -> Any:
    root = name.split(".")[0]
    if root not in ALLOWED_IMPORTS:
        raise ImportError(f"Module '{name}' is blocked inside the Mnemos verification sandbox.")
    return builtins.__import__(name, globals, locals, fromlist, level)


def _restricted_builtins() -> dict[str, Any]:
    safe_names = (
        "abs",
        "all",
        "any",
        "bool",
        "dict",
        "divmod",
        "enumerate",
        "Exception",
        "float",
        "hasattr",
        "getattr",
        "setattr",
        "int",
        "isinstance",
        "KeyError",
        "len",
        "list",
        "max",
        "min",
        "object",
        "pow",
        "range",
        "reversed",
        "round",
        "RuntimeError",
        "set",
        "sorted",
        "str",
        "sum",
        "tuple",
        "TypeError",
        "ValueError",
        "zip",
        "__build_class__",
    )
    allowed = {name: getattr(builtins, name) for name in safe_names}
    allowed["__import__"] = _safe_import
    allowed["print"] = lambda *args, **kwargs: None
    return allowed


def _sandbox_worker(
    user_code: str,
    driver_fn: Callable[[dict[str, Any]], dict[str, Any]],
    queue: Any,
) -> None:
    namespace: dict[str, Any] = {"__builtins__": _restricted_builtins(), "__name__": "__sandbox__"}
    try:
        compiled = compile(user_code, "<learner_solution>", "exec")
    except SyntaxError as exc:
        queue.put({"compile_error": f"SyntaxError on line {exc.lineno}: {exc.msg}"})
        return

    try:
        exec(compiled, namespace, namespace)  # noqa: S102
        output = driver_fn(namespace)
        queue.put({"result": output})
    except Exception as exc:
        queue.put({"runtime_error": f"{type(exc).__name__}: {exc}"})


def execute_in_sandbox(
    user_code: str,
    driver_fn: Callable[[dict[str, Any]], dict[str, Any]],
    timeout_s: float = 1.5,
) -> dict[str, Any]:
    """Execute user code + test/simulation driver inside a forked subprocess with timeout watchdog."""
    started = time.perf_counter()
    ctx = mp.get_context("fork")
    queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(target=_sandbox_worker, args=(user_code, driver_fn, queue))
    proc.start()
    proc.join(timeout_s)

    if proc.is_alive():
        proc.terminate()
        proc.join(0.2)
        if proc.is_alive():
            proc.kill()
            proc.join(0.2)
        return {
            "timed_out": True,
            "runtime_error": f"Execution exceeded {timeout_s:.1f}s CPU watchdog (possible infinite loop).",
            "execution_ms": round((time.perf_counter() - started) * 1000.0, 2),
        }

    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
    if queue.empty():
        return {
            "runtime_error": "Sandbox exited unexpectedly without producing output.",
            "execution_ms": elapsed_ms,
        }
    payload = queue.get()
    payload["execution_ms"] = elapsed_ms
    return payload
