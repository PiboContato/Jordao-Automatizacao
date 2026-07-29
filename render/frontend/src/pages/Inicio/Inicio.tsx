import React from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './Inicio.module.css';

export const Inicio: React.FC = () => {
  const navigate = useNavigate();

  const shortcuts = [
    {
      icon: '⚙️',
      title: 'Controle de Automação',
      desc: 'Acione extrações manuais, defina períodos e acompanhe a fila de relatórios e os logs em tempo real.',
      path: '/automacao'
    },
    {
      icon: '📊',
      title: 'Dashboard Analítico (BI)',
      desc: 'Visualize indicadores gráficos, faturamentos, totais de contratos e distribuição de imóveis.',
      path: '/bi'
    },
    {
      icon: '🗂️',
      title: 'Visualizador de Tabelas',
      desc: 'Acesse os dados brutos de cada um dos 12 relatórios extraídos, com paginação e busca local.',
      path: '/tabelas'
    },
    {
      icon: '📋',
      title: 'Histórico de Auditoria',
      desc: 'Consulte os relatórios gerados por data, tempos de execução de cada tarefa e tamanho das tabelas.',
      path: '/auditoria'
    },
    {
      icon: '💾',
      title: 'Gestão de Backups',
      desc: 'Visualize pontos de backup salvos no Supabase e restaure tabelas específicas com um clique.',
      path: '/backups'
    }
  ];

  return (
    <div>
      <div className={styles.headerBox}>
        <h1 className={styles.title}>Painel de Controle Jordão</h1>
        <p className={styles.subtitle}>Bem-vindo! Selecione uma opção para começar</p>
      </div>

      <div className={styles.cardShortcutGrid}>
        {shortcuts.map((shortcut, idx) => (
          <div 
            key={idx} 
            className={styles.shortcutCard} 
            onClick={() => navigate(shortcut.path)}
          >
            <div className={styles.shortcutIcon}>{shortcut.icon}</div>
            <h3 className={styles.shortcutTitle}>{shortcut.title}</h3>
            <p className={styles.shortcutDesc}>{shortcut.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
