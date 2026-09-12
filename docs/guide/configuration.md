# Configuration

_SampleToNES_ reconstructs audio according to a **generation configuration**: the
sample rate, the NES frequency, how the audio is analyzed, and how candidates are
scored. The settings you change most often are on the **Main** tab. The rest are
in the configuration file, for when you want to go deeper.

Channels are not part of the configuration. The NES has four sound channels —
**Pulse 1**, **Pulse 2**, **Triangle**, and **Noise** — and you choose which of
them each recording uses in the converter's list, every time you set up a
conversion. See [choosing which channels a recording
uses](converting.md#choosing-which-channels-a-recording-uses).

## From the interface

Three cards on the **Main** tab hold the everyday settings:

- **General settings** — **Normalize audio** and **Quantize audio**, and the
  **Sample rate** and **NES frequency** that a library is built for.
- **Source settings** — **Drive**, which sets how hard the channels are pushed,
  and the channels and bends of the recording you selected in the converter's
  list.
- **Advanced settings** — **Method** and **Feature scaling**, which set how the
  audio's frequency content is measured and weighted (see [Reconstruction
  algorithms](../concepts/reconstruction.md)); the **Workers** count; and the
  instruction library and output folders. Choose **View ▸ Show advanced
  settings** to display this card.

Changing any of these updates your configuration, which is saved to `config.json`
(see [Where your files live](files.md)).

## In the configuration file

The configuration holds more than the interface shows. You can edit the finer
controls directly in `config.json`: the
[selector](../concepts/reconstruction.md) (greedy or Viterbi), the phase aligner,
the scoring weights and distance metric, the number of candidates kept per frame,
and so on. The [configuration file
reference](../formats/configuration.md) lists every section and key, and
[Reconstruction algorithms](../concepts/reconstruction.md) explains what they do
and lists the defaults.

You can also load and save whole configurations from the **Reconstruction** menu
(**Load generation settings...** and **Save generation settings...**), or point
the app at one on the [command line](command-line.md) with `--config`.

## Deployment settings

Two settings — the log level and strict history checking — are decided when the
application is packaged, so they are not part of your configuration. They exist
for development and support.
