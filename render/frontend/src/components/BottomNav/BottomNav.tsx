import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LogOut, Palette } from 'lucide-react';
import { NAV_ITEMS } from '../navItems';
import { useUsuario, temPermissao } from '../../context/UsuarioContext';
import styles from './BottomNav.module.css';

interface BottomNavProps {
  onTema: () => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({ onTema }) => {
  const { usuario, logout } = useUsuario();
  const navigate = useNavigate();

  const itensVisiveis = NAV_ITEMS.filter((item) => temPermissao(usuario, item.flag));

  function sair() {
    logout();
    navigate('/login');
  }

  return (
    <nav className={styles.bottomNav}>
      {itensVisiveis.map((item) => (
        <NavLink
          key={item.id}
          to={item.path}
          title={item.label}
          className={({ isActive }) =>
            `${styles.item} ${isActive ? styles.itemActive : ''}`
          }
          end={item.path === '/'}
        >
          {item.icon}
          <span>{item.label}</span>
        </NavLink>
      ))}
      <button onClick={onTema} className={styles.item} title="Tema de cor">
        <Palette size={20} />
        <span>Tema</span>
      </button>
      <button onClick={sair} className={styles.item} title="Sair">
        <LogOut size={20} />
        <span>Sair</span>
      </button>
    </nav>
  );
};
