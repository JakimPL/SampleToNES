# Coding Guidelines

## General

1. Keep code modularized around clear ownership boundaries.
1. If a function has several meaningful steps, split them into helpers with one clear responsibility.
1. Run `pre-commit` on new files after each change.
1. Do not abbreviate variable names. Use `note`, not `n`.
1. Avoid hardcoded semantic values. Prefer `Final` constants, and move them to a shared module when the concept is reused.
1. Use `pathlib.Path` instead of `os.path`.
1. Prefer protocols over inheritance.
1. Separate function options with `*`. Positional arguments should be intentionally chosen.
1. Prefer `match` statements over long `isinstance` chains, and for enumeration handling.
1. Do not preserve backward compatibility for internal APIs, configs, or data shapes unless the user explicitly asks for it.
1. Avoid _tramp data_ antipattern.
1. Be cautious about optional parameters. All variables upon the logic relies on cannot be optional, including configuration instances.
1. Restrict yourself from using default values for non-optional, excluding these that are not meant to be frequently changed (e.g. seed). If you do use defaults, declare a Final top-level constant for that.
1. Be explicit about type expectations. Avoid dynamic `getattr` or `hasattr`.
1. Prefer computable properties over stored boolean variables. A boolean derived from existing state should be a `@property` (or `@computed_field` on a Pydantic model) rather than a field that must be kept in sync manually. Stored booleans create hidden state branches that are easy to leave inconsistent.

## Shared Ownership

1. Refer to `architecture-md` for project ownership rules.
1. General-purpose helpers that are not model-specific belong in shared/common modules, not inside feature modules.
1. Do not create delegated imports or re-export modules just so other modules can import through them.
1. Import shared helpers directly from the module that owns their implementation.
1. Before adding a helper, search the repository for existing logic with `rg`.
1. If new code duplicates existing logic, extract the shared rule first and make both call sites use it.
1. `__init__` must not expose anything outside it's tree hierarchy.
1. If new code duplicates existing logic, extract the shared rule first and make both call sites use it.
1. Do not overload with a single module with too many different responsibilities.
1. Prefer subpackages over flatten directory structure.

## Type Hints

1. Specify all input and return types in function signatures, including `None`.
1. Fill generic types. Use `Dict[str, int]`, not `Dict`.
1. Do not cast/silence type errors unless the boundary is an untyped or mistyped third-party API.
1. Avoid `Any` and `object` unless the boundary genuinely accepts arbitrary data.
1. Do not quote type names. Use `from __future__ import annotations` (only if needed), `Self`, or `TYPE_CHECKING`.
1. Prefer classic typehints: `Dict[...]` instead of `dict[...]`, `Optional[...]` over `... | None` etc.
1. Validate with `mypy`.

## Error Handling

1. Let failures crash unless the code can recover meaningfully.
1. Handle errors at the execution boundary when possible.
1. Do not add `try`/`except` blocks that only repackage failures without recovery.
1. Bare `except` and `except Exception` are forbidden.
1. Error handling blocks should cover only the code that is subject to a failure, unless there is a valid reason.


## Models

1. Prefer Pydantic models for validated or serialized data.
1. Use `frozen` when instances are not meant to change.
1. Dataclasses are acceptable for small internal state objects that are not serialized or validated, including test case dataclasses.

## Documentation

1. Documentation should explain the intention of a class/function and context of usage.
1. State functionality in positive terms. Describe what a class or function *does* — not what it avoids, omits, skips, differs from, or no longer does. Reframe every negation ("does not", "rather than", "instead of", "without", "never", "cannot", "no longer") into the behaviour that actually happens. Do not contrast with rejected alternatives as justification; the positive statement carries the meaning.
1. Negative phrasing is allowed only where the condition itself is the contract: exception triggers in `Raises:` clauses, precondition/postcondition bounds (prefer "must be at least X" over "cannot be less than X" where natural), and documented edge-case returns. Outside these concrete cases, negative descriptions are information noise and must be removed.
1. If a function does some decisions, logic should be explained with a justification for arbitrary choices, in docstrings, not code comments. Frame the justification positively (what the choice achieves), not as the failure it sidesteps.
1. Avoid comments and docstrings that restate code.
1. Use clear names instead of explanatory comments.
1. Avoid code comments. Comments are acceptable for tensor shapes, third-party API quirks, or non-obvious invariants.
1. Code comments and docstrings are not for documenting changes nor progress.

## Tests

1. Test files should mirror the ownership of the functionality under test.
1. When moving functionality between packages, move its direct unit tests in the same change.
1. Parametrize test functions of the same body and use test case dataclass.
1. Use test scenario suite class for defining more complex steps defined as series of functions with assertions.
1. Prefer fixtures over factories. Define shared fixtures in an appropriate place.
1. Do not assert default values of configurations, layouts, settings, and similar. Defaults are not contracts, and pinning them overconstrains the tests. Test behavior instead: validation bounds, serialization round-trips, and invariants. The exception is when values must match by contract rather than equal a chosen constant — e.g. project metadata at creation or after a save/load round-trip should be asserted to match, never hardcoded to a version string.
1. Unit tests may mock system boundaries (file I/O, external services, IPC channels), but must not mock the domain logic that is the subject of the test. Integration tests must exercise real computation pipelines against real (synthetically built) data.
1. When a test expectation diverges from the production code's actual behaviour, determine which is wrong before acting. A failing test is evidence of a potential bug in the production code unless the test itself is demonstrably incorrect (wrong imports, misread API contract, incorrect fixture). Never silently delete or weaken a test to make it pass. If uncertain, flag the divergence explicitly and ask before changing either side.
