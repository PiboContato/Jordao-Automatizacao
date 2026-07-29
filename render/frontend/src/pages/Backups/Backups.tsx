import React, { useEffect, useState } from 'react';
import { DatabaseBackup, RotateCcw } from 'lucide-react';
import { apiFetch } from '../../api/client';
import { ConfirmModal } from '../../components/Modal/ConfirmModal';
import styles from './Backups.module.css';

interface BackupRecord {
  id: number;
  table_name: string;
  nome_amigavel: string;
  total_registros: number;
  created_at: string;
}

export const Backups: React.FC = () => {
  const [backups, setBackups] = useState<BackupRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [restoringId, setRestoringId] = useState<number | null>(null);
  
  const [confirmModal, setConfirmModal] = useState<{ isOpen: boolean; id: number | null }>({
    isOpen: false,
    id: null
  });

  useEffect(() => {
    carregarBackups();
  }, []);

  const carregarBackups = async () => {
    try {
      const data = await apiFetch<BackupRecord[]>('/api/backups');
      setBackups(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRestaurarClick = (id: number) => {
    setConfirmModal({ isOpen: true, id });
  };

  const confirmarRestauracao = async () => {
    const id = confirmModal.id;
    setConfirmModal({ isOpen: false, id: null });
    
    if (!id) return;
    
    setRestoringId(id);
    try {
      const res = await apiFetch<{ status: string; resultado?: any }>(`/api/backups/restaurar/${id}`, {
        method: 'POST'
      });
      alert(res.status || 'Backup restaurado com sucesso!');
      carregarBackups();
    } catch (err: any) {
      alert("Erro ao restaurar: " + (err.message || 'Falha na comunicação'));
    } finally {
      setRestoringId(null);
    }
  };

  const formatarData = (dtStr: string) => {
    try {
      return new Date(dtStr).toLocaleString('pt-BR');
    } catch {
      return dtStr;
    }
  };

  return (
    <div className={styles.container}>
      <div className={`${styles.headerBox} sticky-header`} style={{ marginBottom: 0 }}>
        <h2 className={styles.title}><DatabaseBackup size={24} color="#3b82f6" /> Gerenciamento de Backups</h2>
        <p className={styles.subtitle}>Consulte pontos de restauração gerados antes de toda nova extração da VM.</p>
      </div>

      <div className={styles.tableCard}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
            <DatabaseBackup size={40} className="spinner" style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
            <p>Carregando pontos de restauração...</p>
          </div>
        ) : backups.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
            Nenhum backup encontrado.
          </div>
        ) : (
          <>
            <div className={styles.tableContainer}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    <th>Data do Backup</th>
                    <th>Relatório Origem</th>
                    <th style={{ textAlign: 'center' }}>Total de Registros Salvos</th>
                    <th style={{ textAlign: 'right' }}>Ações de Restauração</th>
                  </tr>
                </thead>
                <tbody>
                  {backups.map((bkp) => (
                    <tr key={bkp.id}>
                      <td>{formatarData(bkp.created_at)}</td>
                      <td style={{ fontWeight: 500 }}>{bkp.nome_amigavel || bkp.table_name}</td>
                      <td style={{ textAlign: 'center' }}>{bkp.total_registros}</td>
                      <td style={{ textAlign: 'right' }}>
                        <button 
                          className={styles.btnAction}
                          onClick={() => handleRestaurarClick(bkp.id)}
                          disabled={restoringId === bkp.id}
                        >
                          <RotateCcw size={16} /> 
                          {restoringId === bkp.id ? 'Restaurando...' : 'Restaurar'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className={styles.mobileCards}>
              {backups.map((bkp) => (
                <div key={bkp.id} className={styles.mobileCard}>
                  <div className={styles.mobileRow}>
                    <span className={styles.mobileLabel}>Data:</span>
                    <span className={styles.mobileValue}>{formatarData(bkp.created_at)}</span>
                  </div>
                  <div className={styles.mobileRow}>
                    <span className={styles.mobileLabel}>Tabela:</span>
                    <span className={styles.mobileValue}>{bkp.nome_amigavel || bkp.table_name}</span>
                  </div>
                  <div className={styles.mobileRow}>
                    <span className={styles.mobileLabel}>Registros:</span>
                    <span className={styles.mobileValue}>{bkp.total_registros}</span>
                  </div>
                  <div className={styles.mobileActions}>
                    <button 
                      className={styles.btnAction}
                      onClick={() => handleRestaurarClick(bkp.id)}
                      disabled={restoringId === bkp.id}
                    >
                      <RotateCcw size={16} /> 
                      {restoringId === bkp.id ? 'Restaurando...' : 'Restaurar'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title="Restaurar Backup"
        message={`Atenção! Esta ação irá apagar os dados atuais da tabela e substituí-los pela versão salva no backup #${confirmModal.id}. Tem certeza que deseja continuar?`}
        onConfirm={confirmarRestauracao}
        onCancel={() => setConfirmModal({ isOpen: false, id: null })}
      />
    </div>
  );
};
