import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Toaster } from 'sonner';
import { AiChat } from './AiChat';

export function Layout() {
  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="main-content">
        <Outlet />
      </main>
      <Toaster position="top-right" duration={4000} richColors />
      <AiChat />
    </div>
  );
}
