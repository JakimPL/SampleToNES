# Packaging parity testing

One supported way to run SampleToNES is the PyInstaller executable produced by
`make build`. Today that path has no automated coverage: the unit and integration
suites exercise the Python package, and the binary is trusted to behave the same by
inspection. This document is the methodology for closing that gap — for proving, on
every supported operating system, that the frozen `sampletones` executable behaves
identically to `python -m sampletones`.

The maintainer's question, stated plainly:

> One way to use my application is through a PyInstaller executable. I have no tests
> for these. How do I make sure the built application behaves the same as the Python
> package, regardless of OS?

The answer here is a **layered parity harness**: four tiers of checks that grow from a
one-line version diff to a headless GUI boot, each cheap enough to run in CI on Linux,
Windows, and macOS. The design is prescriptive and phased; it recommends three concrete
production additions (a `--self-check` verb, a reviewable `sampletones.spec`, and a
`tests/packaging/` suite) and a three-OS CI matrix, and it grounds every risk in the
code that ships today.

Companion documents: `docs/releasing.md` owns the release orchestration and the
version single-source-of-truth work this document leans on; `docs/testing.md` owns the
declarative action-based scenario framework whose parity role Tier 3 describes. Coding
rules are in `docs/guidelines.md`; the application layering is in `docs/architecture.md`.

---

## What ships today

The build is a PyInstaller `--onefile` bundle. The Linux recipe
(`scripts/linux/build/build.sh`) and its Windows twin (`scripts/windows/build/build.bat`)
pass the same flags, diverging only where the platform forces it:

```bash
pyinstaller --name sampletones \
    --onefile \
    --distpath . \
    --icon "src/sampletones_assets/icons/sampletones.png" \
    --add-data "src/sampletones_assets/icons:assets/icons" \
    --add-data "src/sampletones_assets/fonts:assets/fonts" \
    --add-data "src/sampletones_config:config" \
    "src/sampletones/__main__.py"
```

The three `--add-data` mounts define the contract the binary must honour at runtime:

| Source tree | Bundle target | Holds |
| --- | --- | --- |
| `src/sampletones_assets/icons` | `assets/icons` | `sampletones.png`, `sampletones.ico`, window icons |
| `src/sampletones_assets/fonts` | `assets/fonts` | `RobotoMono-*.ttf`, `DejaVuSans.ttf` (`FONT_ICON`) |
| `src/sampletones_config` | `config` | `behavior/`, `layout/`, `lang/`, `theme/`, `calibration/` |

Platform divergences already present, and the ones a parity harness must account for:

- **Data-mount separator.** Linux/macOS use `:` (`icons:assets/icons`); Windows uses `;`
  (`icons;assets\icons`). A single-string `--add-data` recipe is therefore not portable,
  which is one reason this document recommends a `sampletones.spec` (below), where
  `datas` is a list of tuples and the separator problem disappears.
- **Icon format.** Linux points `--icon` at `sampletones.png`; Windows points it at
  `sampletones.ico`.
- **No macOS build.** There is no `scripts/macos/build/build.sh`. macOS parity coverage
  requires adding one; the Linux recipe transfers directly because macOS also uses the
  `:` separator.

`install.sh` / `install.bat` orchestrate the chain (python check → isolated `.venv-build` →
package install → build) into a dedicated build virtual environment that leaves the invoking
Python untouched. `make build` runs `install.(sh|bat)` (respecting the current
`deployment.yaml`); `make release` adds `--release` to inject the release deployment config;
`make system-deps` installs the OS packages separately. The produced artifact is `sampletones`
on POSIX and `sampletones.exe` on Windows, dropped at the repository root (`--distpath .`).

### Frozen-mode path resolution: the finding

The single largest parity risk for any `--onefile` bundle is resolving bundled data:
under `--onefile` the mounts live in a temporary extraction directory exposed as
`sys._MEIPASS`, **not** next to the source tree. Code that computes paths from
`__file__` or a relative source layout works as a package and breaks as a binary.

SampleToNES **already resolves both mounts in frozen mode**, in two independent places:

1. **Config** — `src/sampletones_application/paths.py` keys directly on the frozen marker:

   ```python
   _MEIPASS = getattr(sys, "_MEIPASS", None)
   CONFIG_DIRECTORY: Final[Path] = (
       Path(_MEIPASS) / "config" if _MEIPASS is not None
       else Path(_config_pkg.__file__).parent
   )
   ```

   So `BEHAVIOR_DIRECTORY`, `LAYOUT_DIRECTORY`, `LANG_DIRECTORY`, `THEME_DIRECTORY`, and
   `DEPLOYMENT_CONFIG_PATH` all rebase onto `sys._MEIPASS/config` inside the binary.

2. **Assets** — `src/sampletones_application/ui/resources/loader.py` keys on the frozen
   flag and rebases onto `sys._MEIPASS/assets/<type>`:

   ```python
   def _get_package_path(self, resource_name: str) -> Union[Path, Traversable]:
       if getattr(sys, "frozen", False):
           base_path = Path(sys._MEIPASS)
           resource_type = self.resource_directory.name
           return base_path / "assets" / resource_type / resource_name
       package_name = f"sampletones_assets.{self.resource_directory.name}"
       return files(package_name).joinpath(resource_name)
   ```

This is good news: the design is sound, and both mounts have a frozen branch. The gap is
**verification**, not correctness — and there are three specifics a test harness must pin:

- **The frozen branch is dead code in the current suite.** No test sets `sys.frozen` /
  `sys._MEIPASS`, so nothing exercises the `_MEIPASS is not None` path of `paths.py` or
  the `getattr(sys, "frozen", False)` path of `loader.py`. A refactor could silently
  regress either branch and every test would stay green. The harness must run *the actual
  binary*, because that is the only place these branches execute.
- **The two resolvers use different frozen-detection idioms.** `paths.py` treats "has
  `_MEIPASS`" as the signal; `loader.py` treats "has `frozen`" as the signal and then
  reads `_MEIPASS`. A PyInstaller `--onefile` bundle sets both, so both hold today. The
  divergence is a latent inconsistency worth unifying (a shared `is_frozen()` /
  `frozen_base()` helper) so a future non-PyInstaller freezer, or a change to one idiom,
  cannot desynchronise them.
- **`src/sampletones_core/paths.py` performs filesystem work at import time.** Its final
  lines `mkdir(parents=True, exist_ok=True)` the user `Documents` subtrees. That side
  effect fires the moment the module imports, frozen or not, so a clean `--self-check`
  import doubles as a check that startup does not fail on a read-only or unusual home
  directory. `ASSETS_DIRECTORY = "assets"` in the same module is only a directory *name*
  consumed by `ResourceLoader`, so it needs no frozen branch.

### The bundled-config release concern

`src/sampletones_config/behavior/deployment.yaml` — mounted into the binary at
`config/behavior/deployment.yaml` — currently ships:

```yaml
log_level: DEBUG
strict_history: true
```

Both values are baked into every executable produced from this tree. `log_level: DEBUG`
gives end users verbose developer logging, and `strict_history: true` makes
`DeploymentConfig` raise `UntrackedMutationError` on any untracked domain mutation —
developer-facing strictness that turns a self-healing situation into a crash in a
shipped binary. A release build wants `INFO` (or higher) and `strict_history: false`.
`docs/releasing.md` owns the decision of *which* `deployment.yaml` a release bundles;
this document contributes the **test** that pins it: Tier 1 loads the bundled
`DeploymentConfig` from inside the binary and asserts its values match the release
profile, so a debug config can never ship unnoticed.

---

## Parity risk taxonomy

Why a frozen binary diverges from `pip install`, what the divergence looks like, and
which tier catches it. This table is the map the rest of the document fills in.

| # | Risk | Symptom in the binary | How a test catches it |
| --- | --- | --- | --- |
| R1 | Bundled-data path resolution (`sys._MEIPASS`, frozen detection) — the finding above | `FileNotFoundError` on config, font, or icon; blank window; startup abort | Tier 1 `--self-check` resolves and loads every mount from inside the binary; Tier 2 boots the real GUI |
| R2 | Missing hidden imports (dynamically imported modules: `librosa`/`numba`, `soundfile` backends, `lazy_loader` targets, `pyaudio`) | `ModuleNotFoundError` / `ImportError` at startup or first use, absent from the package run | Tier 0 `--version` / `--help` fail to import; Tier 0.5 `--generate` and a reconstruction exercise the core stack |
| R3 | Missing data files for bundled libraries (`numba` runtime, `scipy` data, `librosa` example data) | Import succeeds but a lib raises at call time (`FileNotFoundError` deep in a dependency) | Tier 0.5 runs a real reconstruction through librosa/scipy/numba and diffs the artifact against the package |
| R4a | Native library not collected (`pyaudio` → PortAudio, `soundfile` → libsndfile, `dearpygui` native) | `OSError`/`ImportError` naming a missing `.so`/`.dll`/`.dylib` | Tier 1 imports the audio stack; Tier 2 boots DPG |
| R4b | OS packaging differences (`:` vs `;` data separator, DLL/dylib/.so layout, macOS Gatekeeper/code signing, Windows antivirus quarantine) | Build differs per OS, or binary refuses to launch on a clean machine | Full three-OS CI matrix builds and smoke-tests on each runner |
| R5 | Debug `deployment.yaml` bundled into a release build | Verbose DEBUG logs and `strict_history` crashes in the field | Tier 1 loads the bundled `DeploymentConfig` and asserts the release profile |
| R6 | GUI needs a display; CI runners are headless | GUI tier hangs or aborts with "no display" | Tier 2 runs the binary under `xvfb-run` on Linux; documented limits on Windows/macOS |
| R7 | Version drift between the two declaration sites | `--version` disagrees with `importlib.metadata.version("sampletones")` or the git tag | Version-stamping test (below) diffs all three |
| R8 | `multiprocessing` under a frozen binary | Worker processes relaunch the whole app (fork bomb) or fail to start | `multiprocessing.freeze_support()` is already the first line of `__main__`; Tier 0.5 `--generate` drives the `pebble` pool and confirms it |

---

## The layered test strategy

Four tiers, ordered by cost and by how much of the stack they light up. Each tier is a
strict superset of the confidence of the one before it, and each is cheap enough to run
on all three OSes — except where a tier's per-OS feasibility is called out explicitly.

| Tier | What it runs | Catches | Per-OS feasibility |
| --- | --- | --- | --- |
| 0 | Binary `--version` / `--help`, diffed against the package | R2, R7, gross collection failure | All three OSes |
| 0.5 | Binary `--generate` and a small reconstruction, artifact diffed against the package | R2, R3, R4a, R8 | All three OSes (headless; no display) |
| 1 | Binary `--self-check`: resolve + load every mount, load `DeploymentConfig` | R1, R4a, R5 | All three OSes |
| 2 | Boot the real frozen GUI headlessly | R1, R4a, R6 | Linux via `xvfb-run`; Windows partial; macOS limited |
| 3 | Declarative behavioural scenarios, package vs. binary subset | End-to-end parity of CLI-observable behaviour | Scenario-dependent |

The organising idea across all tiers: **"same behaviour as the package" is made literal**
by running the *same* invocation through both `python -m sampletones` and the built
executable and asserting their observable outputs are equal.

### Tier 0 — headless CLI smoke, diffed against the package

The cheapest and most portable check. `src/sampletones/__main__.py` exposes a small CLI
that runs without opening a window; the GUI-free flags are the ideal smoke test because
they force PyInstaller's import graph to resolve without needing a display.

Catalogue of CLI flags (from `__main__.py`), annotated for parity value:

| Flag | Behaviour | Parity value |
| --- | --- | --- |
| `--version` / `-v` | Prints `SAMPLETONES_NAME_VERSION` (`"SampleToNES v0.2.4"`) and exits | Cheapest smoke; also the version-stamp probe (R7) |
| `--help` / `-h` | Custom (`add_help=False`); prints `parser.print_help()` and exits | Cheap smoke; imports argparse graph only |
| `--generate` / `-g` | Generates library data through the core stack; no GUI | Tier 0.5 — exercises `librosa`/`numba`/`scipy` and `pebble` workers |
| positional `path` | Reconstructs an audio file/dir, or loads `.stn`/`.ins`/`.stp` | Tier 0.5 — real audio pipeline |
| `--output` / `-o`, `--config` / `-c` | Output path and config-file overrides for the above | Feed the Tier 0.5 reconstruction |

A Tier 0 test shells out to both runners for each GUI-free flag and asserts equal exit
code and equal stdout. Sketch (`tests/packaging/test_cli_parity.py`):

```python
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
BINARY_ENV_VAR: str = "SAMPLETONES_BINARY"
BINARY_NAME: str = "sampletones.exe" if sys.platform == "win32" else "sampletones"


def _locate_binary() -> Optional[Path]:
    override = os.environ.get(BINARY_ENV_VAR)
    candidate = Path(override) if override else REPO_ROOT / BINARY_NAME
    return candidate if candidate.is_file() else None


@pytest.fixture(scope="session")
def binary_path() -> Path:
    located = _locate_binary()
    if located is None:
        pytest.skip(f"Built binary not found; set {BINARY_ENV_VAR} or run 'make build'")

    return located


def _run(command: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)


@dataclass(frozen=True)
class CliCase:
    label: str
    flags: List[str]


CLI_CASES: List[CliCase] = [
    CliCase(label="version", flags=["--version"]),
    CliCase(label="help", flags=["--help"]),
]


@pytest.mark.parametrize("case", CLI_CASES, ids=lambda case: case.label)
def test_binary_matches_package(case: CliCase, binary_path: Path) -> None:
    package = _run([sys.executable, "-m", "sampletones", *case.flags])
    binary = _run([str(binary_path), *case.flags])

    assert binary.returncode == package.returncode == 0
    assert binary.stdout == package.stdout
```

The `binary_path` fixture skips when no artifact is present, so the file is inert during
ordinary `make test` and only asserts when a build exists (locally after `make build`, or
always in the CI matrix). This is the "guarded to run only when a built binary is present"
rule that governs the whole `tests/packaging/` suite.

### Tier 0.5 — real work through the core stack

`--version` and `--help` prove the interpreter and argparse graph resolve, but they never
touch `librosa`, `numba`, `soundfile`, `scipy`, or the `pebble` process pool — exactly the
dependencies most likely to be mis-collected (R2, R3, R4a) or to misbehave under a frozen
`multiprocessing` model (R8). Tier 0.5 drives a small unit of real work through both
runners and diffs the produced artifact:

- Feed a short synthetic `.wav` fixture (a few hundred milliseconds; the integration
  suite already builds synthetic audio) to `sampletones <input.wav> --output <out>` and to
  `python -m sampletones <input.wav> --output <out>`, then assert the two output files are
  byte-identical (or equal after a tolerant numeric compare where floats are involved).
- Optionally run `--generate` under both to confirm library generation — and with it the
  `pebble` worker pool — completes in the frozen process. Because
  `multiprocessing.freeze_support()` is already the first statement under
  `if __name__ == "__main__"`, workers relaunch correctly instead of re-running `main()`;
  Tier 0.5 is what proves that guard holds in the bundle.

Tier 0.5 needs no display, so it runs on every OS in the matrix. Keep the input tiny to
keep CI wall-clock low — the goal is *collection and execution parity*, not throughput.

### Tier 1 — bundled-resource self-check

Tier 0 proves imports resolve; it does not prove the *data mounts* resolve, because
`--version` reads a constant and never touches `sys._MEIPASS`. Tier 1 closes R1, R4a, and
R5 directly by exercising path resolution from inside the binary.

**Recommendation (highest-value addition): add a hidden `--self-check` verb to
`__main__.py`.** It turns "did the bundle work" into a one-line, GUI-free, cross-OS CI
assertion. It resolves every `--add-data` target through the *same* code the app uses,
loads the bundled `DeploymentConfig`, and returns a nonzero exit code on the first
failure. Sketch of the verb (production code — typed, pathlib, positive framing, no bare
except, matching `docs/guidelines.md`):

```python
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

SELF_CHECK_OK: int = 0
SELF_CHECK_FAILED: int = 1


@dataclass(frozen=True)
class SelfCheckResult:
    label: str
    detail: str
    passed: bool


def run_self_check() -> int:
    from sampletones_application.config.deployment.deployment import DeploymentConfig
    from sampletones_application.paths import (
        CONFIG_DIRECTORY,
        DEPLOYMENT_CONFIG_PATH,
        LANG_EN,
    )
    from sampletones_application.ui.resources.loader import ResourceLoader
    from sampletones_core.paths import (
        FONT_ICON,
        FONT_MAIN,
        ICON_UNIX_FILENAME,
    )

    results: List[SelfCheckResult] = []

    frozen = bool(getattr(sys, "frozen", False))
    results.append(SelfCheckResult("frozen", f"frozen={frozen}", True))

    config_ok = CONFIG_DIRECTORY.is_dir() and DEPLOYMENT_CONFIG_PATH.is_file()
    results.append(SelfCheckResult("config", str(CONFIG_DIRECTORY), config_ok))

    lang_ok = LANG_EN.is_file()
    results.append(SelfCheckResult("lang", str(LANG_EN), lang_ok))

    deployment = DeploymentConfig.load(DEPLOYMENT_CONFIG_PATH)
    results.append(SelfCheckResult("deployment", f"log_level={deployment.log_level}", True))

    fonts = ResourceLoader(Path("fonts"))
    font_ok = Path(fonts.get_path(FONT_MAIN)).is_file() and Path(fonts.get_path(FONT_ICON)).is_file()
    results.append(SelfCheckResult("fonts", FONT_MAIN, font_ok))

    icons = ResourceLoader(Path("icons"))
    icon_ok = Path(icons.get_path(ICON_UNIX_FILENAME)).is_file()
    results.append(SelfCheckResult("icons", ICON_UNIX_FILENAME, icon_ok))

    for result in results:
        marker = "PASS" if result.passed else "FAIL"
        print(f"[{marker}] {result.label}: {result.detail}")

    return SELF_CHECK_OK if all(result.passed for result in results) else SELF_CHECK_FAILED
```

Wired into `main()` alongside the existing flags, guarded like `--version`:

```python
if args.self_check:
    raise SystemExit(run_self_check())
```

`ResourceLoader.get_path` already raises `FileNotFoundError` when a resource is missing, so
the verb surfaces a broken mount with a precise path rather than a blank window. Because it
loads `DeploymentConfig`, the same run also carries the shipped `log_level` and
`strict_history` in its output — the Tier 1 test asserts they equal the release profile,
which is how R5 (a debug config shipping unnoticed) gets caught mechanically.

The Tier 1 test is then trivial:

```python
def test_self_check_passes(binary_path: Path) -> None:
    result = _run([str(binary_path), "--self-check"])

    assert result.returncode == 0
    assert "log_level=INFO" in result.stdout  # release profile; see docs/releasing.md
```

Until the verb lands, a weaker Tier 1 is still possible against the *package* by
monkeypatching `sys.frozen` / `sys._MEIPASS` to point at a staged directory laid out like
the bundle and asserting `paths.py` and `ResourceLoader` rebase correctly. That exercises
the frozen branches in-process, but it does not prove the real bundle contains the files —
only the binary can. Treat the monkeypatched variant as a fast pre-flight and the
`--self-check` run as the authority.

### Tier 2 — GUI boot in headless mode

The package already proves the GUI graph constructs headlessly:
`tests/unit/sampletones_application/test_startup.py` boots a real `Application()` with the
DPG display functions (`create_context`, `create_viewport`, `show_viewport`,
`render_dearpygui_frame`, and the viewport setters) patched to no-ops, so construction and
wiring run without a window. That test guards the *package* graph.

Tier 2 asks the harder question: does the *frozen* GUI initialise, with DPG's native
library collected and every panel's font and icon resolving from `sys._MEIPASS`? The DPG
functions cannot be monkeypatched inside a separate binary process, so the honest approach
is a real display provided by a virtual framebuffer:

- **Linux** — run the binary under `xvfb-run`, which starts an in-memory X server. Give
  the app a way to boot, render a frame or two, and exit cleanly (a `--smoke-boot` flag
  that constructs `Application`, pumps a fixed number of frames, and quits; or reuse
  `--self-check` extended to instantiate the shell). Assert exit code 0.

  ```bash
  xvfb-run --auto-servernum --server-args="-screen 0 1280x1024x24" \
      ./sampletones --self-check
  ```

- **Windows** — `windows-latest` GitHub runners provide a desktop session, so a short-lived
  real GUI boot can work without a framebuffer, but it is flakier (window focus, driver
  quirks). Keep Tier 2 on Windows to a bounded boot-and-quit with a hard timeout, and
  treat Tier 0/0.5/1 as the load-bearing Windows coverage.

- **macOS** — headless GUI on `macos-latest` runners is the least reliable (no framebuffer
  equivalent as clean as Xvfb; windowserver access from CI is constrained). Be honest: on
  macOS, rely on Tier 0/0.5/1 for parity and treat a full GUI boot as a manual or
  best-effort step rather than a required gate.

A dedicated `--smoke-boot` verb is preferable to driving the real event loop, because it
bounds the run deterministically and needs no synthetic input events. It reuses the exact
startup path `run.py` → `Application()` → `run()` and simply requests an early, clean exit.

### Tier 3 — behavioural parity via declarative scenarios

`docs/testing.md` (companion) describes the declarative, action-based scenario framework;
it lives today in `tests/suite/` as `BaseTestScenario` / `ScenarioStep` (an ordered
sequence of named `action(context)` steps over one mutable context) and
`BaseTestSuite` / `BaseTestCase` (parametrised input/output cases). These scenarios drive
domain objects and `Application` **in-process**, which is exactly why they cannot steer a
separate frozen binary directly: there is no in-process handle to the executable's objects.

The realistic parity role for Tier 3 is therefore narrower than "run every scenario twice":

- **CLI-observable scenarios run against both runners.** Any scenario whose entire
  observable effect is a file the CLI produces (reconstruct this audio → this `.stn`;
  load this `.stn` and export → this `.ftm`) can execute against `python -m sampletones`
  and against the binary, with the produced artifacts diffed. These are the scenarios that
  genuinely prove *end-to-end* parity, and they are a superset of Tier 0.5.
- **In-process scenarios stay package-only.** Scenarios that assert on intermediate view
  models, callback ordering, or undo-history state have no CLI surface and cannot drive the
  binary. They remain valuable package coverage; they are simply out of scope for the
  binary, and the harness should not pretend otherwise.

Concretely: factor the CLI-observable scenarios so their inputs and expected artifacts are
data (paths + expected output files), then parametrise a Tier 3 test that runs each through
both runners and compares artifacts. The scenario *definitions* are shared; only the
*driver* differs (in-process call vs. `subprocess`). This keeps a single source of truth
for "what correct behaviour is" and lets the binary be measured against it.

---

## Recommended production additions

Three additions make the strategy above concrete and reviewable. All are design
recommendations; none changes existing behaviour.

### 1. A `sampletones.spec` PyInstaller spec

The inline CLI recipe has three weaknesses: it is not reviewable as data, it duplicates the
`:` / `;` separator problem across two scripts, and it offers no place to declare the
hidden imports and data files the native dependencies need. A checked-in
`sampletones.spec` fixes all three. It makes `datas` a portable list of tuples (PyInstaller
handles the separator per OS), and it declares the collection directives the risk taxonomy
predicts:

```python
# sampletones.spec — reviewable, portable build definition
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

datas = [
    ("src/sampletones_assets/icons", "assets/icons"),
    ("src/sampletones_assets/fonts", "assets/fonts"),
    ("src/sampletones_config", "config"),
]
hiddenimports: list[str] = []

for package in ("librosa", "numba", "llvmlite", "soundfile"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    hiddenimports += package_hidden

hiddenimports += collect_submodules("lazy_loader")
datas += collect_data_files("scipy")

a = Analysis(
    ["src/sampletones/__main__.py"],
    pathex=["src"],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["cupy"],  # optional GPU stack stays out of the default bundle
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="sampletones", onefile=True)
```

Notes tying the spec to the dependency stack (`pyproject.toml`):

- **`librosa` 0.11 → `numba` / `llvmlite`, `soundfile`, `audioread`, `lazy_loader`,
  `pooch`.** `numba`/`llvmlite` are the classic PyInstaller pitfall (JIT runtime plus data
  files); `librosa` uses `lazy_loader`, whose deferred imports PyInstaller cannot see
  statically, hence `collect_submodules`. `soundfile` needs its bundled `libsndfile`
  native library — `collect_all` pulls the binaries. These are the R2/R3/R4a hot spots.
- **`pyaudio` 0.2.14 → PortAudio.** The wheel carries a native library that must be
  collected; a missing PortAudio is a runtime `OSError`, so Tier 1's audio import catches
  it. Modern PyInstaller hooks usually cover it, but the spec is where an explicit
  `--collect-binaries pyaudio` lives if a runner needs it.
- **`dearpygui` 2.3.1** ships a native library that PyInstaller's hook collects; Tier 2's
  boot is the proof it loads.
- **`numpy` / `scipy` / `pydantic` (pydantic-core) / `msgpack`** are compiled but covered
  by standard hooks; `scipy` occasionally needs `collect_data_files`, included above as
  cheap insurance.
- **`pebble` + `multiprocessing`** rely on `multiprocessing.freeze_support()`, already
  present in `__main__.py`. No spec change; Tier 0.5 confirms it.
- **Windows-only `pywin32` / `pytaskbar`** need the pywin32 hook (`pythoncom`,
  `pywintypes` DLLs). Because they are `platform_system == 'Windows'` dependencies, the
  spec's collection should be guarded by platform so the Linux/macOS builds do not try to
  collect them.
- **`cupy` (GPU extra)** is excluded from the default bundle: it is large and drags the
  CUDA runtime. A separate GPU spec variant can include it if a GPU binary is ever shipped.

Both `build.sh` and `build.bat` then reduce to `pyinstaller sampletones.spec`, and the two
scripts stop diverging except for the icon format.

### 2. The `--self-check` (and `--smoke-boot`) verbs

Detailed under Tier 1 and Tier 2. `--self-check` is the single highest-value addition: it
converts the entire bundled-data risk class (R1, R4a, R5) into a one-line CI assertion that
runs identically on every OS. `--smoke-boot` extends the idea to the GUI for Tier 2.

### 3. A `tests/packaging/` suite

A new top-level test package, mirroring the existing `tests/unit`, `tests/integration`,
`tests/suite` layout (`docs/guidelines.md`: test files mirror the functionality they
cover; cross-cutting suites sit at the top level):

```
tests/packaging/
├── conftest.py            ← binary_path fixture + audio fixtures, skip when no build
├── test_cli_parity.py     ← Tier 0: --version / --help diffed against the package
├── test_reconstruction_parity.py  ← Tier 0.5: artifact diff on a synthetic .wav
├── test_self_check.py     ← Tier 1: --self-check exit code + release profile assertion
├── test_gui_boot.py       ← Tier 2: --smoke-boot under xvfb (Linux-gated)
└── test_version_stamp.py  ← R7: --version vs importlib.metadata vs tag
```

Every test here is gated on the `binary_path` fixture, so the suite is a no-op during
ordinary `make test` and becomes assertive the moment a build exists. It is excluded from
the coverage `fail_under` gate (it measures the binary, not source-line coverage).

---

## Reproducibility and version stamping

The binary must report the same version as the package, and both must match the release
tag. The version is currently declared in **two** places:

- `SAMPLETONES_VERSION = "0.2.4"` in `src/sampletones_shared/constants/application.py`
  (what `--version` prints, via `SAMPLETONES_NAME_VERSION`);
- `version = "0.2.4"` in `pyproject.toml` (what the wheel metadata carries, read by
  `importlib.metadata.version("sampletones")`).

Two declarations can drift. `docs/releasing.md` owns collapsing them to a single source of
truth; this document contributes the test that makes drift fatal (R7):

```python
from __future__ import annotations

import subprocess
from importlib.metadata import version
from pathlib import Path


def test_binary_version_matches_metadata(binary_path: Path) -> None:
    package_metadata = version("sampletones")
    result = subprocess.run(
        [str(binary_path), "--version"], capture_output=True, text=True, check=True
    )

    assert package_metadata in result.stdout.strip()
```

At release time the same value is compared to the git tag (the CI matrix passes the tag in
and asserts `--version` contains it), so the tag, the wheel metadata, and the frozen
string are proven equal in one place. Note that `importlib.metadata` reads installed
distribution metadata, so this assertion runs where the package is installed; for the
binary-only leg, the matrix compares the binary's `--version` string to the package's
`--version` string (both read the constant) and separately to the tag.

For reproducibility beyond the version string: the `sampletones.spec` (pinned alongside the
already-pinned dependency set in `pyproject.toml`) is what makes two builds of the same
commit produce the same bundle contents, which is the precondition for any of these parity
diffs to be meaningful across runners.

---

## CI matrix

Parity is only proven when the binary is built and smoke-tested on each supported OS, on a
clean machine, from the same commit. The proposal is a GitHub Actions workflow (there is no
`.github/workflows/` directory yet, so this is greenfield; `docs/releasing.md` owns how it
ties into tagging and artifact publication) that builds on `ubuntu-latest`,
`windows-latest`, and `macos-latest` and runs Tier 0 + Tier 0.5 + Tier 1 on each, plus
Tier 2 under `xvfb` on Linux, uploading each artifact.

```yaml
name: build-and-parity

on:
  push:
    tags: ["v*"]
  workflow_dispatch:

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install package and PyInstaller
        run: |
          python -m pip install --upgrade pip
          pip install .
          pip install pyinstaller

      - name: Build binary
        run: pyinstaller sampletones.spec

      - name: Tier 0 + 0.5 + 1 (headless smoke, all OSes)
        env:
          SAMPLETONES_BINARY: ${{ github.workspace }}/dist/sampletones
        run: pip install pytest && pytest tests/packaging -m "not gui"

      - name: Tier 2 GUI boot under Xvfb (Linux only)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update && sudo apt-get install -y xvfb
          xvfb-run --auto-servernum --server-args="-screen 0 1280x1024x24" \
            pytest tests/packaging -m gui
        env:
          SAMPLETONES_BINARY: ${{ github.workspace }}/dist/sampletones

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: sampletones-${{ matrix.os }}
          path: |
            sampletones
            sampletones.exe
```

Matrix notes:

- **The `xvfb` step is Linux-only** and gated by a `gui` pytest marker, so Windows and
  macOS jobs run only the display-free tiers. This matches the honest Tier 2 feasibility:
  Xvfb gives Linux a reliable headless display; Windows runners have a real session but are
  flakier; macOS headless GUI is the least reliable and stays out of the required gates.
- **macOS needs a build script.** Add `scripts/macos/build/build.sh` mirroring the Linux
  recipe — the `:` separator transfers directly — or, better, have all three OSes call
  `pyinstaller sampletones.spec` so there is one build definition. macOS additionally
  raises Gatekeeper/code-signing and `.app` bundling questions for a *distributable*
  binary; for *parity testing* an unsigned CLI-style executable run on the runner is
  sufficient, and signing is a release concern for `docs/releasing.md`.
- **Windows antivirus / SmartScreen** can quarantine an unsigned freshly built `.exe`. On
  the GitHub runner this is usually a non-issue, but it is a real end-user divergence worth
  a note in the release document.
- **`fail-fast: false`** keeps one OS's failure from masking the others — the whole point is
  to see which platform diverged.

---

## Phased rollout

Following the project's phased-refactor practice (`docs/guidelines.md`; each phase lands
and is independently verifiable):

**Phase 1 — local parity floor.** Add the `--self-check` verb to `__main__.py` and create
`tests/packaging/` with Tier 0 (`--version` / `--help` diff), Tier 0.5 (synthetic-`.wav`
artifact diff), and Tier 1 (`--self-check` exit code + release-profile assertion). Verify
by running `make build` locally, then `SAMPLETONES_BINARY=./sampletones pytest
tests/packaging`. Deliverable: a developer can prove binary/package parity on their own OS
in one command. This phase also *finds* any frozen-path bug the current suite hides.

**Phase 2 — reviewable, correct builds.** Add `sampletones.spec` with the `datas`,
`hiddenimports`, and `collect_all` directives above; repoint `build.sh` / `build.bat` (and
a new macOS build) at it; fix any frozen-path or collection bug Phase 1 surfaced; unify the
two frozen-detection idioms behind one helper; and settle the release `deployment.yaml`
profile with `docs/releasing.md`. Verify by rebuilding via the spec on the local OS and
re-running the Phase 1 suite green. Deliverable: one portable build definition, and the
debug-config-shipping risk (R5) closed by test.

**Phase 3 — three-OS gate.** Add the GitHub Actions matrix building on Linux, Windows, and
macOS; run Tier 0/0.5/1 everywhere and Tier 2 under `xvfb` on Linux; add the
version-stamping test (R7) wired to the tag; upload artifacts. Add `--smoke-boot` for
Tier 2. Verify by pushing a tag and watching all three legs pass. Deliverable: every
release proves, mechanically and per-OS, that the frozen `sampletones` behaves like
`python -m sampletones`.
