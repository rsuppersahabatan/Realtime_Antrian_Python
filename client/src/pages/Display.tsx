import { useEffect, useMemo, useRef, useState } from 'react';
import type { FC } from 'react';
import PageTitle from '../components/Typography/PageTitle';

const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ||
  'http://localhost:8000';

const STORAGE_KEY = 'display_client_id';
const POLL_INTERVAL_MS = 3000;

type StatusAntrian = 'menunggu' | 'dipanggil' | 'selesai' | 'batal';

type LoketMini = {
  id: number;
  id_layanan: number;
  nama_loket: string;
  status_buka?: 'buka' | 'tutup';
  nama_layanan?: string | null;
  kode_huruf?: string | null;
};

type Client = {
  id: number;
  nama_client: string;
  is_active: 'ya' | 'tidak';
  lokets: LoketMini[];
};

type Antrian = {
  id: number;
  id_layanan: number;
  id_loket: number | null;
  keterangan: string | null;
  nomor_antrian: string;
  status: StatusAntrian;
  waktu_panggil: string | null;
  nama_loket?: string | null;
};

type ApiResponse<T = unknown> = {
  status: boolean;
  message?: string;
  data?: T;
};

type AntrianListResponse = {
  status: boolean;
  data?: Antrian[];
};

function authHeaders(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const DisplayPage: FC = () => {
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | ''>(() => {
    if (typeof window === 'undefined') return '';
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? Number(saved) : '';
  });
  const [antrian, setAntrian] = useState<Antrian[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const fetchClients = async () => {
    try {
      const res = await fetch(`${API_URL}/api/client/active`, { headers: { ...authHeaders() } });
      const json: ApiResponse<Client[]> = await res.json();
      if (!res.ok || !json.status) {
        setError(json.message || `Gagal memuat client (HTTP ${res.status})`);
        return;
      }
      const list = json.data || [];
      setClients(list);
      // Validasi saved client masih ada & aktif
      if (selectedClientId !== '' && !list.find((c) => c.id === selectedClientId)) {
        setSelectedClientId('');
        if (typeof window !== 'undefined') localStorage.removeItem(STORAGE_KEY);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Gagal terhubung ke server');
    }
  };

  const fetchAntrian = async () => {
    try {
      const res = await fetch(`${API_URL}/api/antrian/`, { headers: { ...authHeaders() } });
      const json: AntrianListResponse = await res.json();
      if (!res.ok || !json.status) {
        setError(json.message || `Gagal memuat antrian (HTTP ${res.status})`);
        return;
      }
      setAntrian(json.data || []);
      setLastUpdate(new Date());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Gagal terhubung ke server');
    }
  };

  // Initial load
  useEffect(() => {
    (async () => {
      setLoading(true);
      await Promise.all([fetchClients(), fetchAntrian()]);
      setLoading(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Polling antrian setiap 3 detik
  useEffect(() => {
    const t = setInterval(fetchAntrian, POLL_INTERVAL_MS);
    return () => clearInterval(t);
  }, []);

  // Sync selected client ke localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (selectedClientId === '') {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, String(selectedClientId));
    }
  }, [selectedClientId]);

  // Track fullscreen state
  useEffect(() => {
    const onFsChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, []);

  const selectedClient = useMemo(
    () => clients.find((c) => c.id === selectedClientId) || null,
    [clients, selectedClientId],
  );

  // Untuk setiap loket di client terpilih, ambil panggilan terakhir hari ini
  type CallEntry = {
    loket: LoketMini;
    nomor: string | null;
    keterangan: string | null;
    waktu_panggil: string | null;
  };

  const calls: CallEntry[] = useMemo(() => {
    if (!selectedClient) return [];
    return selectedClient.lokets.map((l) => {
      const callsForLoket = antrian
        .filter((a) => a.id_loket === l.id && a.waktu_panggil)
        .sort((a, b) => (b.waktu_panggil || '').localeCompare(a.waktu_panggil || ''));
      const top = callsForLoket[0];
      return {
        loket: l,
        nomor: top?.nomor_antrian || null,
        keterangan: top?.keterangan || null,
        waktu_panggil: top?.waktu_panggil || null,
      };
    });
  }, [selectedClient, antrian]);

  const toggleFullscreen = async () => {
    if (!document.fullscreenElement && containerRef.current) {
      await containerRef.current.requestFullscreen().catch(() => {});
    } else {
      await document.exitFullscreen().catch(() => {});
    }
  };

  const waktuShort = (t: string | null) => (t ? t.slice(11, 19) : '');

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PageTitle>Display Client</PageTitle>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          {lastUpdate && (
            <span>
              Update: {lastUpdate.toLocaleTimeString()}{' '}
              <span className="inline-block w-2 h-2 ml-1 bg-green-500 rounded-full animate-pulse" />
            </span>
          )}
          <button
            type="button"
            onClick={toggleFullscreen}
            className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:border-gray-500 dark:text-gray-200 dark:bg-gray-700 dark:border-gray-600"
          >
            {isFullscreen ? '⤵ Keluar Fullscreen' : '⤢ Fullscreen'}
          </button>
        </div>
      </div>

      {/* Client picker */}
      <div className="p-4 mb-6 bg-white rounded-lg shadow-xs dark:bg-gray-800">
        {clients.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Tidak ada display dalam status <strong>aktif</strong>. Aktifkan dulu di menu{' '}
            <strong>Setting Display</strong>.
          </p>
        ) : (
          <label className="block text-sm text-gray-700 dark:text-gray-400">
            <span>Pilih Display</span>
            <select
              className="block w-full mt-1 text-sm border border-gray-300 rounded-md px-3 py-2 focus:border-purple-400 focus:outline-none focus:ring focus:ring-purple-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
              value={selectedClientId === '' ? '' : String(selectedClientId)}
              onChange={(e) =>
                setSelectedClientId(e.target.value ? Number(e.target.value) : '')
              }
            >
              <option value="">— Pilih display —</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nama_client} · {c.lokets.length} loket
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {error && (
        <div
          role="alert"
          className="mb-4 px-3 py-2 text-sm text-red-700 bg-red-100 border border-red-200 rounded-md dark:bg-red-900/30 dark:text-red-300 dark:border-red-800"
        >
          {error}
        </div>
      )}

      {/* Display panel — fullscreen-able container */}
      <div
        ref={containerRef}
        className={
          'rounded-lg ' +
          (isFullscreen
            ? 'fixed inset-0 z-50 bg-gray-900 p-8 overflow-auto'
            : 'bg-gradient-to-br from-gray-50 to-gray-200 dark:from-gray-900 dark:to-gray-800 p-6 shadow-xs')
        }
      >
        {!selectedClient ? (
          <p className="py-12 text-center text-gray-500 dark:text-gray-400">
            {loading ? 'Memuat...' : 'Pilih display dulu untuk melihat panggilan.'}
          </p>
        ) : calls.length === 0 ? (
          <p className="py-12 text-center text-gray-500 dark:text-gray-400">
            Display ini belum punya loket yang ditampilkan. Tambahkan loket di Setting Display.
          </p>
        ) : (
          <>
            {isFullscreen && (
              <h2 className="mb-6 text-3xl font-bold text-center text-white">
                {selectedClient.nama_client}
              </h2>
            )}
            <div
              className={
                'grid gap-6 ' +
                (calls.length === 1
                  ? 'grid-cols-1'
                  : calls.length === 2
                    ? 'md:grid-cols-2'
                    : calls.length === 3
                      ? 'md:grid-cols-3'
                      : 'md:grid-cols-2 xl:grid-cols-4')
              }
            >
              {calls.map((c) => (
                <div
                  key={c.loket.id}
                  className={
                    'flex flex-col items-center justify-center p-6 rounded-xl shadow-md text-center ' +
                    (isFullscreen
                      ? 'bg-gray-800 text-white min-h-[40vh]'
                      : 'bg-white dark:bg-gray-800 min-h-[200px]')
                  }
                >
                  <p
                    className={
                      'mb-2 text-sm font-semibold uppercase tracking-wide ' +
                      (isFullscreen ? 'text-purple-300' : 'text-purple-600 dark:text-purple-300')
                    }
                  >
                    {c.loket.nama_loket}
                  </p>
                  <p
                    className={
                      'mb-1 text-xs ' +
                      (isFullscreen ? 'text-gray-400' : 'text-gray-500 dark:text-gray-400')
                    }
                  >
                    {c.loket.kode_huruf && `${c.loket.kode_huruf} · `}
                    {c.loket.nama_layanan}
                  </p>
                  {c.nomor ? (
                    <>
                      <p
                        className={
                          'my-2 font-bold leading-none ' +
                          (isFullscreen
                            ? 'text-9xl text-white'
                            : 'text-7xl text-purple-600 dark:text-purple-400')
                        }
                      >
                        {c.nomor}
                      </p>
                      {c.keterangan && (
                        <p
                          className={
                            'mt-2 text-sm ' +
                            (isFullscreen ? 'text-gray-200' : 'text-gray-700 dark:text-gray-300')
                          }
                        >
                          {c.keterangan}
                        </p>
                      )}
                      <p
                        className={
                          'mt-2 text-xs ' +
                          (isFullscreen ? 'text-gray-400' : 'text-gray-500 dark:text-gray-400')
                        }
                      >
                        Dipanggil pukul {waktuShort(c.waktu_panggil)}
                      </p>
                    </>
                  ) : (
                    <p
                      className={
                        'my-6 text-3xl ' +
                        (isFullscreen ? 'text-gray-500' : 'text-gray-400 dark:text-gray-500')
                      }
                    >
                      -
                    </p>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <p className="mt-4 text-xs text-gray-500 dark:text-gray-400">
        Panel ini polling tiap {POLL_INTERVAL_MS / 1000} detik. Pakai tombol Fullscreen untuk mode
        layar TV.
      </p>
    </>
  );
};

export default DisplayPage;
