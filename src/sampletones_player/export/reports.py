from sampletones_core.exports.progress import ExportProgress, ExportReporter
from sampletones_core.exports.stage import ExportStage
from sampletones_core.performance import WalkProgress, WalkReporter
from sampletones_player.compression.progress.report import CodecProgress, CodecReporter

UNMEASURED: None = None


def walk_reporter(report: ExportReporter) -> WalkReporter:
    """The walk's own reckoning, said in the words an export reports itself in.

    A song's order states the ticks it lasts before a row of it is played, so this stage travels
    toward a length it knows and reads as a true fraction of the song.

    Args:
        report: Hears each stage of the export, and answers whether it goes on.

    Returns:
        WalkReporter: What playing the song out tells the export about itself.
    """

    def reached(progress: WalkProgress) -> bool:
        return report(
            ExportProgress(
                stage=ExportStage.WALKING,
                completed=progress.ticks,
                total=progress.total,
            )
        )

    return reached


def codec_reporter(report: ExportReporter) -> CodecReporter:
    """The codec's own reckoning, said in the words an export reports itself in.

    A codec run ends when no further phrase pays for itself, which the song decides, so what it
    offers is the bytes it has laid down so far, measured against no length of its own.

    Args:
        report: Hears each stage of the export, and answers whether it goes on.

    Returns:
        CodecReporter: What the compression tells the export about itself.
    """

    def reached(progress: CodecProgress) -> bool:
        return report(
            ExportProgress(
                stage=ExportStage.COMPRESSING,
                completed=progress.size,
                total=UNMEASURED,
            )
        )

    return reached
