import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Settings, BarChart3, Table2, ClipboardList, Database } from 'lucide-react';
import { useUsuario, temPermissao } from '../../context/UsuarioContext';
import styles from './Inicio.module.css';

export const Inicio: React.FC = () => {
  const navigate = useNavigate();
  const { usuario } = useUsuario();

  const shortcuts = [
    {
      icon: <Settings size={40} />,
      title: 'Automação',
      path: '/automacao',
      flag: 'acesso_automacao' as const,
    },
    {
      icon: <BarChart3 size={40} />,
      title: 'Dashboard',
      path: '/bi',
      flag: 'acesso_bi' as const,
    },
    {
      icon: <Table2 size={40} />,
      title: 'Banco de Dados',
      path: '/tabelas',
      flag: 'acesso_tabelas' as const,
    },
    {
      icon: <ClipboardList size={40} />,
      title: 'Auditoria',
      path: '/auditoria',
      flag: 'acesso_auditoria' as const,
    },
    {
      icon: <Database size={40} />,
      title: 'Backups',
      path: '/backups',
      flag: 'acesso_backups' as const,
    },
  ];

  const visiveis = shortcuts.filter((s) => temPermissao(usuario, s.flag));

  return (
    <div>
      <div className={`${styles.headerBox} sticky-header`} style={{ marginBottom: 0 }}>
        <h1 className={styles.title}>Bem Vindo à Jordão Imobiliária,</h1>
        <p className={styles.subtitle}>Selecione uma opção para começar</p>
      </div>

      <div className={styles.cardShortcutGrid}>
        {visiveis.map((shortcut, idx) => (
          <div
            key={idx}
            className={styles.shortcutCard}
            onClick={() => navigate(shortcut.path)}
          >
            <div className={styles.shortcutIcon}>{shortcut.icon}</div>
            <h3 className={styles.shortcutTitle}>{shortcut.title}</h3>
          </div>
        ))}
      </div>
    </div>
  );
};
