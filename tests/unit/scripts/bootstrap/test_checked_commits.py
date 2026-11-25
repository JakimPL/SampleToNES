from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest

from bootstrap.checked_commits import (
    KEPT_TREES,
    checked_trees,
    clean_tree,
    commit_tree,
    is_checked,
    mark_checked,
)
from bootstrap.layout import CHECKED_TREES_RECORD
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.git import FIRST_FILE, ScratchRepository


def _edit(repository: ScratchRepository) -> None:
    repository.write(FIRST_FILE, "VALUE = 2\n")


def _stage(repository: ScratchRepository) -> None:
    _edit(repository)
    repository.git("add", FIRST_FILE)


def _add_untracked(repository: ScratchRepository) -> None:
    repository.write("untracked.py", "VALUE = 3\n")


class TestCleanTree(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        change: Callable[[ScratchRepository], None]

    test_cases = (
        TestCase(label="an_edited_file", change=_edit),
        TestCase(label="a_staged_file", change=_stage),
        TestCase(label="an_untracked_file", change=_add_untracked),
    )

    def test_a_work_tree_holding_the_commit_s_files_names_its_tree(self, repository: ScratchRepository) -> None:
        assert clean_tree(repository.root) == repository.git("rev-parse", "HEAD^{tree}")

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_work_tree_differing_from_the_commit_names_none(
        self,
        repository: ScratchRepository,
        test_case: TestCase,
    ) -> None:
        test_case.change(repository)

        assert clean_tree(repository.root) is None


class TestCommitTree:
    def test_a_commit_changing_no_file_holds_its_parent_s_tree(self, repository: ScratchRepository) -> None:
        parent = repository.git("rev-parse", "HEAD")

        empty = repository.commit("Recorded: nothing")

        assert commit_tree(repository.root, empty) == commit_tree(repository.root, parent)

    def test_an_annotated_tag_holds_the_tree_of_the_commit_it_names(self, repository: ScratchRepository) -> None:
        repository.git("tag", "--annotate", "v1.0.0", "--message", "Release")

        tag = repository.git("rev-parse", "v1.0.0")

        assert tag != repository.git("rev-parse", "HEAD")
        assert commit_tree(repository.root, tag) == commit_tree(repository.root, "HEAD")


class TestMarks:
    def test_a_repository_starts_with_no_marks(self, repository: ScratchRepository) -> None:
        assert checked_trees(repository.root) == []
        assert not is_checked(repository.root, "HEAD")

    def test_a_marked_tree_is_checked(self, repository: ScratchRepository) -> None:
        mark_checked(repository.root, commit_tree(repository.root, "HEAD"))

        assert is_checked(repository.root, "HEAD")

    def test_a_commit_changing_a_file_after_the_mark_is_unchecked(self, repository: ScratchRepository) -> None:
        mark_checked(repository.root, commit_tree(repository.root, "HEAD"))
        _edit(repository)

        changed = repository.commit("Changed: the value")

        assert not is_checked(repository.root, changed)

    def test_a_mark_made_in_one_worktree_serves_every_other(self, repository: ScratchRepository) -> None:
        linked = ScratchRepository(repository.root.parent / "linked")
        repository.git("worktree", "add", "--quiet", "--detach", str(linked.root))

        mark_checked(linked.root, commit_tree(linked.root, "HEAD"))

        assert is_checked(repository.root, "HEAD")

    def test_marking_a_tree_again_moves_it_to_the_newest_mark(self, repository: ScratchRepository) -> None:
        first = commit_tree(repository.root, "HEAD")
        mark_checked(repository.root, first)
        _edit(repository)
        second = commit_tree(repository.root, repository.commit("Changed: the value"))
        mark_checked(repository.root, second)

        mark_checked(repository.root, first)

        assert checked_trees(repository.root) == [second, first]

    def test_the_newest_marks_are_kept(self, repository: ScratchRepository) -> None:
        older = [f"{index:040x}" for index in range(KEPT_TREES)]
        common = Path(repository.git("rev-parse", "--path-format=absolute", "--git-common-dir"))
        (common / CHECKED_TREES_RECORD).write_text("\n".join(older) + "\n", encoding="utf-8")
        newest = commit_tree(repository.root, "HEAD")

        mark_checked(repository.root, newest)

        assert checked_trees(repository.root) == [*older[1:], newest]
