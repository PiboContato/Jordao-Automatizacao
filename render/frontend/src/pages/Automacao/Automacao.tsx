import React, { useState, useEffect, useRef } from 'react';
import { PlayCircle, Clock, StopCircle, RefreshCw, ChevronDown } from 'lucide-react';
import { apiFetch } from '../../api/client';
import { SchedulerModal } from './components/SchedulerModal';
import styles from './Automacao.module.css';

interface ReportConfig {
  id: number;
  name: string;
  table: string;
  desc: string;
}

interface CommandInfo {
  id?: number;
  status?: string;
  mensagem?: string;
}

interface LiveStatus {
  status: string; // e.g. '✅', '🔄', '❌', '🛑', '-'
  tempo: string;  // e.g. '15s', '-'
  startTime?: number; // timestamp
}

export const Automacao: React.FC = () => {
  const [reports, setReports] = useState<ReportConfig[]>([]);
  const [isSchedulerOpen, setIsSchedulerOpen] = useState(false);
  const [cmdBoxMsg, setCmdBoxMsg] = useState('');
  const [showAlertaVM, setShowAlertaVM] = useState(false);
  
  // Date states. Keyed by report ID.
  const [dates, setDates] = useState<Record<number, { inicio?: string; fim?: string; mes?: string; inicioMes?: string; fimMes?: string }>>({});
  const [masaInicio, setMasaInicio] = useState('');
  const [masaFim, setMasaFim] = useState('');

  // Live status tracking
  const [liveStatuses, setLiveStatuses] = useState<Record<number, LiveStatus>>({});
  
  // Polling interval ref
  const monitorRef = useRef<number | null>(null);
  const liveTimerRef = useRef<number | null>(null);

  useEffect(() => {
    carregarRelatorios();
    
    // Live timer updater for '🔄' status
    liveTimerRef.current = window.setInterval(() => {
      setLiveStatuses(prev => {
        const next = { ...prev };
        let changed = false;
        Object.keys(next).forEach(k => {
          const id = Number(k);
          if (next[id].status === '🔄' && next[id].startTime) {
            const elapsed = Math.floor((Date.now() - next[id].startTime!) / 1000);
            next[id] = { ...next[id], tempo: `${elapsed}s` };
            changed = true;
          }
        });
        return changed ? next : prev;
      });
    }, 1000);

    return () => {
      if (liveTimerRef.current) clearInterval(liveTimerRef.current);
      if (monitorRef.current) clearInterval(monitorRef.current);
    };
  }, []);

  const carregarRelatorios = async () => {
    try {
      const res = await apiFetch<{ reports: ReportConfig[] }>('/api/relatorios/config');
      setReports(res.reports || []);
      
      const initDates: Record<number, any> = {};
      const initStatus: Record<number, LiveStatus> = {};
      
      const now = new Date();
      const todayStr = now.toISOString().split('T')[0];
      const firstDayStr = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
      const lastDayStr = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0];
      const currentMonthStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

      (res.reports || []).forEach(r => {
        let inicio = '';
        let fim = '';
        let mes = '';
        let inicioMes = '';
        let fimMes = '';

        if ([1, 2, 4, 5, 8, 12].includes(r.id)) {
            inicio = todayStr;
        } else if ([3, 9, 10, 13, 15].includes(r.id)) {
            inicio = firstDayStr;
            fim = lastDayStr;
        } else if ([6, 11, 14].includes(r.id)) {
            mes = currentMonthStr;
        } else if (r.id === 7) {
            inicioMes = currentMonthStr;
            fimMes = currentMonthStr;
        }

        initDates[r.id] = { inicio, fim, mes, inicioMes, fimMes };
        initStatus[r.id] = { status: '-', tempo: '-' };
      });
      setDates(initDates);
      setLiveStatuses(initStatus);
    } catch (err) {
      console.error(err);
    }
  };

  const handleMasaSync = () => {
    if (!masaInicio || !masaFim) return;
    const [yearIni, monthIni] = masaInicio.split('-');
    const mesIniStr = `${yearIni}-${monthIni}`;
    const [yearFim, monthFim] = masaFim.split('-');
    const mesFimStr = `${yearFim}-${monthFim}`;

    setDates(prev => {
      const next = { ...prev };
      reports.forEach(r => {
        next[r.id] = {
          ...next[r.id],
          inicio: masaInicio,
          fim: masaFim,
          mes: mesIniStr,
          inicioMes: mesIniStr,
          fimMes: mesFimStr
        };
      });
      return next;
    });
  };

  const obterDatasParaEnvio = (id: number) => {
    const d = dates[id] || {};
    let data_inicio = "";
    let data_fim = "";
    
    if ([6, 11, 14].includes(id)) {
      if (d.mes) {
        const [year, month] = d.mes.split('-');
        const lastDay = new Date(Number(year), Number(month), 0).getDate();
        data_inicio = `${year}-${month}-01`;
        data_fim = `${year}-${month}-${String(lastDay).padStart(2, '0')}`;
      }
    } else if (id === 7) {
      if (d.inicioMes) data_inicio = d.inicioMes;
      if (d.fimMes) data_fim = d.fimMes;
      else if (data_inicio) data_fim = data_inicio;
    } else {
      if (d.inicio) data_inicio = d.inicio;
      if (d.fim) data_fim = d.fim;
    }
    
    return { report_id: id, data_inicio, data_fim };
  };

  const enviarComandoRemoto = async (relatoriosArray: any[]) => {
    setCmdBoxMsg('🚀 Enviando comando para a VM...');
    try {
      const res = await apiFetch<{ comando?: CommandInfo, error?: string }>('/api/remoto/disparar', {
        method: 'POST',
        json: { relatorios: relatoriosArray }
      });
      setCmdBoxMsg('✅ Comando recebido! Aguardando a VM iniciar o robô...');
      if (res.comando?.id) monitorarComando(res.comando.id);
    } catch (err: any) {
      setCmdBoxMsg('❌ Erro de conexão ao enviar comando.');
    }
  };

  const iniciarTimer = (id: number) => {
    setLiveStatuses(prev => ({
      ...prev,
      [id]: { status: '🔄', tempo: '0s', startTime: Date.now() }
    }));
  };

  const pararTimer = (statusFinal: string) => {
    setLiveStatuses(prev => {
      const next = { ...prev };
      Object.keys(next).forEach(k => {
        const id = Number(k);
        if (next[id].status === '🔄') {
          next[id] = { ...next[id], status: statusFinal };
        }
      });
      return next;
    });
  };

  const iniciarExtracaoRemota = (id: number) => {
    iniciarTimer(id);
    enviarComandoRemoto([obterDatasParaEnvio(id)]);
  };

  const baixarTudoRemoto = () => {
    const arr = reports.map(r => {
      iniciarTimer(r.id);
      return obterDatasParaEnvio(r.id);
    });
    enviarComandoRemoto(arr);
  };

  const cancelarExecucaoRemota = async () => {
    setCmdBoxMsg('🛑 Enviando solicitação de cancelamento para a VM...');
    try {
      const res = await apiFetch<{ comando?: CommandInfo, error?: string }>('/api/remoto/cancelar', {
        method: 'POST'
      });
      setCmdBoxMsg('🛑 Cancelamento enviado com sucesso! Aguardando a VM fechar a sessão...');
      pararTimer('🛑');
      if (res.comando?.id) monitorarComando(res.comando.id);
    } catch (err) {
      alert("Erro de conexão ao cancelar.");
    }
  };

  const monitorarComando = (cmdId: number) => {
    if (monitorRef.current) clearInterval(monitorRef.current);
    
    monitorRef.current = window.setInterval(async () => {
      try {
        const res = await apiFetch<{ comando: CommandInfo, vm_sem_responder: boolean }>(`/api/remoto/status/${cmdId}`);
        const cmd = res.comando;
        setShowAlertaVM(!!res.vm_sem_responder);
        
        if (cmd.status === 'em_execucao') {
          setCmdBoxMsg(`🔄 Robô executando na VM em tempo real... ${cmd.mensagem || ''}`);
        } else if (cmd.status === 'concluido') {
          setCmdBoxMsg('✅ Execução concluída com sucesso na VM!');
          setShowAlertaVM(false);
          pararTimer('✅');
          clearInterval(monitorRef.current!);
          setTimeout(() => setCmdBoxMsg(''), 5000);
        } else if (cmd.status === 'falha') {
          setCmdBoxMsg(`❌ ${cmd.mensagem || 'Falha ou cancelamento na VM'}`);
          pararTimer('❌');
          clearInterval(monitorRef.current!);
        }
      } catch (err) {
        console.error(err);
      }
    }, 3000);
  };

  const handleDateChange = (id: number, field: string, val: string) => {
    setDates(prev => ({
      ...prev,
      [id]: { ...prev[id], [field]: val }
    }));
  };

  // Renders the input block dynamically based on report id
  const renderInputs = (r: ReportConfig) => {
    const d = dates[r.id] || {};
    if ([1, 2, 4, 5, 8, 12].includes(r.id)) {
      return (
        <div className={styles.inputGroup} style={{ width: '100%', maxWidth: '280px' }}>
          <label>Data Base (Única)</label>
          <input type="date" className={styles.dateInput} value={d.inicio || ''} onChange={e => handleDateChange(r.id, 'inicio', e.target.value)} style={{ width: '100%' }} />
        </div>
      );
    } else if ([6, 11, 14].includes(r.id)) {
      return (
        <div className={styles.inputGroup}>
          <label>Mês Referência</label>
          <input type="month" className={styles.dateInput} value={d.mes || ''} onChange={e => handleDateChange(r.id, 'mes', e.target.value)} />
        </div>
      );
    } else if (r.id === 7) {
      return (
        <div className={styles.dateRow}>
          <div className={styles.inputGroup}>
            <label>Mês Inicial</label>
            <input type="month" className={styles.dateInput} value={d.inicioMes || ''} onChange={e => handleDateChange(r.id, 'inicioMes', e.target.value)} />
          </div>
          <div className={styles.inputGroup}>
            <label>Mês Final</label>
            <input type="month" className={styles.dateInput} value={d.fimMes || ''} onChange={e => handleDateChange(r.id, 'fimMes', e.target.value)} />
          </div>
        </div>
      );
    } else {
      return (
        <div className={styles.dateRow}>
          <div className={styles.inputGroup}>
            <label>Data Início</label>
            <input type="date" className={styles.dateInput} value={d.inicio || ''} onChange={e => handleDateChange(r.id, 'inicio', e.target.value)} />
          </div>
          <div className={styles.inputGroup}>
            <label>Data Fim</label>
            <input type="date" className={styles.dateInput} value={d.fim || ''} onChange={e => handleDateChange(r.id, 'fim', e.target.value)} />
          </div>
        </div>
      );
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.headerBox}>
        <div>
          <h2 className={styles.title}>Automação RPA (VM Remota)</h2>
          <p className={styles.subtitle}>Gerencie extrações via robô, defina agendamentos ou dispare em lote remotamente.</p>
        </div>
        <div className={styles.topActions}>
          <button className={`${styles.btn} ${styles.btnPrimary}`} onClick={baixarTudoRemoto}>
            <PlayCircle size={18} /> Iniciar Extração Completa
          </button>
          <button className={`${styles.btn} ${styles.btnDanger}`} onClick={cancelarExecucaoRemota}>
            <StopCircle size={18} /> Interromper Robô
          </button>
          <button className={`${styles.btn} ${styles.btnWarning}`} onClick={() => setIsSchedulerOpen(true)}>
            <Clock size={18} /> Agendador
          </button>
        </div>
      </div>

      {showAlertaVM && (
        <div className={styles.alertBanner}>
          ⚠️ Atenção: A VM parece não estar respondendo. O robô pode estar travado ou a VM desligada.
        </div>
      )}

      {cmdBoxMsg && (
        <div className={styles.statusComandoBox}>
          {cmdBoxMsg}
        </div>
      )}

      <div className={styles.viewCard}>
        <div className={styles.syncMasaGroup}>
          <div className={styles.syncMasaLabel}>Período Único para Lote (Massa):</div>
          <input type="date" className={styles.dateInput} value={masaInicio} onChange={e => setMasaInicio(e.target.value)} placeholder="Início" />
          <input type="date" className={styles.dateInput} value={masaFim} onChange={e => setMasaFim(e.target.value)} placeholder="Fim" />
          <button className={`${styles.btn} ${styles.btnSecondary}`} onClick={handleMasaSync}>
            <RefreshCw size={16} /> Sincronizar Todos
          </button>
        </div>

        {/* Desktop Table */}
        <div className={styles.reportsTableContainer}>
          <table className={styles.reportsTable}>
            <thead>
              <tr>
                <th>Nome do Relatório</th>
                <th>Parâmetros de Data</th>
                <th style={{ width: '180px' }}>Ação</th>
                <th style={{ width: '80px', textAlign: 'center' }}>Status</th>
                <th style={{ width: '80px', textAlign: 'center' }}>Tempo</th>
              </tr>
            </thead>
            <tbody>
              {reports.map(r => (
                <tr key={r.id}>
                  <td className={styles.reportTitleCell}>
                    {r.name}
                    <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 400 }}>{r.desc}</div>
                  </td>
                  <td>{renderInputs(r)}</td>
                  <td>
                    <button className={`${styles.btn} ${styles.btnSecondary}`} style={{ width: '100%', justifyContent: 'center' }} onClick={() => iniciarExtracaoRemota(r.id)}>
                      🚀 Extrair
                    </button>
                  </td>
                  <td className={styles.statusIcon}>{liveStatuses[r.id]?.status}</td>
                  <td className={styles.tempoBadge}>{liveStatuses[r.id]?.tempo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile Accordion Cards */}
        <div className={styles.mobileReportsCards}>
          {reports.map(r => (
            <MobileReportCard 
              key={r.id} 
              report={r} 
              liveStatus={liveStatuses[r.id]} 
              renderInputs={() => renderInputs(r)}
              onExtrair={() => iniciarExtracaoRemota(r.id)}
            />
          ))}
        </div>
      </div>

      <SchedulerModal isOpen={isSchedulerOpen} onClose={() => setIsSchedulerOpen(false)} />
    </div>
  );
};

const MobileReportCard = ({ report, liveStatus, renderInputs, onExtrair }: any) => {
  const [open, setOpen] = useState(false);
  
  return (
    <div className={styles.mobileCard}>
      <div className={styles.mobileHeader} onClick={() => setOpen(!open)}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className={styles.statusIcon} style={{ fontSize: '1rem' }}>{liveStatus?.status}</div>
          <div className={styles.mobileTitleBox}>
            <div className={styles.mobileTitle}>{report.name}</div>
          </div>
        </div>
        <div className={styles.mobileMeta}>
          <span className={styles.tempoBadge} style={{ fontSize: '0.8rem' }}>{liveStatus?.tempo}</span>
          <ChevronDown size={18} className={`${styles.chevron} ${open ? styles.open : ''}`} />
        </div>
      </div>
      {open && (
        <div className={styles.mobileBody}>
          <div className={styles.mobileDesc} style={{ marginBottom: '15px' }}>{report.desc}</div>
          <div style={{ marginBottom: '15px' }}>
            {renderInputs()}
          </div>
          <button className={`${styles.btn} ${styles.btnSecondary}`} style={{ width: '100%', justifyContent: 'center' }} onClick={onExtrair}>
            🚀 Extrair na VM
          </button>
        </div>
      )}
    </div>
  );
};
