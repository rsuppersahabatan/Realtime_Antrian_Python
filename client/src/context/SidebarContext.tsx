import React, { useState, useMemo, ReactNode } from 'react';

type SidebarContextValue = {
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  closeSidebar: () => void;
};

export const SidebarContext = React.createContext<SidebarContextValue | undefined>(undefined);

type SidebarProviderProps = {
  children: ReactNode;
};

export const SidebarProvider: React.FC<SidebarProviderProps> = ({ children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);

  function toggleSidebar(): void {
    setIsSidebarOpen(!isSidebarOpen);
  }

  function closeSidebar(): void {
    setIsSidebarOpen(false);
  }

  const value = useMemo<SidebarContextValue>(
    () => ({
      isSidebarOpen,
      toggleSidebar,
      closeSidebar,
    }),
    [isSidebarOpen]
  );

  return <SidebarContext.Provider value={value}>{children}</SidebarContext.Provider>;
};
