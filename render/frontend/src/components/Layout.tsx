import React, { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { useUsuario } from '../context/UsuarioContext';
import { Sidebar } from './Sidebar/Sidebar';
import { BottomNav } from './BottomNav/BottomNav';
import ModoExibicaoPopup from './ModoExibicaoPopup/ModoExibicaoPopup';
import { api } from '../api/client';

const INTERVALO_ATUALIZACAO_MS = 5 * 60 * 1000; // 5 min, mesmo intervalo dos painéis Astral/Britt

export const Layout: React.FC = () => {
  const { usuario } = useUsuario();
  const [temaAberto, setTemaAberto] = useState(false);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState<string | null>(null);
  const tema = usuario?.modo_exibicao ?? 'colorido';

  useEffect(() => {
    function buscar() {
      api
        .ultimaAtualizacao()
        .then((r) => setUltimaAtualizacao(r.ultima_atualizacao))
        .catch(() => {});
    }
    buscar();
    const intervalo = setInterval(buscar, INTERVALO_ATUALIZACAO_MS);
    return () => clearInterval(intervalo);
  }, []);

  return (
    <div className={`app-shell modo-${tema}`}>
      <Sidebar onTema={() => setTemaAberto(true)} />
      <main className="main-content">
        {ultimaAtualizacao && (
          <div className="update-bar">
            <span className="update-bar-dot" />
            <strong>Última atualização do robô:</strong>
            <span>{new Date(ultimaAtualizacao).toLocaleString('pt-BR')}</span>
          </div>
        )}
        <Outlet />
      </main>
      <BottomNav onTema={() => setTemaAberto(true)} />
      {temaAberto && <ModoExibicaoPopup onClose={() => setTemaAberto(false)} />}
    </div>
  );
};

export default Layout;
