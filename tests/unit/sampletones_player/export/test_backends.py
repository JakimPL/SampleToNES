from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.scope import ExportScope
from sampletones_player.export.backends import program_backends
from sampletones_player.nsf.header import HEADER_TEXT
from sampletones_shared.paths.extensions import EXT_FILE_NSF


class TestProgramBackends:
    """The backends writing console programs, as the application composes them."""

    def test_every_backend_is_keyed_by_the_format_it_writes(self) -> None:
        for export_format, backend in program_backends().items():
            assert backend.export_format == export_format

    def test_every_backend_stands_where_the_export_seam_expects_one(self) -> None:
        for backend in program_backends().values():
            seam: ExportBackend = backend
            assert seam.supported_scopes == frozenset(ExportScope)

    def test_the_nsf_backend_writes_nsf_files_under_header_text(self) -> None:
        backend = program_backends()[ExportFormat.NSF]
        assert (backend.extension(ExportScope.PROJECT), backend.text) == (EXT_FILE_NSF, HEADER_TEXT)
