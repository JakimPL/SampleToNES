# Configuration

_SampleToNES_ converts audio with one set of settings, the **generation configuration**. It covers the
sample rate, the NES frequency, how the audio is analyzed and how sounds are compared. You change the
everyday ones on the **Main** tab. The configuration file has the rest.

## Settings on the Main tab

Three cards on the **Main** tab have the everyday settings:

- **General settings**: the **Sample rate** and **NES frequency** a library is built for,
  **Normalize audio**, which evens out the loudness of the recording before it is matched, and
  **Quantize audio**, which coarsens it to fewer volume steps first.
- **Source settings**: the channel settings of the recording you selected. See
  [settings for one recording](converting.md#settings-for-one-recording).
- **Advanced settings**: **Method** and **Feature scaling**, which set how the app measures the
  frequencies in the audio, the number of **Workers**, and the library and output folders. Choose
  **View ▸ Show advanced settings** to show this card. [Reconstruction
  algorithms](../concepts/reconstruction.md) explains **Method** and **Feature scaling**.

The app saves your changes to `config.json`. See [Where your files live](files.md).

## The configuration file

`config.json` holds the rest. The [configuration file
reference](../formats/configuration.md) lists every setting, and [reconstruction
algorithms](../concepts/reconstruction.md) explains what each one does and the value it starts at.

To load or save a whole configuration, use **Reconstruction ▸ Load generation settings...** and
**Reconstruction ▸ Save generation settings...**. On the [command line](command-line.md), add
`--config` to a command.
