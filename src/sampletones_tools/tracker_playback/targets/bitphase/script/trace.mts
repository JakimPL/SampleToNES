import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

type Timeline = { currentPatternOrderIndex: number; currentRow: number };

type TrackerState = { timeline: Timeline };

type UnitWrite = { unit: string; address: number; value: number };

type TracedTick = { frame: number; row: number; writes: UnitWrite[] };

type Write = (pointer: number, address: number, value: number) => unknown;

type Engine = {
  applyRegisterState(registers: unknown): void;
  process(sampleRate: number): unknown;
};

type Constructor<T> = new (...args: any[]) => T;

type Module = Record<string, any>;

const USAGE = "Usage: trace.mts <bitphase directory> <document.btp> <trace.json>";
const USAGE_STATUS = 2;
const PUBLIC_DIRECTORY = "public";
const NES_CHIP = "nes";
const SONG_INDEX = 0;
const ONE_PASS = 1;
const SILENT_OUTPUT = { left: 0, right: 0 };
const STATE_MODULE = "nes/nes-state.js";
const DRIVER_MODULE = "nes/nes-audio-driver.js";
const ENGINE_MODULE = "nes/nes-apu-engine.js";
const UNIT_WRITES: Record<string, string> = {
  apu: "nes_apu_Write",
  dmc: "nes_dmc_Write"
};

class TickRecorder {
  readonly ticks: TracedTick[] = [];
  private pending: UnitWrite[] = [];
  private state: TrackerState | null = null;
  private driverPassed = false;

  watchState(state: TrackerState): void {
    this.state = state;
  }

  markDriverPass(): void {
    this.driverPassed = true;
  }

  write(unit: string, address: number, value: number): void {
    this.pending.push({ unit, address, value });
  }

  // The engine writes the chip as it resets and once more before the first tick, so a tick is the
  // apply that follows a pass of the driver over the instruments, carrying every write since the
  // tick before.
  record(): void {
    if (!this.driverPassed || this.state === null) {
      return;
    }
    this.driverPassed = false;
    this.ticks.push({
      frame: this.state.timeline.currentPatternOrderIndex,
      row: this.state.timeline.currentRow,
      writes: this.pending
    });
    this.pending = [];
  }
}

// The emulator splits the APU into two units, and the engine writes each through an export of its
// own on the module it is created with. The exports object is frozen, so the engine is handed a copy.
function recordingWasm(wasm: Module, recorder: TickRecorder): Module {
  const recording: Module = { ...wasm };
  for (const [unit, name] of Object.entries(UNIT_WRITES)) {
    const write = wasm[name] as Write;
    recording[name] = (pointer: number, address: number, value: number): unknown => {
      recorder.write(unit, address, value);
      return write(pointer, address, value);
    };
  }
  return recording;
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
        createNesApuEngine(wasm: Module) {
          const made = module.createNesApuEngine(recordingWasm(wasm, recorder));
          const engine = made.engine as Engine;
          const apply = engine.applyRegisterState.bind(engine);
          engine.applyRegisterState = (registers: unknown) => {
            apply(registers);
            recorder.record();
          };
          engine.process = () => SILENT_OUTPUT;
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
