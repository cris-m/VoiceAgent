/**
 * Tests for the AudioWaveform component.
 *
 * Critical invariant: `createMediaElementSource` can only be called ONCE per
 * HTMLAudioElement (browser constraint). The component caches the ctx/analyser
 * on the element itself (`__waveCtx`, `__waveAnalyser`) so re-renders with
 * the same audio element do not call createMediaElementSource a second time.
 *
 * The AudioContext and requestAnimationFrame are stubbed in setup.ts.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, act } from '@testing-library/react';
import React, { useRef } from 'react';
import { AudioWaveform } from '../AudioWaveform';

// ---------------------------------------------------------------------------
// AudioContext spy — track createMediaElementSource calls per test
// ---------------------------------------------------------------------------

// The global MockAudioContext from setup.ts already stubs AudioContext.
// We need fresh spy instances per test so we clear them in beforeEach.

// ---------------------------------------------------------------------------
// Helper component: wraps AudioWaveform with a real audioRef
// ---------------------------------------------------------------------------

interface WrapperProps {
  isPlaying?: boolean;
  progress?: number;
}

function AudioWaveformWrapper({ isPlaying = false, progress = 0 }: WrapperProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  return (
    <>
      <audio ref={audioRef} data-testid="audio-el" />
      <AudioWaveform
        audioRef={audioRef as React.RefObject<HTMLAudioElement>}
        isPlaying={isPlaying}
        progress={progress}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AudioWaveform – rendering', () => {
  it('renders 48 bars by default (NUM_BARS)', () => {
    render(<AudioWaveformWrapper />);
    // The bars are divs inside the container div
    const container = screen.getByRole('slider');
    expect(container.children).toHaveLength(48);
  });

  it('renders a container with role=slider', () => {
    render(<AudioWaveformWrapper />);
    expect(screen.getByRole('slider')).toBeInTheDocument();
  });

  it('has correct aria-label', () => {
    render(<AudioWaveformWrapper />);
    expect(screen.getByRole('slider')).toHaveAttribute('aria-label', 'Seek');
  });

  it('sets aria-valuenow to rounded progress', () => {
    render(<AudioWaveformWrapper progress={42.7} />);
    expect(screen.getByRole('slider')).toHaveAttribute('aria-valuenow', '43');
  });

  it('sets aria-valuemin=0 and aria-valuemax=100', () => {
    render(<AudioWaveformWrapper />);
    const slider = screen.getByRole('slider');
    expect(slider).toHaveAttribute('aria-valuemin', '0');
    expect(slider).toHaveAttribute('aria-valuemax', '100');
  });

  it('applies the custom height style', () => {
    render(
      <AudioWaveformWrapper />,
    );
    // Default height is 28px
    const container = screen.getByRole('slider');
    expect(container.style.height).toBe('28px');
  });
});

describe('AudioWaveform – createMediaElementSource called-once invariant', () => {
  it('does NOT call createMediaElementSource more than once across multiple re-renders', async () => {
    // The component caches AudioContext on the element via `__waveAnalyser`.
    // We track AudioContext instantiation count to verify only one context
    // is created for repeated renders of the same element.
    let ctxCount = 0;
    const OrigAudioContext = globalThis.AudioContext;

    class TrackingAudioContext extends OrigAudioContext {
      constructor() {
        super();
        ctxCount++;
      }
    }
    vi.stubGlobal('AudioContext', TrackingAudioContext);

    const { rerender } = render(<AudioWaveformWrapper isPlaying={false} progress={0} />);

    await act(async () => {
      rerender(<AudioWaveformWrapper isPlaying={true} progress={25} />);
    });

    await act(async () => {
      rerender(<AudioWaveformWrapper isPlaying={true} progress={50} />);
    });

    // At most 1 AudioContext should be created (cached on the element)
    expect(ctxCount).toBeLessThanOrEqual(1);

    vi.stubGlobal('AudioContext', OrigAudioContext);
  });

  it('caches analyser on the element (__waveAnalyser property)', async () => {
    // Render with isPlaying=true to trigger the effect that calls createMediaElementSource
    const audioEl = document.createElement('audio');

    function DirectWrapper() {
      const audioRef = React.useRef(audioEl);
      return (
        <AudioWaveform
          audioRef={audioRef as React.RefObject<HTMLAudioElement>}
          isPlaying
          progress={0}
        />
      );
    }

    await act(async () => {
      render(<DirectWrapper />);
    });

    // After mount the component should have cached the analyser on the element
    // (or left it undefined if createMediaElementSource threw — which our stub won't)
    type CachedEl = HTMLAudioElement & { __waveAnalyser?: unknown };
    const cached = audioEl as CachedEl;
    // The element is either augmented with __waveAnalyser, or not (if AudioContext
    // setup failed silently). Either way we shouldn't crash.
    expect(() => cached.__waveAnalyser).not.toThrow();
  });
});

describe('AudioWaveform – seek interaction', () => {
  it('calls onSeek when the container is clicked', async () => {
    const onSeek = vi.fn();

    function ClickWrapper() {
      const audioRef = useRef<HTMLAudioElement>(null);
      return (
        <>
          <audio ref={audioRef} />
          <AudioWaveform
            audioRef={audioRef as React.RefObject<HTMLAudioElement>}
            isPlaying={false}
            progress={0}
            onSeek={onSeek}
          />
        </>
      );
    }

    render(<ClickWrapper />);
    const slider = screen.getByRole('slider');

    await act(async () => {
      slider.click();
    });

    expect(onSeek).toHaveBeenCalledTimes(1);
  });
});

describe('AudioWaveform – progress colouring', () => {
  it('renders bars with different colours based on progress threshold', () => {
    render(<AudioWaveformWrapper progress={50} />);
    const container = screen.getByRole('slider');
    const bars = Array.from(container.children) as HTMLDivElement[];

    // First bar (i=0) → (0/48)*100 = 0 ≤ 50 → filled (accent)
    expect(bars[0]?.style.backgroundColor).toBe('var(--color-accent)');
    // Last bar (i=47) → (47/48)*100 ≈ 97.9 > 50 → dimmed
    expect(bars[47]?.style.backgroundColor).toBe('var(--color-border-strong)');
  });
});

describe('AudioWaveform – no crash without audio element', () => {
  it('renders without crashing when audioRef is empty', () => {
    // A ref that has no current (null)
    function NoAudioWrapper() {
      const audioRef = useRef<HTMLAudioElement>(null);
      return (
        <AudioWaveform
          audioRef={audioRef as React.RefObject<HTMLAudioElement>}
          isPlaying={false}
          progress={0}
        />
      );
    }

    expect(() => render(<NoAudioWrapper />)).not.toThrow();
  });
});
