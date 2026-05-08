import '@testing-library/jest-dom';

// ---------------------------------------------------------------------------
// localStorage stub — jsdom provides a real localStorage but vitest's module
// isolation sometimes replaces it. This ensures tests always have a working
// implementation with .clear().
// ---------------------------------------------------------------------------

const localStorageStore: Record<string, string> = {};

const localStorageMock: Storage = {
  getItem: (key: string) => localStorageStore[key] ?? null,
  setItem: (key: string, value: string) => {
    localStorageStore[key] = value;
  },
  removeItem: (key: string) => {
    delete localStorageStore[key];
  },
  clear: () => {
    Object.keys(localStorageStore).forEach((k) => delete localStorageStore[k]);
  },
  get length() {
    return Object.keys(localStorageStore).length;
  },
  key: (index: number) => Object.keys(localStorageStore)[index] ?? null,
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

// ---------------------------------------------------------------------------
// AudioContext stub — jsdom doesn't implement Web Audio API
// ---------------------------------------------------------------------------

class MockAudioContext {
  state: AudioContextState = 'running';
  currentTime = 0;
  destination = {};
  sampleRate = 48000;

  createMediaElementSource = vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
  }));
  createAnalyser = vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    fftSize: 128,
    frequencyBinCount: 64,
    smoothingTimeConstant: 0.7,
    getByteFrequencyData: vi.fn(),
  }));
  createBuffer = vi.fn(() => ({
    getChannelData: vi.fn(() => new Float32Array(0)),
    duration: 0,
    length: 0,
    numberOfChannels: 1,
    sampleRate: 48000,
  }));
  createBufferSource = vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
    buffer: null as AudioBuffer | null,
    onended: null as (() => void) | null,
  }));
  createMediaStreamSource = vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
  }));
  resume = vi.fn(() => Promise.resolve());
  suspend = vi.fn(() => Promise.resolve());
  close = vi.fn(() => Promise.resolve());
  decodeAudioData = vi.fn(() => Promise.resolve({
    duration: 0.1,
    length: 4800,
    numberOfChannels: 1,
    sampleRate: 48000,
    getChannelData: vi.fn(() => new Float32Array(4800)),
  }));
  audioWorklet = {
    addModule: vi.fn(() => Promise.resolve()),
  };
}

class MockOfflineAudioContext extends MockAudioContext {
  constructor(
    _channels: number,
    _length: number,
    _sampleRate: number,
  ) {
    super();
    this.sampleRate = _sampleRate;
  }
  startRendering = vi.fn(() =>
    Promise.resolve({
      duration: 0.1,
      length: 4800,
      numberOfChannels: 1,
      sampleRate: this.sampleRate,
      getChannelData: vi.fn(() => new Float32Array(4800)),
    }),
  );
}

vi.stubGlobal('AudioContext', MockAudioContext);
vi.stubGlobal('OfflineAudioContext', MockOfflineAudioContext);

// ---------------------------------------------------------------------------
// AudioWorkletNode stub
// ---------------------------------------------------------------------------

class MockAudioWorkletNode {
  port = { onmessage: null as ((e: MessageEvent) => void) | null, postMessage: vi.fn() };
  connect = vi.fn();
  disconnect = vi.fn();
}

vi.stubGlobal('AudioWorkletNode', MockAudioWorkletNode);

// ---------------------------------------------------------------------------
// MediaDevices stub
// ---------------------------------------------------------------------------

const mockMediaStream = {
  getTracks: vi.fn(() => []),
  getAudioTracks: vi.fn(() => [{ stop: vi.fn(), kind: 'audio' }]),
};

Object.defineProperty(navigator, 'mediaDevices', {
  value: {
    getUserMedia: vi.fn(() => Promise.resolve(mockMediaStream)),
  },
  writable: true,
});

// ---------------------------------------------------------------------------
// URL.createObjectURL / revokeObjectURL stubs
// ---------------------------------------------------------------------------

vi.stubGlobal('URL', {
  ...URL,
  createObjectURL: vi.fn(() => 'blob:mock-url'),
  revokeObjectURL: vi.fn(),
});

// ---------------------------------------------------------------------------
// requestAnimationFrame / cancelAnimationFrame stubs
// ---------------------------------------------------------------------------

vi.stubGlobal('requestAnimationFrame', vi.fn((cb: FrameRequestCallback) => {
  // Don't auto-invoke — let tests control timing
  return 1;
}));
vi.stubGlobal('cancelAnimationFrame', vi.fn());
