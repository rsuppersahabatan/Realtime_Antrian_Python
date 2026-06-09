import React, { useEffect, useMemo, useState } from 'react';
import PageTitle from '../components/Typography/PageTitle';
import { EditIcon, TrashIcon } from '../icons';

const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ||
  'http://localhost:8000';

type IsActive = 'ya' | 'tidak';

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
  is_active: IsActive;
  lokets: LoketMini[];
};

type ApiResponse<T = unknown> = {
  status: boolean;
  message?: string;
  data?: T;
};

type FormState = {
  nama_client: string;
  is_active: IsActive;
  id_lokets: number[];
};

const emptyForm: FormState = {
  nama_client: '',
  is_active: 'tidak',
  id_lokets: [],
};

const PAGE_SIZE = 10;

function authHeaders(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const DisplaySettingPage: React.FC = () => {
  const [items, setItems] = useState<Client[]>([]);
  const [loketList, setLoketList] = useState<LoketMini[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [resClient, resLoket] = await Promise.all([
        fetch(`${API_URL}/api/client/`, { headers: { ...authHeaders() } }),
        fetch(`${API_URL}/api/loket/`, { headers: { ...authHeaders() } }),
      ]);

      const jsonClient: ApiResponse<Client[]> = await resClient.json();
      if (!resClient.ok || !jsonClient.status) {
        setError(jsonClient.message || `Gagal memuat client (HTTP ${resClient.status})`);
        return;
      }
      setItems(jsonClient.data || []);

      const jsonLoket: ApiResponse<LoketMini[]> = await resLoket.json();
      if (resLoket.ok && jsonLoket.status) setLoketList(jsonLoket.data || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Gagal terhubung ke server');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(null), 3000);
    return () => clearTimeout(t);
  }, [notice]);

  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = useMemo(
    () => items.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE),
    [items, safePage],
  );
  const showingFrom = items.length === 0 ? 0 : (safePage - 1) * PAGE_SIZE + 1;
  const showingTo = Math.min(safePage * PAGE_SIZE, items.length);

  const pageNumbers = useMemo(() => {
    const maxButtons = 5;
    if (totalPages <= maxButtons) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    let start = Math.max(1, safePage - 2);
    const end = Math.min(totalPages, start + maxButtons - 1);
    start = Math.max(1, end - maxButtons + 1);
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }, [totalPages, safePage]);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm);
    setFormError(null);
    setIsModalOpen(true);
  };

  const openEdit = (row: Client) => {
    setEditingId(row.id);
    setForm({
      nama_client: row.nama_client,
      is_active: row.is_active,
      id_lokets: row.lokets.map((l) => l.id),
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    if (submitting) return;
    setIsModalOpen(false);
  };

  const toggleLoket = (id: number) => {
    setForm((f) =>
      f.id_lokets.includes(id)
        ? { ...f, id_lokets: f.id_lokets.filter((x) => x !== id) }
        : { ...f, id_lokets: [...f.id_lokets, id] },
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setFormError(null);

    const payload = {
      nama_client: form.nama_client.trim(),
      is_active: form.is_active,
      id_lokets: form.id_lokets,
    };

    const url = editingId ? `${API_URL}/api/client/${editingId}` : `${API_URL}/api/client/`;
    const method = editingId ? 'PUT' : 'POST';

    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(payload),
      });
      const json: ApiResponse<Client> = await res.json();
      if (!res.ok || !json.status) {
        setFormError(json.message || `Operasi gagal (HTTP ${res.status})`);
        return;
      }
      setIsModalOpen(false);
      setNotice(json.message || (editingId ? 'Client diupdate' : 'Client ditambahkan'));
      await fetchAll();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Gagal terhubung ke server');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (row: Client) => {
    if (!window.confirm(`Hapus client "${row.nama_client}"?`)) return;
    try {
      const res = await fetch(`${API_URL}/api/client/${row.id}`, {
        method: 'DELETE',
        headers: { ...authHeaders() },
      });
      const json: ApiResponse = await res.json();
      if (!res.ok || !json.status) {
        setError(json.message || `Gagal menghapus (HTTP ${res.status})`);
        return;
      }
      setNotice(json.message || 'Client dihapus');
      await fetchAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Gagal terhubung ke server');
    }
  };

  const toggleActive = async (row: Client) => {
    const next: IsActive = row.is_active === 'ya' ? 'tidak' : 'ya';
    try {
      const res = await fetch(`${API_URL}/api/client/status/${row.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ is_active: next }),
      });
      const json: ApiResponse = await res.json();
      if (!res.ok || !json.status) {
        setError(json.message || `Gagal mengubah status (HTTP ${res.status})`);
        return;
      }
      setNotice(`Client "${row.nama_client}" sekarang ${next === 'ya' ? 'AKTIF' : 'NONAKTIF'}`);
      await fetchAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Gagal terhubung ke server');
    }
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <PageTitle>Setting Display</PageTitle>
        <button
          type="button"
          onClick={openCreate}
          className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 focus:outline-none focus:shadow-outline-purple"
        >
          + Tambah Display
        </button>
      </div>

      {notice && (
        <div
          role="status"
          className="mb-4 px-3 py-2 text-sm text-green-700 bg-green-100 border border-green-200 rounded-md dark:bg-green-900/30 dark:text-green-300 dark:border-green-800"
        >
          {notice}
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="mb-4 px-3 py-2 text-sm text-red-700 bg-red-100 border border-red-200 rounded-md dark:bg-red-900/30 dark:text-red-300 dark:border-red-800"
        >
          {error}
        </div>
      )}

      <div className="w-full overflow-hidden rounded-lg shadow-xs">
        <div className="w-full overflow-x-auto">
          <table className="w-full whitespace-no-wrap">
            <thead>
              <tr className="text-xs font-semibold tracking-wide text-left text-gray-500 uppercase border-b dark:border-gray-700 bg-gray-50 dark:text-gray-400 dark:bg-gray-800">
                <th className="px-4 py-3">Nama Display</th>
                <th className="px-4 py-3">Loket Ditampilkan</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y dark:divide-gray-700 dark:bg-gray-800">
              {loading && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-4 py-6 text-sm text-center text-gray-500 dark:text-gray-400"
                  >
                    Memuat...
                  </td>
                </tr>
              )}

              {!loading && items.length === 0 && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-4 py-6 text-sm text-center text-gray-500 dark:text-gray-400"
                  >
                    Belum ada display
                  </td>
                </tr>
              )}

              {!loading &&
                pageItems.map((row) => (
                  <tr key={row.id} className="text-gray-700 dark:text-gray-400">
                    <td className="px-4 py-3 text-sm font-semibold">{row.nama_client}</td>
                    <td className="px-4 py-3 text-sm">
                      {row.lokets.length === 0 ? (
                        <span className="text-gray-400">-</span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {row.lokets.map((l) => (
                            <span
                              key={l.id}
                              className="inline-block px-2 py-0.5 text-xs font-semibold leading-none text-gray-700 bg-gray-100 rounded-full dark:text-gray-200 dark:bg-gray-700"
                            >
                              {l.nama_loket}
                              {l.kode_huruf && (
                                <span className="ml-1 text-gray-500 dark:text-gray-400">
                                  ({l.kode_huruf})
                                </span>
                              )}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <button
                        type="button"
                        onClick={() => toggleActive(row)}
                        title="Klik untuk toggle status"
                        className={
                          'inline-block px-2 py-1 text-xs font-semibold leading-none rounded-full cursor-pointer ' +
                          (row.is_active === 'ya'
                            ? 'text-green-700 bg-green-100 hover:bg-green-200 dark:text-green-100 dark:bg-green-700'
                            : 'text-red-700 bg-red-100 hover:bg-red-200 dark:text-red-100 dark:bg-red-700')
                        }
                      >
                        {row.is_active === 'ya' ? 'aktif' : 'nonaktif'}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end space-x-4">
                        <button
                          type="button"
                          onClick={() => openEdit(row)}
                          className="text-gray-600 hover:text-purple-600 dark:text-gray-400 focus:outline-none"
                          aria-label="Edit"
                        >
                          <EditIcon className="w-5 h-5" aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(row)}
                          className="text-gray-600 hover:text-red-600 dark:text-gray-400 focus:outline-none"
                          aria-label="Hapus"
                        >
                          <TrashIcon className="w-5 h-5" aria-hidden="true" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        {/* Pagination footer */}
        <div className="grid px-4 py-3 text-xs font-semibold tracking-wide text-gray-500 uppercase border-t dark:border-gray-700 bg-gray-50 sm:grid-cols-9 dark:text-gray-400 dark:bg-gray-800">
          <span className="flex items-center col-span-3">
            Showing {showingFrom}-{showingTo} of {items.length}
          </span>
          <span className="col-span-2" />
          <span className="flex col-span-4 mt-2 sm:mt-auto sm:justify-end">
            <nav aria-label="Table navigation">
              <ul className="inline-flex items-center">
                <li>
                  <button
                    type="button"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={safePage <= 1}
                    className="px-3 py-1 rounded-md rounded-r-none focus:outline-none focus:shadow-outline-purple disabled:opacity-40"
                    aria-label="Previous"
                  >
                    ‹
                  </button>
                </li>
                {pageNumbers.map((n) => (
                  <li key={n}>
                    <button
                      type="button"
                      onClick={() => setPage(n)}
                      className={
                        'px-3 py-1 rounded-md focus:outline-none focus:shadow-outline-purple ' +
                        (n === safePage
                          ? 'text-white bg-purple-600 border border-r-0 border-purple-600'
                          : '')
                      }
                    >
                      {n}
                    </button>
                  </li>
                ))}
                <li>
                  <button
                    type="button"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={safePage >= totalPages}
                    className="px-3 py-1 rounded-md rounded-l-none focus:outline-none focus:shadow-outline-purple disabled:opacity-40"
                    aria-label="Next"
                  >
                    ›
                  </button>
                </li>
              </ul>
            </nav>
          </span>
        </div>
      </div>

      {isModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6 bg-black/50"
          onClick={closeModal}
        >
          <div
            className="w-full max-w-md p-6 bg-white rounded-lg shadow-xl dark:bg-gray-800 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-4 text-lg font-semibold text-gray-700 dark:text-gray-300">
              {editingId ? 'Edit Display' : 'Tambah Display'}
            </h3>

            {formError && (
              <div
                role="alert"
                className="mb-3 px-3 py-2 text-sm text-red-700 bg-red-100 border border-red-200 rounded-md dark:bg-red-900/30 dark:text-red-300 dark:border-red-800"
              >
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3">
              <label className="block text-sm text-gray-700 dark:text-gray-400">
                <span>Nama Display</span>
                <input
                  className="block w-full mt-1 text-sm border border-gray-300 rounded-md px-3 py-2 focus:border-purple-400 focus:outline-none focus:ring focus:ring-purple-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
                  type="text"
                  maxLength={50}
                  placeholder="TV Lobby, TV Poli"
                  value={form.nama_client}
                  onChange={(e) => setForm({ ...form, nama_client: e.target.value })}
                  required
                  disabled={submitting}
                />
              </label>

              <label className="block text-sm text-gray-700 dark:text-gray-400">
                <span>Status</span>
                <select
                  className="block w-full mt-1 text-sm border border-gray-300 rounded-md px-3 py-2 focus:border-purple-400 focus:outline-none focus:ring focus:ring-purple-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
                  value={form.is_active}
                  onChange={(e) =>
                    setForm({ ...form, is_active: e.target.value as IsActive })
                  }
                  disabled={submitting}
                >
                  <option value="tidak">tidak (nonaktif)</option>
                  <option value="ya">ya (aktif)</option>
                </select>
              </label>

              <div className="block text-sm text-gray-700 dark:text-gray-400">
                <span>Loket yang Ditampilkan ({form.id_lokets.length} dipilih)</span>
                <div className="mt-1 border border-gray-300 rounded-md dark:border-gray-600 max-h-48 overflow-y-auto bg-white dark:bg-gray-700">
                  {loketList.length === 0 ? (
                    <p className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">
                      Tidak ada loket
                    </p>
                  ) : (
                    loketList.map((l) => (
                      <label
                        key={l.id}
                        className="flex items-center px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-600"
                      >
                        <input
                          type="checkbox"
                          className="mr-2 text-purple-600 form-checkbox focus:border-purple-400 focus:outline-none focus:ring focus:ring-purple-300"
                          checked={form.id_lokets.includes(l.id)}
                          onChange={() => toggleLoket(l.id)}
                          disabled={submitting}
                        />
                        <span className="text-gray-700 dark:text-gray-200">{l.nama_loket}</span>
                        <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                          {l.kode_huruf && `(${l.kode_huruf})`} {l.nama_layanan}
                        </span>
                      </label>
                    ))
                  )}
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:border-gray-500 dark:text-gray-200 dark:bg-gray-700 dark:border-gray-600 disabled:opacity-60"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-60"
                >
                  {submitting ? 'Menyimpan...' : editingId ? 'Update' : 'Simpan'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};

export default DisplaySettingPage;
