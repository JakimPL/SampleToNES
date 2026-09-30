import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

type DriverChannel = {
  enabled: boolean;
  period: number;
  volume: number;
  duty: number;
  noisePeriod: number;
  noiseMode: boolean;
};

type RegisterState = { channels: DriverChannel[] };

type Timeline = { currentPatternOrderIndex: number; currentRow: number };

type TrackerState = { timeline: Timeline };

type TracedChannel = {
  enabled: boolean;
  period: number;
  volume: number;
  duty: number;
  noise_period: number;
  noise_mode: boolean;
};

type TracedTick = { frame: number; row: number; channels: TracedChannel[] };

type Constructor<T> = new (...args: any[]) => T;

type Module = Record<string, any>;

const USAGE = "Usage: trace.mts <bitphase checkout> <document.btp> <trace.json>";
const USAGE_STATUS = 2;
const PUBLIC_DIRECTORY = "public";
const NES_CHIP = "nes";
const SONG_INDEX = 0;
const ONE_PASS = 1;
const SOUNDING_CHANNELS = 4;
const SILENT_OUTPUT = { left: 0, right: 0 };
const STATE_MODULE = "nes/nes-state.js";
const DRIVER_MODULE = "nes/nes-audio-driver.js";
const ENGINE_MODULE = "nes/nes-apu-engine.js";

function traced(channel: DriverChannel): TracedChannel {
  return {
    enabled: channel.enabled,
    period: channel.period,
    volume: channel.volume,
    duty: channel.duty,
    noise_period: channel.noisePeriod,
    noise_mode: channel.noiseMode
  };
}

class TickRecorder {
  readonly ticks: TracedTick[] = [];
  private state: TrackerState | null = null;
  private driverPassed = false;

  watchState(state: TrackerState): void {
    this.state = state;
  }

  markDriverPass(): void {
    this.driverPassed = true;
  }

  // The renderer applies the register state once before its first tick, so a tick is the one
  // apply that follows a pass of the driver over the instruments.
  record(registers: RegisterState): void {
    if (!this.driverPassed || this.state === null) {
      return;
    }
    this.driverPassed = false;
    this.ticks.push({
      frame: this.state.timeline.currentPatternOrderIndex,
      row: this.state.timeline.currentRow,
      channels: registers.channels.slice(0, SOUNDING_CHANNELS).map(traced)
    });
  }
}

function recordingModule(url: string, module: Module, recorder: TickRecorder): Module {
  switch (url) {
    case STATE_MODULE: {
      const State = module.default as Constructor<TrackerState>;
      class WatchedState extends State {
        constructor(...args: any[]) {
          super(...args);
          recorder.watchState(this);
        }
      }
      return { ...module, default: WatchedState };
    }
    case DRIVER_MODULE: {
      const Driver = module.default as Constructor<{
        processInstruments(state: unknown, registers: unknown): void;
      }>;
      class WatchedDriver extends Driver {
        processInstruments(state: unknown, registers: unknown): void {
          super.processInstruments(state, registers);
          recorder.markDriverPass();
        }
      }
      return { ...module, default: WatchedDriver };
    }
    case ENGINE_MODULE:
      return {
        ...module,
        createNesApuEngine(wasm: unknown) {
          const made = module.createNesApuEngine(wasm);
          made.engine.applyRegisterState = (registers: RegisterState) => recorder.record(registers);
          made.engine.process = () => SILENT_OUTPUT;
          return made;
        }
      };
    default:
      return module;
  }
}

async function main(): Promise<void> {
  const [root, documentPath, tracePath] = process.argv.slice(2);
  if (root === undefined || documentPath === undefined || tracePath === undefined) {
    console.error(USAGE);
    process.exit(USAGE_STATUS);
  }

  const upstream = (relative: string): Promise<Module> =>
    import(pathToFileURL(path.join(root, relative)).href);
  const { loadBtpFromFile } = await upstream("cli/btp-loader.ts");
  const { FileSystemResourceLoader } = await upstream("cli/resource-loader-node.ts");
  const { ensureCoreRegistry, getChipByType } = await upstream("src/lib/chips/registry-core.ts");

  await ensureCoreRegistry();
  const project = loadBtpFromFile(path.resolve(documentPath));
  const chip = getChipByType(NES_CHIP);
  const files = new FileSystemResourceLoader(path.join(root, PUBLIC_DIRECTORY));
  const recorder = new TickRecorder();
  const loader = {
    loadWasm: (url: string): Promise<ArrayBuffer> => files.loadWasm(url),
    loadModule: async (url: string): Promise<Module> =>
      recordingModule(url, await files.loadModule(url), recorder)
  };

  const renderer = chip.createRenderer(loader, {
    chipType: chip.type,
    audioSlotKind: chip.audioSlotKind
  });
  await renderer.render(project, SONG_INDEX, undefined, {
    separateChannels: false,
    loopCount: ONE_PASS
  });
  fs.writeFileSync(tracePath, JSON.stringify({ ticks: recorder.ticks }));
}

await main();
