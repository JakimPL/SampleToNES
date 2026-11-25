from typing import Dict, Final, List

import pytest
import yaml

from bootstrap.checked_commits import commit_tree, mark_checked, short_commit
from bootstrap.layout import REPOSITORY_ROOT
from tests.suite.git import FIRST_FILE, ScratchRepository
from tests.suite.scripts import load_script

verify = load_script("verify_pushed_commit.py")

PRE_COMMIT_CONFIG: Final[str] = ".pre-commit-config.yaml"
SCRIPT: Final[str] = "scripts/verify_pushed_commit.py"
PRE_PUSH: Final[str] = "pre-push"


def _mark_head(repository: ScratchRepository) -> None:
    mark_checked(repository.root, commit_tree(repository.root, "HEAD"))


def _hooks_running_the_script() -> List[Dict[str, object]]:
    config = yaml.safe_load((REPOSITORY_ROOT / PRE_COMMIT_CONFIG).read_text(encoding="utf-8"))
    return [
        hook
        for repository in config["repos"]
        for hook in repository["hooks"]
        if str(hook.get("entry", "")).endswith(SCRIPT)
    ]


class TestPushFailure:
    def test_a_commit_the_check_passed_on_goes_through(self, repository: ScratchRepository) -> None:
        _mark_head(repository)

        assert verify.push_failure(repository.root, repository.git("rev-parse", "HEAD")) is None

    def test_a_commit_no_check_passed_on_is_held_back_with_what_to_run(self, repository: ScratchRepository) -> None:
        commit = repository.git("rev-parse", "HEAD")

        failure = verify.push_failure(repository.root, commit)

        assert failure == verify.UNCHECKED.format(commit=short_commit(repository.root, commit))
        assert "make check" in failure

    def test_a_commit_changing_a_file_after_the_mark_is_held_back(self, repository: ScratchRepository) -> None:
        _mark_head(repository)
        repository.write(FIRST_FILE, "VALUE = 2\n")

        changed = repository.commit("Changed: the value")

        assert verify.push_failure(repository.root, changed) is not None

    def test_a_reworded_commit_keeps_the_mark(self, repository: ScratchRepository) -> None:
        _mark_head(repository)

        repository.git("commit", "--amend", "--quiet", "--message", "Added: the first module")

        assert verify.push_failure(repository.root, repository.git("rev-parse", "HEAD")) is None

    def test_a_merge_bringing_the_checked_files_unchanged_keeps_the_mark(self, repository: ScratchRepository) -> None:
        repository.git("switch", "--quiet", "--create", "feature")
        repository.write("feature.py", "FEATURE = True\n")
        repository.commit("Added: a feature")
        _mark_head(repository)
        repository.git("switch", "--quiet", "-")

        repository.git("merge", "--no-ff", "--quiet", "--message", "Merged: the feature", "feature")

        assert len(repository.git("rev-list", "--parents", "--max-count=1", "HEAD").split()) == 3
        assert verify.push_failure(repository.root, repository.git("rev-parse", "HEAD")) is None

    def test_an_annotated_tag_on_a_checked_commit_goes_through(self, repository: ScratchRepository) -> None:
        _mark_head(repository)
        repository.git("tag", "--annotate", "v1.0.0", "--message", "Release")

        assert verify.push_failure(repository.root, repository.git("rev-parse", "v1.0.0")) is None

    def test_a_push_naming_no_commit_goes_through(self, repository: ScratchRepository) -> None:
        assert verify.push_failure(repository.root, None) is None


class TestTheHook:
    def test_the_pre_push_stage_runs_the_script_on_every_push(self) -> None:
        hooks = _hooks_running_the_script()

        assert len(hooks) == 1
        assert hooks[0]["stages"] == [PRE_PUSH]
        assert hooks[0]["always_run"] is True
        assert hooks[0]["pass_filenames"] is False

    def test_a_push_naming_no_commit_is_let_through(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(verify.PUSHED_COMMIT_VARIABLE, raising=False)

        assert verify.main([]) == 0
