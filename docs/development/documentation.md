# Writing the documentation

This document governs the prose in this repository: the README, the guide, the development documents, the
reference pages, and the changelog. Consult it before adding a page, and before editing one. The
conventions for code and docstrings are in [guidelines.md](guidelines.md).

## Every document has one reader

Each document serves one reader, and that reader decides the rest: what belongs on the page, how much of
it, and the words it is written in. A passage that serves a different reader belongs in that reader's
document, or nowhere.

| Document | Reader | What they came for |
|---|---|---|
| `README.md` | someone who just found the project | what it is, and how to run it |
| `docs/guide/` | a beginner using the application | how to do the thing they want to do |
| `docs/tools/` | someone running a measurement command | what the command does, and how to run it |
| `docs/development/`, `docs/concepts/` | a developer or agent about to change the code | the design, and the reasons behind it |
| `docs/formats/`, `docs/api/` | a programmer reading or writing our files | the exact shape of a format or a call |
| `CHANGELOG.md` | the people who use each release | what changed for them |

## README

Say what the project is, what it needs, how to install it, and how to run it. Keep it as plain as
possible, and no plainer. A reader decides here whether to try the application at all, so nothing else
competes for their attention. Detail belongs in the guide, and mechanism in the development documents.

## The guide

Write for a beginner who wants to get something done, and assume no prior knowledge. Help the reader
act: name the control they click, in the order they would reach it. Keep each topic short — a few
sentences per feature — and leave out how the application works inside.

Use plain, direct English. Short sentences, one fact each. Everyday verbs, not this repository's own
vocabulary. A term the reader would not know is either avoided or defined in
[the glossary](../glossary.md) and linked from the page that uses it.

Two passages read the way a guide page should. "Voices: samples and instruments" in
[the sequencer guide](../guide/sequencer.md) names each kind in one sentence, then says what the reader
does with it. The three install options at the top of [installation](../guide/installation.md) give each
option a name and one sentence saying who it suits.

## Tools pages

One page per command, written for someone about to run it: what the command measures or produces, how to
run it with no options, what it writes, and every custom use. How it works comes last. The guide's
writing rules hold here — plain English, short sentences, a list wherever the page states several things
of one kind. [Tooling](tooling.md) governs what a tool is, and [docs/index.md](../index.md) lists the
pages.

The opening of [the calibration page](../tools/calibration.md) does this: what it measures, what to use
it for, then how to run it.

## Development documents

Write for a developer or an agent about to change the code. This is the reader of
`docs/development/` and of `docs/concepts/` alike. Open by saying what the document governs and when to
consult it, so a reader learns in one paragraph whether they are in the right place.

What belongs here is what the code cannot say: concepts and definitions, principles, design decisions,
the contracts a layer honors, and the reasons behind them. State what a mechanism achieves, generally.

**Apply one test to every paragraph: if reading the code would tell you the same thing, it goes.** A walk
through classes and methods, a call order, a source tree, a table of which file holds what — the code
already says all of that, and says it correctly after the next refactor. So does a copy of a keybinding, a
default or a measured weight: name the constant or the file that holds the value, not the value.

Lead with principles, then mechanics. Keep the three kinds distinct: a principle is a reason, a convention
is a mechanic that serves it, and a description is a fact about how something works. Prefer a few strong
principles to many narrow rules; a growing list of small rules usually means a principle has gone
unstated.

Write for a reader who never saw the history. A development document is not a devlog: leave out past
states, resolved problems and rejected alternatives. The design as it stands carries its own
justification. Work still owed goes to [the ledger](bugs-and-todos.md), one brief entry each.

Two documents to read for the register: [the render thread](application/render-thread.md), where every
section is a decision with the hazard it answers and the mechanism stays general, and
[colors and palettes](application/palette.md), which does the same in forty lines. The design principles
in [architecture.md](architecture.md) show the other half of it: each principle is a claim with its
reason, binding code it never names.

## Reference pages

Formats and the Python API are consulted rather than read. Be exact and complete about the shape — the
fields, the order, the units — and let tables carry it. A reader arrives knowing what they are looking
for, so the page needs no narrative.

## The changelog

`CHANGELOG.md` belongs to the maintainer, who writes it for the people using each release. Leave it
alone.

## What holds everywhere

- One fact per sentence, and short sentences. Several clauses joined by semicolons hide the facts inside
  them.
- State each fact once, in the document that owns it, and link the sibling document rather than repeating
  it.
- A measurement is written so a reader can place it. State it as a comparison — this against that, taken
  together — or give the conditions it was taken under: the material, the machine, the build. A bare
  figure carries no meaning a reader can check, so it is dropped or turned into the comparison it stands
  for.
- State things in positive terms: what the design does, not what it avoids or once did. Reach for a
  negative only where the contrast teaches something a positive sentence cannot.
- Use American English. A name someone else owns keeps their spelling: `MatchRule.serialise()` is
  jeepney's.

## Upkeep

A document is part of the change that motivates it. Code that alters a contract a document states lands
together with the edit stating the new contract, and a deviation the change knowingly leaves behind lands
with an entry in [the ledger](bugs-and-todos.md).

A development document sits beside what it governs: the top of `docs/development/` holds what spans the
repository's packages, `application/` what governs the graphical application, and `release/` what a
release ships and keeps compatible. [docs/index.md](../index.md) lists every document.

Deleting is an edit like any other. A page whose reader has gone, or whose content the code now carries,
goes with the change that made it so.
