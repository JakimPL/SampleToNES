from typing import (
    AbstractSet,
    Callable,
    Dict,
    Final,
    Iterable,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
)

from pydantic import BaseModel

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project import Project
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.song import Song
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import samples
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_shared.utils.hashing import hash_model, identity_digest
from sampletones_shared.utils.serialization import dump

FINGERPRINT_LENGTH: Final[int] = 64
SONG_STRUCTURE: Final[Set[str]] = {"rows_per_pattern", "order"}

StreamHash = Callable[[InstructionsItem], str]
AssignmentHash = Callable[[ChannelAssignment], str]
PatternHash = Callable[[Pattern], str]

Value = TypeVar("Value")


class PartHashes(Protocol):
    """How the heavy parts of a project are hashed: each sample's document and the song's patterns.

    A fingerprint spells the project's light structure itself and hands the heavy parts here, so
    one object states the choice for every part a commit pays for: a digest read afresh, or one
    memoized by the object's identity.
    """

    def reconstruction(self, reconstruction: Reconstruction) -> str: ...

    def song(self, song: Song) -> str: ...


def _canonical(
    model: BaseModel,
    *,
    fields: Optional[Set[str]] = None,
) -> str:
    """The model, or the fields of it named, spelled as JSON with its keys sorted, one spelling for one state.

    ``fields`` is the set pydantic's ``include`` takes.
    """
    return dump(model.model_dump(mode="json", include=fields))


def fingerprint_project(
    project: Project,
    *,
    hashes: PartHashes,
) -> str:
    """Returns a content hash used to verify that a restore reproduces a snapshot.

    The hash covers the full project state, spelled out part by part so that two projects
    differing anywhere in it differ here. Each part is hashed with its keys sorted, so a mapping
    holding the same entries in another order reads as the same state. The song and each
    sample's document enter through ``hashes``, so the caller decides between memoized digests
    (capture, where copy-on-write keeps them valid) and fresh ones (verification, where
    recomputing from scratch catches any divergence).
    """
    parts: List[str] = [
        _canonical(project.metadata),
        _canonical(project.info),
        _canonical(project.settings),
        hashes.song(project.song),
    ]
    for voice in project.voices:
        parts.append(voice.id)
        parts.append(voice.name)
        match voice:
            case Sample():
                parts.append(hashes.reconstruction(voice.reconstruction))
            case Instrument():
                parts.append(_canonical(voice))

    return identity_digest(*parts, length=FINGERPRINT_LENGTH)


def reconstruction_digest(
    reconstruction: Reconstruction,
    *,
    stream_hash: StreamHash,
    assignment_hash: AssignmentHash,
) -> str:
    """A reconstruction's content spelled out part by part, its streams and its owner records through the hashes given.

    Every field the document stores enters: its metadata, id, configuration and coefficient, each
    channel's stream, and the record of its recordings, which is the setup, the sources, the
    assignment of each frame to an owner and the scale. The streams' digests join as one part and
    the assignments' as another, so a document of three streams and two records reads apart from
    one of two streams and three. The light parts are spelled in JSON mode; a stream and a record
    are spelled by the hash handed in, which capture memoizes by identity and verification reads
    afresh, and the two agree because each part is spelled one way on both sides.

    Args:
        reconstruction: The document hashed.
        stream_hash: How one channel's stream is hashed.
        assignment_hash: How one channel's owner record is hashed.

    Returns:
        str: The digest of the document's content.
    """
    stems_data = reconstruction.stems_data
    return identity_digest(
        _canonical(reconstruction.metadata),
        reconstruction.id,
        _canonical(reconstruction.config),
        identity_digest(*(stream_hash(stream) for stream in reconstruction.instructions_data)),
        _canonical(stems_data.config),
        identity_digest(*(_canonical(source) for source in stems_data.sources)),
        identity_digest(*(assignment_hash(assignment) for assignment in stems_data.assignments)),
        dump(stems_data.scale),
        dump(reconstruction.coefficient),
    )


def song_digest(
    song: Song,
    *,
    pattern_hash: PatternHash,
) -> str:
    """A song's content spelled out part by part, its patterns through the hash given.

    The row count and the order are spelled in JSON mode as they stand. Each channel's pool is
    one nested part: the channel it is keyed under and named for, then each index it holds a
    pattern at beside that pattern's digest, the pools in channel order and the indices
    ascending, so a pool read in another order reads as the same pool and a pattern moved to
    another index reads as a change. A pattern is spelled by the hash handed in, which capture
    memoizes by identity and verification reads afresh.

    Args:
        song: The song hashed.
        pattern_hash: How one pattern is hashed.

    Returns:
        str: The digest of the song's content.
    """
    return identity_digest(
        _canonical(song, fields=SONG_STRUCTURE),
        *(_pool_digest(name, song.channels[name], pattern_hash) for name in sorted(song.channels)),
    )


def _pool_digest(
    name: ChannelName,
    channel: Channel,
    pattern_hash: PatternHash,
) -> str:
    parts = [dump(name), dump(channel.name)]
    for index in sorted(channel.patterns):
        parts.append(dump(index))
        parts.append(pattern_hash(channel.patterns[index]))

    return identity_digest(*parts)


def hash_reconstruction(reconstruction: Reconstruction) -> str:
    """A reconstruction's digest with every part read afresh, which a verification spells."""
    return reconstruction_digest(reconstruction, stream_hash=hash_model, assignment_hash=hash_model)


def hash_song(song: Song) -> str:
    """A song's digest with every pattern read afresh, which a verification spells."""
    return song_digest(song, pattern_hash=hash_model)


class FreshHashes:
    """Every heavy part read afresh, so a verification reproduces a digest from the content alone."""

    def reconstruction(self, reconstruction: Reconstruction) -> str:
        return hash_reconstruction(reconstruction)

    def song(self, song: Song) -> str:
        return hash_song(song)


class _Memo:
    """Digests by object identity, each entry holding its object so its ``id()`` stays bound to it."""

    def __init__(self) -> None:
        self._entries: Dict[int, Tuple[object, str]] = {}

    def digest(
        self,
        value: Value,
        compute: Callable[[Value], str],
    ) -> str:
        """The digest kept for ``value``, computed by ``compute`` the first time the object is met."""
        cached = self._entries.get(id(value))
        if cached is None:
            cached = (value, compute(value))
            self._entries[id(value)] = cached

        return cached[1]

    def keep(self, live: AbstractSet[int]) -> None:
        """Releases every entry whose object's identity is outside ``live``."""
        self._entries = {key: value for key, value in self._entries.items() if key in live}


class HashCache:
    """Memoizes content hashes by object identity for every value a project is made of.

    Copy-on-write discipline makes a value's content immutable for the object's lifetime: a
    reconstruction, each stream and each owner record it is made of, and each pattern of the
    song. A gesture replaces the values it changes and keeps every other by identity, so a fresh
    document's digest composes from one new stream's hash and the memoized rest, the song's from
    the one pattern a row edit replaced and the memoized rest, and capture-time fingerprinting
    collapses to hashing what the gesture replaced. The song and its channels are shells written
    in place, so they are spelled afresh on every commit around the memoized patterns. Each entry
    stores a strong reference beside the digest: the reference keeps the object alive, so its
    ``id()`` stays bound to that object for as long as the entry exists. :meth:`prune` keeps only
    the entries whose object still appears in one of the given projects, releasing the rest and
    bounding the cache by what the history retains.
    """

    def __init__(
        self,
        *,
        stream_hash: StreamHash,
        assignment_hash: AssignmentHash,
        pattern_hash: PatternHash,
    ) -> None:
        self._stream_hash = stream_hash
        self._assignment_hash = assignment_hash
        self._pattern_hash = pattern_hash
        self._memo = _Memo()

    def reconstruction(self, reconstruction: Reconstruction) -> str:
        return self._memo.digest(reconstruction, self._compose_reconstruction)

    def song(self, song: Song) -> str:
        return song_digest(song, pattern_hash=self._pattern)

    def _compose_reconstruction(self, reconstruction: Reconstruction) -> str:
        return reconstruction_digest(
            reconstruction,
            stream_hash=self._stream,
            assignment_hash=self._assignment,
        )

    def _stream(self, stream: InstructionsItem) -> str:
        return self._memo.digest(stream, self._stream_hash)

    def _assignment(self, assignment: ChannelAssignment) -> str:
        return self._memo.digest(assignment, self._assignment_hash)

    def _pattern(self, pattern: Pattern) -> str:
        return self._memo.digest(pattern, self._pattern_hash)

    def prune(self, projects: Iterable[Project]) -> None:
        """Keeps the entries of the objects ``projects`` still hold, one live set over every kind of part."""
        retained = list(projects)
        reconstructions = [sample.reconstruction for project in retained for sample in samples(project.voices)]
        live: Set[int] = {id(reconstruction) for reconstruction in reconstructions}
        live.update(id(stream) for reconstruction in reconstructions for stream in reconstruction.instructions_data)
        live.update(
            id(assignment) for reconstruction in reconstructions for assignment in reconstruction.stems_data.assignments
        )
        live.update(
            id(pattern)
            for project in retained
            for channel in project.song.channels.values()
            for pattern in channel.patterns.values()
        )
        self._memo.keep(live)
