import { io, type Socket } from 'socket.io-client';

const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ||
  'http://localhost:8000';

let socket: Socket | null = null;

/**
 * Singleton Socket.IO client.
 *
 * Server (FastAPI + fastapi_socketio) broadcast pesan ke channel `"message"`
 * dengan payload string:
 *   - `loketXX-NOMOR`                  -> panggilan baru di loket XX
 *   - `loketXX-NOMOR|KETERANGAN`       -> idem, dengan keterangan
 *   - `antrian-baru-{id_layanan}-{nomor}` atau `|KETERANGAN` -> tiket baru diambil
 *
 * Catatan SSR: TanStack Start melakukan SSR — Socket.IO hanya untuk browser,
 * jadi panggil `getSocket()` di dalam `useEffect`, jangan di module-scope.
 */
export function getSocket(): Socket {
  if (typeof window === 'undefined') {
    throw new Error('getSocket() hanya boleh dipanggil di browser (di useEffect)');
  }
  if (!socket) {
    socket = io(API_URL, {
      transports: ['websocket', 'polling'],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });
  }
  return socket;
}

export type ParsedMessage =
  | { kind: 'loket'; idLoket: number; nomor: string; keterangan: string }
  | { kind: 'antrian-baru'; idLayanan: number; nomor: string; keterangan: string }
  | { kind: 'unknown'; raw: string };

/** Parse payload broadcast `message` ke struktur yang typed. */
export function parseMessage(raw: unknown): ParsedMessage {
  if (typeof raw !== 'string') return { kind: 'unknown', raw: String(raw) };

  const [head, ...rest] = raw.split('|');
  const keterangan = rest.join('|');

  // Format panggilan: loketXX-NOMOR
  const mLoket = /^loket(\d+)-(.+)$/.exec(head);
  if (mLoket) {
    return {
      kind: 'loket',
      idLoket: parseInt(mLoket[1], 10),
      nomor: mLoket[2],
      keterangan,
    };
  }

  // Format tiket baru: antrian-baru-{idLayanan}-{nomor}
  const mAntrian = /^antrian-baru-(\d+)-(.+)$/.exec(head);
  if (mAntrian) {
    return {
      kind: 'antrian-baru',
      idLayanan: parseInt(mAntrian[1], 10),
      nomor: mAntrian[2],
      keterangan,
    };
  }

  return { kind: 'unknown', raw };
}
