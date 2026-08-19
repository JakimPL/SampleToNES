# Configuration

_SampleToNES_ reconstructs according to a **generation configuration** — the
sample rate, the NES frequency, which channels are used, how the audio is
analysed, and how candidates are scored. The settings you reach for most often are
on the **Main** tab; the rest live in the configuration file, for when you want to
go deeper.

## From the interface

The **Main** tab exposes the everyday settings (grouped under **General
settings**, **Reconstructor settings**, and **Advanced settings**):

- which **Channels** take part, and the **Drive** applied to them;
- **Normalize audio** and **Quantize audio** preprocessing;
- the **Sample rate** and **NES frequency**;
- the **Generation method** and **Feature scaling**, which set how the audio's
  frequency content is measured and weighted (see
  [Reconstruction algorithms](../concepts/reconstruction.md));
- the **Workers** count and the library and output folders.

Changing any of these updates your configuration, which is saved to `config.json`
(see [Where your files live](files.md)).

## In the configuration file

The configuration holds more than the interface shows. The finer controls — the
[selector](../concepts/reconstruction.md) (greedy or Viterbi), the phase aligner,
the scoring weights and distance metric, the number of candidates kept per frame,
and so on — can be edited directly in `config.json`. The
[configuration file reference](../formats/configuration.md) lists every section
and key, and [Reconstruction algorithms](../concepts/reconstruction.md) explains
what they do and lists the defaults.

You can also load and save whole configurations from the **Reconstruction** menu
(**Load generation settings...** and **Save generation settings...**), or point the
app at one on the [command line](command-line.md) with `--config`.

## Deployment settings

A couple of settings — the log level and strict history checking — are decided when
the application is packaged, not by you, so they are not part of your
configuration. They exist for development and support.
