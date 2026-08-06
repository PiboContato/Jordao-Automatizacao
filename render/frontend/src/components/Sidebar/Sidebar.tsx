import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Home, 
  Settings, 
  BarChart3, 
  Table2, 
  ClipboardList, 
  Database, 
  ScrollText, 
  LogOut,
  Bell 
} from 'lucide-react';
import styles from './Sidebar.module.css';

interface SidebarProps {
  onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onLogout }) => {
  const menuItems = [
    { path: '/', label: 'Início', icon: <Home size={18} /> },
    { path: '/automacao', label: 'Automação', icon: <Settings size={18} /> },
    { path: '/bi', label: 'Dashboard (BI)', icon: <BarChart3 size={18} /> },
    { path: '/tabelas', label: 'Tabelas', icon: <Table2 size={18} /> },
    { path: '/auditoria', label: 'Auditoria', icon: <ClipboardList size={18} /> },
    { path: '/indicadores-notificacoes', label: 'Notificações', icon: <Bell size={18} /> },
    { path: '/backups', label: 'Backups', icon: <Database size={18} /> },
    { path: '/logs', label: 'Logs', icon: <ScrollText size={18} /> },
  ];

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{ width: '28px', height: '28px', borderRadius: '8px', backgroundColor: '#a0522d', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: '900', fontSize: '14px', flexShrink: 0 }}>
          J
        </div>
        Agente Jordão
      </div>
      <nav className={styles.menu}>
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => 
              `${styles.link} ${isActive ? styles.linkActive : ''}`
            }
            end={item.path === '/'}
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
        <button onClick={onLogout} className={styles.logoutLink} style={{ background: 'none', border: 'none', width: '100%', textAlign: 'left' }}>
          <LogOut size={18} />
          <span>Sair do Painel</span>
        </button>
      </nav>
    </aside>
  );
};
