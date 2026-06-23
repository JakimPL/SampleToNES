# Coding Guidelines

## General

1. Keep code modularized around clear ownership boundaries.
2. If a function has several meaningful steps, split them into helpers with one clear responsibility.
3. Do not abbreviate variable names. Use `note`, not `n`.
4. Avoid hardcoded semantic values. Prefer `Final` constants, and move them to a shared module when the concept is reused.
5. Use `pathlib.Path` instead of `os.path`.
6. Prefer protocols over inheritance.
7. Separate function options with `*`. Positional arguments should be intentionally chosen.
8. Prefer `match` statements over long `isinstance` chains, and for enumeration handling.
9. Do not preserve backward compatibility for internal APIs, configs, or data shapes unless the user explicitly asks for it.
10. Avoid _tramp data_ antipattern.
11. Be cautious about optional parameters. All variables upon the logic relies on cannot be optional, including configuration instances.
12. Restrict yourself from using default values for non-optional, excluding these that are not meant to be frequently changed (e.g. seed). If you do use defaults, declare a Final top-level constant for that.
13. Be explicit about type expectations. Avoid dynamic `getattr` or `hasattr`.
14. Prefer computable properties over stored boolean variables. A boolean derived from existing state should be a `@property` (or `@computed_field` on a Pydantic model) rather than a field that must be kept in sync manually. Stored booleans create hidden state branches that are easy to leave inconsistent.

## Shared Ownership

1. General-purpose helpers that are not model-specific belong in shared/common modules, not inside feature modules.
2. Do not create delegated imports or re-export modules just so other modules can import through them.
3. Import shared helpers directly from the module that owns their implementation.
4. Before adding a helper, search the repository for existing logic with `rg`.
5. If new code duplicates existing logic, extract the shared rule first and make both call sites use it.
6. `__init__` must not expose anything outside it's tree hierarchy.
7. If new code duplicates existing logic, extract the shared rule first and make both call sites use it.
8. Do not overload with a single module with too many different responsibilities.
9. Prefer subpackages over flatten directory structure.

## Type Hints

1. Specify all input and return types in function signatures, including `None`.
2. Fill generic types. Use `Dict[str, int]`, not `Dict`.
3. Do not cast/silence type errors unless the boundary is an untyped or mistyped third-party API.
4. Avoid `Any` and `object` unless the boundary genuinely accepts arbitrary data.
5. Do not quote type names. Use `from __future__ import annotations` (only if needed), `Self`, or `TYPE_CHECKING`.
6. Prefer classic typehints: `Dict[...]` instead of `dict[...]`, `Optional[...]` over `... | None` etc.
7. Validate with `mypy`.

## Error Handling

1. Let failures crash unless the code can recover meaningfully.
2. Handle errors at the execution boundary when possible.
3. Do not add `try`/`except` blocks that only repackage failures without recovery.
4. Bare `except` and `except Exception` are forbidden.
5. Error handling blocks should cover only the code that is subject to a failure, unless there is a valid reason.


## Models

1. Prefer Pydantic models for validated or serialized data.
2. Use `frozen` when instances are not meant to change.
3. Dataclasses are acceptable for small internal state objects that are not serialized or validated, including test case dataclasses.

## Documentation

1. Documentation should explain the intention of a class/function and context of usage.
2. If a function does some decisions, logic should be explained with a justification for arbitrary choices, in docstrings, not code comments.
3. Avoid comments and docstrings that restate code.
4. Use clear names instead of explanatory comments.
5. Avoid code comments. Comments are acceptable for tensor shapes, third-party API quirks, or non-obvious invariants.
6. Code comments and docstrings are not for documenting changes nor progress.

## Tests

1. Test files should mirror the ownership of the functionality under test.
2. When moving functionality between packages, move its direct unit tests in the same change.
3. Parametrize test functions of the same body and use test case dataclass.
4. Use test scenario suite class for defining more complex steps defined as series of functions with assertions.
5. Prefer fixtures over factories. Define shared fixtures in an appropriate place.
6. Do not assert default values of configurations, layouts, settings, and similar. Defaults are not contracts, and pinning them overconstrains the tests. Test behavior instead: validation bounds, serialization round-trips, and invariants. The exception is when values must match by contract rather than equal a chosen constant — e.g. project metadata at creation or after a save/load round-trip should be asserted to match, never hardcoded to a version string.
