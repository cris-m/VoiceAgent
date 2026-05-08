import { describe, it, expect } from 'vitest';
import { formatTime } from '../formatTime';

describe('formatTime', () => {
  it('formats zero seconds', () => {
    expect(formatTime(0)).toBe('0:00');
  });

  it('formats minutes and seconds', () => {
    expect(formatTime(65)).toBe('1:05');
    expect(formatTime(125)).toBe('2:05');
  });

  it('pads single-digit seconds', () => {
    expect(formatTime(5)).toBe('0:05');
    expect(formatTime(9)).toBe('0:09');
  });

  it('handles over one hour', () => {
    expect(formatTime(3661)).toBe('61:01');
  });

  it('handles invalid inputs', () => {
    expect(formatTime(-1)).toBe('0:00');
    expect(formatTime(NaN)).toBe('0:00');
  });
});
