import '@testing-library/jest-dom'

// Node 25 ships its own global `localStorage`, which shadows jsdom's and, without
// `--localstorage-file`, has no methods. Tests need a working one, so install an in-memory
// Storage whenever the global one is unusable.
class MemoryStorage implements Storage {
  private readonly items = new Map<string, string>()

  get length(): number {
    return this.items.size
  }

  clear(): void {
    this.items.clear()
  }

  getItem(key: string): string | null {
    return this.items.get(key) ?? null
  }

  key(index: number): string | null {
    return [...this.items.keys()][index] ?? null
  }

  removeItem(key: string): void {
    this.items.delete(key)
  }

  setItem(key: string, value: string): void {
    this.items.set(key, String(value))
  }
}

const isUsableStorage = (storage: Storage | undefined): boolean =>
  typeof storage?.getItem === 'function'

for (const name of ['localStorage', 'sessionStorage'] as const) {
  if (!isUsableStorage(globalThis[name])) {
    Object.defineProperty(globalThis, name, {
      value: new MemoryStorage(),
      configurable: true,
      writable: true,
    })
  }
}
