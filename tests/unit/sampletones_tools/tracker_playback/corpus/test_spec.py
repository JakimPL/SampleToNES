from sampletones_tools.tracker_playback.corpus.spec import CorpusSpec


class TestCorpusSpec:
    def test_the_shipped_corpus_loads_from_the_package(self) -> None:
        corpus = CorpusSpec.load()

        assert corpus.projects
        assert corpus.arrangements

    def test_every_project_and_arrangement_writes_its_files_under_a_name_of_its_own(self) -> None:
        corpus = CorpusSpec.load()
        names = [project.name for project in corpus.projects] + [
            arrangement.name for arrangement in corpus.arrangements
        ]

        assert len(set(names)) == len(names)

    def test_every_voice_a_project_holds_is_a_corpus_voice(self) -> None:
        corpus = CorpusSpec.load()

        assert {voice for project in corpus.projects for voice in project.voices} <= set(corpus.voices)
