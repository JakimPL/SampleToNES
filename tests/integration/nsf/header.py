from sampletones_player.nsf.information import NSFInformation
from sampletones_tools.corpus.module import ModuleConfig
from sampletones_tools.samples.nsf import exported_information


def sample_information(name: str) -> NSFInformation:
    """The header text ``nsf samples`` gives a corpus sample: its name, by the corpus's author."""
    return exported_information(name, ModuleConfig.load().author)
