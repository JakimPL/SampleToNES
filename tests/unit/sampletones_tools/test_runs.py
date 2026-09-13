from datetime import UTC, datetime
from pathlib import Path

from sampletones_tools.runs import RUN_STAMP, stamped_run_directory


class TestStampedRunDirectory:
    def test_a_run_lands_under_the_root_named_by_its_start(self, tmp_path: Path) -> None:
        before = datetime.now(UTC).replace(microsecond=0)

        directory = stamped_run_directory(tmp_path)

        started = datetime.strptime(directory.name, RUN_STAMP).replace(tzinfo=UTC)
        assert directory.parent == tmp_path
        assert before <= started <= datetime.now(UTC)
