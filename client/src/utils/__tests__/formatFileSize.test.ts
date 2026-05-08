import { describe, it, expect } from 'vitest';
import { formatFileSize } from '../formatFileSize';

describe('formatFileSize', () => {
  it('formats bytes', () => {
    expect(formatFileSize(0)).toBe('0.0 B');
    expect(formatFileSize(512)).toBe('512 B');
  });

  it('formats kilobytes', () => {
    expect(formatFileSize(1024)).toBe('1.0 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
  });

  it('formats megabytes', () => {
    expect(formatFileSize(1048576)).toBe('1.0 MB');
    expect(formatFileSize(1572864)).toBe('1.5 MB');
  });

  it('formats gigabytes', () => {
    expect(formatFileSize(1073741824)).toBe('1.0 GB');
  });

  it('handles invalid inputs', () => {
    expect(formatFileSize(-1)).toBe('0 B');
    expect(formatFileSize(NaN)).toBe('0 B');
  });
});
