# Configuration

_SampleToNES_ converts audio with one set of settings, called the **generation configuration**: the
sample rate, the NES frequency, how the audio is analyzed and how sounds are compared. The settings
you change most often are on the **Main** tab, and the configuration file holds the rest.

You choose the channels each recording uses, how hard it pushes each of them, and how many of
them it sounds at once on the **Main** tab, each time you set up a conversion. See
[settings for one recording](converting.md#settings-for-one-recording).

## Settings on the Main tab

Three cards on the **Main** tab have the everyday settings:

- **General settings**: the **Sample rate** and **NES frequency** a library is built for,
  **Normalize audio**, which evens out the loudness of the recording before it is matched, and
  **Quantize audio**, which coarsens it to fewer volume steps first.
- **Source settings**: the channels and bends of the recording you selected in the converter's
  list, the drive each of those channels is pushed at, and how many of them the recording may
  sound at once.
- **Advanced settings**: **Method** and **Feature scaling**, which set how the app measures the
  frequencies in the audio, the number of **Workers**, and the library and output folders. Choose
  **View ▸ Show advanced settings** to show this card. [Reconstruction
  algorithms](../concepts/reconstruction.md) explains **Method** and **Feature scaling**.

The app saves your changes to `config.json`. See [Where your files live](files.md).

## The configuration file

`config.json` holds the rest: how a frame's sound is analyzed, how a candidate is scored against it,
and how each channel's stream is chosen from the candidates. The [configuration file
reference](../formats/configuration.md) lists every setting, and [reconstruction
algorithms](../concepts/reconstruction.md) explains what each one does and the value it starts at.

To load or save a whole configuration, use **Reconstruction ▸ Load generation settings...** and
**Reconstruction ▸ Save generation settings...**. On the [command line](command-line.md), add
`--config` to a command.
