import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { useUsuario } from '../context/UsuarioContext';
import { Sidebar } from './Sidebar/Sidebar';
import { BottomNav } from './BottomNav/BottomNav';
import ModoExibicaoPopup from './ModoExibicaoPopup/ModoExibicaoPopup';

export const Layout: React.FC = () => {
  const { usuario } = useUsuario();
  const [temaAberto, setTemaAberto] = useState(false);
  const tema = usuario?.modo_exibicao ?? 'colorido';

  return (
    <div className={`app-shell modo-${tema}`}>
      <Sidebar onTema={() => setTemaAberto(true)} />
      <main className="main-content">
        <Outlet />
      </main>
      <BottomNav onTema={() => setTemaAberto(true)} />
      {temaAberto && <ModoExibicaoPopup onClose={() => setTemaAberto(false)} />}
    </div>
  );
};

export default Layout;
