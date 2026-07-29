import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { apiFetch } from './api/client';
import { Sidebar } from './components/Sidebar/Sidebar';
import { BottomNav } from './components/BottomNav/BottomNav';
import { Login } from './pages/Login/Login';
import { Inicio } from './pages/Inicio/Inicio';
import { Automacao } from './pages/Automacao/Automacao';
import { BI } from './pages/BI/BI';
import { Tabelas } from './pages/Tabelas/Tabelas';
import { TabelaView } from './pages/Tabelas/TabelaView';
import { Auditoria } from './pages/Auditoria/Auditoria';
import { Backups } from './pages/Backups/Backups';
import { Logs } from './pages/Logs/Logs';

export const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  const checkAuthStatus = async () => {
    try {
      const data = await apiFetch<{ logged_in: boolean }>('/api/auth/status');
      setIsAuthenticated(data.logged_in);
    } catch {
      setIsAuthenticated(false);
    }
  };

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const handleLogout = async () => {
    try {
      await fetch('/logout');
      setIsAuthenticated(false);
    } catch (err) {
      console.error("Erro ao fazer logout:", err);
      setIsAuthenticated(false);
    }
  };

  // Enquanto verifica o status de autenticação
  if (isAuthenticated === null) {
    return (
      <div style={{
        display: 'flex',
        height: '100vh',
        width: '100vw',
        justifyContent: 'center',
        alignItems: 'center',
        background: '#f8f9fa',
        color: '#1a3a2a',
        fontFamily: 'sans-serif',
        fontSize: '1.2rem',
        fontWeight: 600
      }}>
        Carregando painel do Agente Jordão...
      </div>
    );
  }

  return (
    <BrowserRouter>
      {isAuthenticated ? (
        <div className="app-shell" style={{ display: 'flex', minHeight: '100vh', width: '100%' }}>
          <Sidebar onLogout={handleLogout} />
          
          <main className="main-content" style={{
            flex: 1,
            padding: '2rem',
            background: '#ffffff',
            minHeight: '100vh'
          }}>
            <Routes>
              <Route path="/" element={<Inicio />} />
              <Route path="/automacao" element={<Automacao />} />
              <Route path="/bi" element={<BI />} />
              <Route path="/tabelas" element={<Tabelas />} />
              <Route path="/tabelas/:tabela" element={<TabelaView />} />
              <Route path="/auditoria" element={<Auditoria />} />
              <Route path="/backups" element={<Backups />} />
              <Route path="/logs" element={<Logs />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          <BottomNav />
        </div>
      ) : (
        <Routes>
          <Route path="/login" element={<Login onLoginSuccess={() => setIsAuthenticated(true)} />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      )}
    </BrowserRouter>
  );
};

export default App;
