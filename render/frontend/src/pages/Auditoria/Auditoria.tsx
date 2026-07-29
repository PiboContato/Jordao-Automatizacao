import React, { useEffect, useState } from 'react';
import { History, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { apiFetch } from '../../api/client';
import styles from './Auditoria.module.css';

interface Execucao {
  id: number;
  status: string;
  mensagem: string;
  created_at?: string;
  iniciado_em?: string;
  data_extracao?: string;
}

export const Auditoria: React.FC = () => {
  const [execucoes, setExecucoes] = useState<Execucao[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    carregarAuditoria();
  }, []);

  const carregarAuditoria = async () => {
    try {
      const data = await apiFetch<{ execucoes: Execucao[] }>('/api/supabase/execucoes');
      setExecucoes(data.execucoes || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const formatarData = (dtStr: string | undefined) => {
    if (!dtStr) return '-';
    try {
      return new Date(dtStr).toLocaleString('pt-BR');
    } catch {
      return dtStr;
    }
  };

  const renderStatus = (status: string) => {
    if (status === 'sucesso') return <span className={`${styles.statusCell} ${styles.statusSucesso}`}><CheckCircle2 size={16} /> Sucesso</span>;
    if (status === 'falha') return <span className={`${styles.statusCell} ${styles.statusFalha}`}><XCircle size={16} /> Falha</span>;
    return <span className={`${styles.statusCell} ${styles.statusPendente}`}><Clock size={16} /> Pendente</span>;
  };

  return (
    <div className={styles.container}>
      <div className={styles.headerBox}>
        <h2 className={styles.title}><History size={24} color="#3b82f6" /> Auditoria Geral</h2>
        <p className={styles.subtitle}>Histórico completo de disparos remotos, erros e conclusões reportadas pelo robô da VM.</p>
      </div>

      <div className={styles.tableCard}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
            <History size={40} className="spinner" style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
            <p>Carregando histórico de auditoria...</p>
          </div>
        ) : execucoes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
            Nenhum registro de auditoria encontrado.
          </div>
        ) : (
          <>
            <div className={styles.tableContainer}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    <th style={{ width: '180px' }}>Data / Hora</th>
                    <th style={{ width: '120px' }}>Status</th>
                    <th>Mensagem Detalhada</th>
                  </tr>
                </thead>
                <tbody>
                  {execucoes.map((ex) => (
                    <tr key={ex.id}>
                      <td>{formatarData(ex.iniciado_em || ex.created_at || ex.data_extracao)}</td>
                      <td>{renderStatus(ex.status)}</td>
                      <td>{ex.mensagem || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className={styles.mobileCards}>
              {execucoes.map((ex) => (
                <div key={ex.id} className={styles.mobileCard}>
                  <div className={styles.mobileHeader}>
                    <span className={styles.mobileDate}>{formatarData(ex.iniciado_em || ex.created_at || ex.data_extracao)}</span>
                    {renderStatus(ex.status)}
                  </div>
                  <div className={styles.mobileMessage}>
                    <strong>Detalhe:</strong><br />
                    {ex.mensagem || '-'}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
