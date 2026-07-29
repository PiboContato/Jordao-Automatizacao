import React, { useEffect, useState } from 'react';
import { apiFetch } from '../../api/client';
import { requestFirebaseNotificationPermission } from '../../firebase-config';
import { BellRing, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react';
import styles from './Notificacoes.module.css';

interface Regra {
  id: string;
  regra_id: string;
  ativo: boolean;
  descricao: string;
}

interface MetricaDescartes {
  relatorio: string;
  linhas_inseridas: number;
  linhas_descartadas: number;
}

export const Notificacoes: React.FC = () => {
  const [regras, setRegras] = useState<Regra[]>([]);
  const [metricas, setMetricas] = useState<MetricaDescartes[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubscribing, setIsSubscribing] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarDados = async () => {
    setIsLoading(true);
    try {
      const [regrasData, metricasData] = await Promise.all([
        apiFetch<Regra[]>('/api/notificacoes/config'),
        apiFetch<MetricaDescartes[]>('/api/notificacoes/metricas')
      ]);
      setRegras(regrasData || []);
      setMetricas(metricasData || []);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubscribe = async () => {
    setIsSubscribing(true);
    setMessage(null);
    try {
      const token = await requestFirebaseNotificationPermission();
      if (token) {
        // Salvar token no backend
        await apiFetch('/api/notificacoes/subscribe', {
          method: 'POST',
          json: { token, user_agent: navigator.userAgent }
        });
        setMessage({ type: 'success', text: 'Notificações ativadas com sucesso neste dispositivo!' });
      } else {
        setMessage({ type: 'error', text: 'Não foi possível gerar o token de notificação. Verifique a permissão do navegador.' });
      }
    } catch (error) {
      console.error(error);
      setMessage({ type: 'error', text: 'Erro ao assinar notificações.' });
    } finally {
      setIsSubscribing(false);
    }
  };

  const handleToggleRegra = async (regraId: string, currentValue: boolean) => {
    try {
      // Otimisticamente atualizar a UI
      setRegras(prev => prev.map(r => r.regra_id === regraId ? { ...r, ativo: !currentValue } : r));
      
      await apiFetch('/api/notificacoes/config', {
        method: 'POST',
        json: { regra_id: regraId, ativo: !currentValue }
      });
    } catch (error) {
      console.error('Erro ao atualizar regra:', error);
      // Reverter em caso de erro
      setRegras(prev => prev.map(r => r.regra_id === regraId ? { ...r, ativo: currentValue } : r));
    }
  };

  const totalDescartadas = metricas.reduce((acc, m) => acc + m.linhas_descartadas, 0);
  const totalInseridas = metricas.reduce((acc, m) => acc + m.linhas_inseridas, 0);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Indicadores e Notificações</h1>
          <p className={styles.subtitle}>Gerencie alertas em tempo real e perdas de dados (descartes).</p>
        </div>
        <button 
          className={styles.subscribeBtn} 
          onClick={handleSubscribe} 
          disabled={isSubscribing}
        >
          {isSubscribing ? <Loader2 className={styles.spinner} size={20} /> : <BellRing size={20} />}
          <span>Ativar Notificações</span>
        </button>
      </header>

      {message && (
        <div className={`${styles.message} ${styles[message.type]}`}>
          {message.text}
        </div>
      )}

      <div className={styles.contentGrid}>
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Regras de Alerta (Push)</h2>
          <div className={styles.regrasContainer}>
            {isLoading ? (
              <p>Carregando regras...</p>
            ) : regras.length === 0 ? (
              <p>Nenhuma regra configurada no banco de dados.</p>
            ) : (
              regras.map(regra => (
                <div key={regra.id} className={styles.regraCard}>
                  <div className={styles.regraInfo}>
                    <h3>{regra.descricao}</h3>
                    <p>ID Interno: <code>{regra.regra_id}</code></p>
                  </div>
                  <label className={styles.switch}>
                    <input 
                      type="checkbox" 
                      checked={regra.ativo} 
                      onChange={() => handleToggleRegra(regra.regra_id, regra.ativo)} 
                    />
                    <span className={styles.slider}></span>
                  </label>
                </div>
              ))
            )}
          </div>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Indicadores de Extração (Geral)</h2>
          <div className={styles.kpiGrid}>
            <div className={`${styles.kpiCard} ${styles.kpiSuccess}`}>
              <div className={styles.kpiHeader}>
                <CheckCircle size={24} />
                <span>Linhas Inseridas</span>
              </div>
              <div className={styles.kpiValue}>{totalInseridas}</div>
            </div>
            
            <div className={`${styles.kpiCard} ${styles.kpiWarning}`}>
              <div className={styles.kpiHeader}>
                <AlertTriangle size={24} />
                <span>Linhas Descartadas</span>
              </div>
              <div className={styles.kpiValue}>{totalDescartadas}</div>
              <div className={styles.kpiSubtitle}>
                ({totalInseridas > 0 ? ((totalDescartadas / (totalInseridas + totalDescartadas)) * 100).toFixed(1) : 0}% de perda)
              </div>
            </div>
          </div>
          
          <h3 className={styles.subheading}>Descartes por Relatório (Últimos dias)</h3>
          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Relatório</th>
                  <th style={{ textAlign: 'right' }}>Inseridas</th>
                  <th style={{ textAlign: 'right' }}>Descartadas</th>
                </tr>
              </thead>
              <tbody>
                {metricas.length === 0 ? (
                  <tr><td colSpan={3} style={{textAlign:'center'}}>Sem dados registrados</td></tr>
                ) : (
                  metricas.map((m, i) => (
                    <tr key={i}>
                      <td>{m.relatorio}</td>
                      <td style={{ textAlign: 'right', color: '#10b981' }}>{m.linhas_inseridas}</td>
                      <td style={{ textAlign: 'right', color: m.linhas_descartadas > 0 ? '#ef4444' : '#64748b' }}>
                        {m.linhas_descartadas}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};
