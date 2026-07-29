import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Home, 
  Settings, 
  BarChart3, 
  Table2, 
  ClipboardList, 
  Database, 
  ScrollText 
} from 'lucide-react';
import styles from './BottomNav.module.css';

export const BottomNav: React.FC = () => {
  const menuItems = [
    { path: '/', label: 'Início', icon: <Home size={20} /> },
    { path: '/automacao', label: 'Robô', icon: <Settings size={20} /> },
    { path: '/bi', label: 'BI', icon: <BarChart3 size={20} /> },
    { path: '/tabelas', label: 'Tabelas', icon: <Table2 size={20} /> },
    { path: '/auditoria', label: 'Audit', icon: <ClipboardList size={20} /> },
    { path: '/backups', label: 'Backups', icon: <Database size={20} /> },
    { path: '/logs', label: 'Logs', icon: <ScrollText size={20} /> },
  ];

  return (
    <nav className={styles.bottomNav}>
      {menuItems.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          className={({ isActive }) => 
            `${styles.item} ${isActive ? styles.itemActive : ''}`
          }
          end={item.path === '/'}
        >
          {item.icon}
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
};
