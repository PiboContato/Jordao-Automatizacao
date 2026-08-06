import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LogOut, Palette } from 'lucide-react';
import { NAV_ITEMS } from '../navItems';
import { useUsuario, temPermissao } from '../../context/UsuarioContext';
import styles from './Sidebar.module.css';

interface SidebarProps {
  onTema: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onTema }) => {
  const { usuario, logout } = useUsuario();
  const navigate = useNavigate();

  const itensVisiveis = NAV_ITEMS.filter((item) => temPermissao(usuario, item.flag));

  function sair() {
    logout();
    navigate('/login');
  }

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand} title="Agente Jordão">
        J
      </div>

      <nav className={styles.menu}>
        {itensVisiveis.map((item) => (
          <NavLink
            key={item.id}
            to={item.path}
            title={item.label}
            className={({ isActive }) =>
              `${styles.link} ${isActive ? styles.linkActive : ''}`
            }
            end={item.path === '/'}
          >
            {item.icon}
            <span className={styles.linkLabel}>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className={styles.bottom}>
        {usuario && (
          <div className={styles.avatar} title={usuario.nome}>
            {usuario.nome.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()}
          </div>
        )}
        <button onClick={onTema} className={styles.action} title="Tema de cor">
          <Palette size={20} />
        </button>
        <button onClick={sair} className={`${styles.action} ${styles.actionDanger}`} title="Sair">
          <LogOut size={20} />
        </button>
      </div>
    </aside>
  );
};
