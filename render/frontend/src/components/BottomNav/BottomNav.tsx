import React, { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { LogOut, Palette, MoreHorizontal } from 'lucide-react';
import { NAV_ITEMS } from '../navItems';
import { useUsuario, temPermissao } from '../../context/UsuarioContext';
import styles from './BottomNav.module.css';

interface BottomNavProps {
  onTema: () => void;
}

const SLOTS = 5;

export const BottomNav: React.FC<BottomNavProps> = ({ onTema }) => {
  const { usuario, logout } = useUsuario();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuExpandido, setMenuExpandido] = useState(false);

  const itensVisiveis = NAV_ITEMS.filter((item) => temPermissao(usuario, item.flag));

  const idAtivo =
    itensVisiveis.find((item) =>
      item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path)
    )?.id ?? 'inicio';

  const precisaTruncar = itensVisiveis.length > SLOTS;

  let itensBarra = itensVisiveis;
  if (precisaTruncar) {
    const k = SLOTS - 2;
    const activeIndex = Math.max(0, itensVisiveis.findIndex((i) => i.id === idAtivo));
    let start: number;
    let end: number;
    if (activeIndex === 0) {
      start = 1;
      end = start + k - 1;
    } else {
      const leftCount = Math.floor((k - 1) / 2);
      const rightCount = k - 1 - leftCount;
      start = activeIndex - leftCount;
      end = activeIndex + rightCount;
      if (start < 1) {
        start = 1;
        end = start + k - 1;
      }
      if (end > itensVisiveis.length - 1) {
        end = itensVisiveis.length - 1;
        start = end - k + 1;
        if (start < 1) start = 1;
      }
    }
    itensBarra = [itensVisiveis[0], ...itensVisiveis.slice(start, end + 1)];
  }

  function sair() {
    logout();
    navigate('/login');
  }

  return (
    <>
      <nav className={styles.bottomNav}>
        {itensBarra.map((item) => (
          <NavLink
            key={item.id}
            to={item.path}
            title={item.label}
            className={({ isActive }) =>
              `${styles.item} ${isActive ? styles.itemActive : ''}`
            }
            end={item.path === '/'}
            onClick={() => setMenuExpandido(false)}
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
        {precisaTruncar && (
          <button
            onClick={() => setMenuExpandido((p) => !p)}
            className={`${styles.item} ${menuExpandido ? styles.itemActive : ''}`}
            title="Mais opções"
          >
            <MoreHorizontal size={20} />
            <span>Mais</span>
          </button>
        )}
      </nav>

      {menuExpandido && (
        <div className={styles.overlay} onClick={() => setMenuExpandido(false)}>
          <div className={styles.overlayContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.overlayGrid}>
              {itensVisiveis.map((item) => (
                <NavLink
                  key={item.id}
                  to={item.path}
                  title={item.label}
                  className={({ isActive }) =>
                    `${styles.overlayItem} ${isActive ? styles.itemActive : ''}`
                  }
                  end={item.path === '/'}
                  onClick={() => setMenuExpandido(false)}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </NavLink>
              ))}
              <button
                onClick={() => {
                  setMenuExpandido(false);
                  onTema();
                }}
                className={styles.overlayItem}
                title="Tema de cor"
              >
                <Palette size={20} />
                <span>Tema</span>
              </button>
              <button onClick={sair} className={styles.overlayItem} title="Sair">
                <LogOut size={20} />
                <span>Sair</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
