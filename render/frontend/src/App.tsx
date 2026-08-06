import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { UsuarioProvider, useUsuario, temPermissao } from './context/UsuarioContext';
import type { Usuario } from './api/client';
import { Layout } from './components/Layout';
import { Login } from './pages/Login/Login';
import { Inicio } from './pages/Inicio/Inicio';
import { Automacao } from './pages/Automacao/Automacao';
import { BI } from './pages/BI/BI';
import { Tabelas } from './pages/Tabelas/Tabelas';
import { TabelaView } from './pages/Tabelas/TabelaView';
import { Auditoria } from './pages/Auditoria/Auditoria';
import { Backups } from './pages/Backups/Backups';
import { Logs } from './pages/Logs/Logs';
import { Notificacoes } from './pages/Notificacoes/Notificacoes';
import { Usuarios } from './pages/Usuarios/Usuarios';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { usuario, carregando } = useUsuario();

  if (carregando) {
    return (
      <div style={{
        display: 'flex',
        height: '100vh',
        width: '100vw',
        justifyContent: 'center',
        alignItems: 'center',
        background: 'var(--cor-fundo)',
        color: 'var(--cor-texto)',
        fontFamily: 'sans-serif',
        fontSize: '1.2rem',
        fontWeight: 600
      }}>
        Carregando painel do Agente Jordão...
      </div>
    );
  }

  if (!usuario) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequirePermissao({ flag, children }: { flag?: keyof Usuario; children: React.ReactNode }) {
  const { usuario } = useUsuario();
  if (!temPermissao(usuario, flag)) {
    return (
      <p style={{ color: 'var(--cor-perigo)', padding: '1rem' }}>
        Você não tem permissão para acessar esta página.
      </p>
    );
  }
  return <>{children}</>;
}

export const App: React.FC = () => {
  return (
    <UsuarioProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route element={<RequireAuth><Layout /></RequireAuth>}>
            <Route path="/" element={<Inicio />} />
            <Route
              path="/automacao"
              element={<RequirePermissao flag="acesso_automacao"><Automacao /></RequirePermissao>}
            />
            <Route
              path="/bi"
              element={<RequirePermissao flag="acesso_bi"><BI /></RequirePermissao>}
            />
            <Route
              path="/tabelas"
              element={<RequirePermissao flag="acesso_tabelas"><Tabelas /></RequirePermissao>}
            />
            <Route
              path="/tabelas/:tabela"
              element={<RequirePermissao flag="acesso_tabelas"><TabelaView /></RequirePermissao>}
            />
            <Route
              path="/auditoria"
              element={<RequirePermissao flag="acesso_auditoria"><Auditoria /></RequirePermissao>}
            />
            <Route
              path="/backups"
              element={<RequirePermissao flag="acesso_backups"><Backups /></RequirePermissao>}
            />
            <Route
              path="/logs"
              element={<RequirePermissao flag="acesso_logs"><Logs /></RequirePermissao>}
            />
            <Route
              path="/indicadores-notificacoes"
              element={<RequirePermissao flag="acesso_notificacoes"><Notificacoes /></RequirePermissao>}
            />
            <Route
              path="/usuarios"
              element={<RequirePermissao flag="acesso_usuarios"><Usuarios /></RequirePermissao>}
            />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </UsuarioProvider>
  );
};

export default App;
