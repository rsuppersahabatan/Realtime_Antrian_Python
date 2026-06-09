/**
 * ⚠ These are used just to render the Sidebar!
 * You can include any link here, local or external.
 *
 * The leading `-` filename prefix tells TanStack Router to skip this file
 * (per `routeFileIgnorePrefix`), since it's a config module, not a route.
 *
 * For actual Router routes, see TanStack file-based routes
 * (`__root.tsx`, `index.tsx`, etc.).
 *
 * The `icon` value matches a named export from `src/icons/index.ts`.
 */

export type SidebarSubmenuRoute = {
  path: string;
  name: string;
};

export type SidebarRoute = {
  path?: string;
  icon?: string;
  name: string;
  exact?: boolean;
  routes?: SidebarSubmenuRoute[];
};

const routes: SidebarRoute[] = [
  { path: '/layanan', icon: 'FormsIcon', name: 'Layanan' },
  { path: '/loket', icon: 'CardsIcon', name: 'Loket' },
  { path: '/display-client', icon: 'PagesIcon', name: 'Display Client' },
  { path: '/setting-display', icon: 'OutlineCogIcon', name: 'Setting Display' },
  { path: '/antrian', icon: 'TablesIcon', name: 'Antrian' },
  { path: '/panggilan', icon: 'BellIcon', name: 'Panggilan' },
  { path: '/pengguna', icon: 'OutlinePersonIcon', name: 'Pengguna' },
  { path: '/grup-keamanan', icon: 'ForbiddenIcon', name: 'Grup Keamanan' },
];

export default routes;
