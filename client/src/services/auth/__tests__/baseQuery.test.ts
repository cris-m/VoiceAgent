import { describe, it, expect, beforeEach, vi } from 'vitest';

class SimpleMutex {
  private _isLocked = false;
  private _waiters: Array<() => void> = [];

  async acquire(): Promise<() => void> {
    while (this._isLocked) {
      await new Promise<void>((resolve) => {
        this._waiters.push(resolve);
      });
    }
    this._isLocked = true;
    return () => this.release();
  }

  private release() {
    this._isLocked = false;
    const nextWaiter = this._waiters.shift();
    if (nextWaiter) {
      nextWaiter();
    }
  }
}

describe('SimpleMutex', () => {
  let mutex: SimpleMutex;

  beforeEach(() => {
    mutex = new SimpleMutex();
  });

  it('should allow single acquire and release', async () => {
    const release = await mutex.acquire();
    expect(typeof release).toBe('function');
    release();
  });

  it('should prevent concurrent acquisition', async () => {
    const release1 = await mutex.acquire();
    
    let acquired = false;
    const promise = mutex.acquire().then((release2) => {
      acquired = true;
      release2();
    });

    expect(acquired).toBe(false);
    release1();
    
    await promise;
    expect(acquired).toBe(true);
  });

  it('should maintain FIFO order for waiters', async () => {
    const order: number[] = [];

    const release1 = await mutex.acquire();

    const p2 = mutex.acquire().then((release) => {
      order.push(2);
      release();
    });

    const p3 = mutex.acquire().then((release) => {
      order.push(3);
      release();
    });

    release1();
    await p2;
    await p3;

    expect(order).toEqual([2, 3]);
  });

  it('should allow reacquire after release', async () => {
    const release1 = await mutex.acquire();
    release1();

    const release2 = await mutex.acquire();
    expect(typeof release2).toBe('function');
    release2();
  });

  it('should handle multiple concurrent waiters', async () => {
    const results: number[] = [];
    const release1 = await mutex.acquire();

    const promises = Array.from({ length: 5 }, (_, i) =>
      mutex.acquire().then((release) => {
        results.push(i + 1);
        release();
      })
    );

    release1();
    await Promise.all(promises);

    expect(results.length).toBe(5);
    expect(results).toEqual([1, 2, 3, 4, 5]);
  });
});
