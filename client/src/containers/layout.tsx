import React, { useContext, Suspense, useEffect, lazy } from 'react';
import { Switch, Route, Redirect, useLocation, RouteComponentProps } from 'react-router-dom';
import routes from '../routes/appRoutes';

import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import Main from './Main';
import ThemedSuspense from '../components/ThemedSuspense';
import { SidebarContext } from '../context/SidebarContext';

const Page404 = lazy(() => import('../pages/404'));

type LayoutProps = Record<string, never>;

type AppRoute = {
  path: string;
  component?: React.ComponentType<RouteComponentProps<Record<string, string>>>;
};

const Layout: React.FC<LayoutProps> = () => {
  const sidebarCtx = useContext(SidebarContext) as {
    isSidebarOpen: boolean;
    closeSidebar: () => void;
  };

  const { isSidebarOpen, closeSidebar } = sidebarCtx;

  const location = useLocation();

  useEffect((): void => {
    closeSidebar();
  }, [location, closeSidebar]);

  return (
    <div
      className={`flex h-screen bg-gray-50 dark:bg-gray-900 ${
        isSidebarOpen ? 'overflow-hidden' : ''
      }`}
    >
      <Sidebar />

      <div className="flex flex-col flex-1 w-full">
        <Header />
        <Main>
          <Suspense fallback={<ThemedSuspense />}>
            <Switch>
              {(routes as AppRoute[]).map((route: AppRoute, i: number) =>
                route.component ? (
                  <Route
                    key={i}
                    exact={true}
                    path={`/app${route.path}`}
                    render={(props): JSX.Element => <route.component {...props} />}
                  />
                ) : null
              )}
              <Redirect exact from="/app" to="/app/dashboard" />
              <Route component={Page404} />
            </Switch>
          </Suspense>
        </Main>
      </div>
    </div>
  );
};

export default Layout;