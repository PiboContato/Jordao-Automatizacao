import React, { useEffect, useState } from 'react';
import { Building2, FileText, ArrowDownRight, ArrowUpRight, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { apiFetch } from '../../api/client';
import styles from './BI.module.css';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

interface KPIs {
  total_imoveis: string | number;
  total_contratos: string | number;
  contas_receber: number;
  contas_pagar: number;
  total_execucoes: string | number;
  taxa_sucesso: string;
}

interface Execucao {
  id: number;
  status: string;
  mensagem: string;
  created_at?: string;
  iniciado_em?: string;
  data_extracao?: string;
}

export const BI: React.FC = () => {
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [execucoes, setExecucoes] = useState<Execucao[]>([]);

  useEffect(() => {
    carregarKpis();
    carregarExecucoes();
  }, []);

  const carregarKpis = async () => {
    try {
      const data = await apiFetch<KPIs>('/api/supabase/kpis');
      setKpis(data);
    } catch (err) {
      console.error(err);
    }
  };

  const carregarExecucoes = async () => {
    try {
      const data = await apiFetch<{ execucoes: Execucao[] }>('/api/supabase/execucoes');
      setExecucoes(data.execucoes || []);
    } catch (err) {
      console.error(err);
    }
  };

  const formatarMoeda = (val: number | undefined) => {
    if (val === undefined || val === null) return '-';
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
  };

  const formatarData = (dtStr: string | undefined) => {
    if (!dtStr) return '-';
    try {
      return new Date(dtStr).toLocaleString('pt-BR');
    } catch {
      return dtStr;
    }
  };

  const barChartData = {
    labels: ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho'],
    datasets: [
      {
        label: 'A Receber',
        data: [12000, 19000, 15000, 22000, 18000, 25000],
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
      },
      {
        label: 'A Pagar',
        data: [8000, 15000, 10000, 18000, 12000, 20000],
        backgroundColor: 'rgba(239, 68, 68, 0.8)',
      }
    ],
  };

  const barChartOptions = {
    responsive: true,
    plugins: {
      legend: { position: 'top' as const },
      title: { display: false }
    },
  };

  const doughnutData = {
    labels: ['Ativos', 'Inativos'],
    datasets: [
      {
        label: 'Contratos',
        data: [kpis?.total_contratos || 0, 5],
        backgroundColor: ['#10b981', '#f43f5e'],
      }
    ]
  };

  return (
    <div className={styles.container}>
      <div className={`${styles.headerBox} sticky-header`} style={{ marginBottom: 0 }}>
        <h2 className={styles.title}>Dashboard Analítico (BI)</h2>
        <p className={styles.subtitle}>Visão geral dos indicadores de desempenho da imobiliária.</p>
      </div>

      <div className={styles.kpiGrid}>
        <div className={styles.kpiCard}>
          <div className={`${styles.kpiIconWrapper} ${styles.blue}`}>
            <Building2 size={24} />
          </div>
          <div className={styles.kpiInfo}>
            <span className={styles.kpiLabel}>Total Imóveis</span>
            <span className={styles.kpiValue}>{kpis?.total_imoveis || '-'}</span>
          </div>
        </div>

        <div className={styles.kpiCard}>
          <div className={`${styles.kpiIconWrapper} ${styles.orange}`}>
            <FileText size={24} />
          </div>
          <div className={styles.kpiInfo}>
            <span className={styles.kpiLabel}>Total Contratos</span>
            <span className={styles.kpiValue}>{kpis?.total_contratos || '-'}</span>
          </div>
        </div>

        <div className={styles.kpiCard}>
          <div className={`${styles.kpiIconWrapper}`}>
            <ArrowDownRight size={24} />
          </div>
          <div className={styles.kpiInfo}>
            <span className={styles.kpiLabel}>A Receber (Geral)</span>
            <span className={styles.kpiValue}>{formatarMoeda(kpis?.contas_receber)}</span>
          </div>
        </div>

        <div className={styles.kpiCard}>
          <div className={`${styles.kpiIconWrapper} ${styles.red}`}>
            <ArrowUpRight size={24} />
          </div>
          <div className={styles.kpiInfo}>
            <span className={styles.kpiLabel}>A Pagar (Geral)</span>
            <span className={styles.kpiValue}>{formatarMoeda(kpis?.contas_pagar)}</span>
          </div>
        </div>
      </div>

      <div className={styles.chartsGrid}>
        <div className={styles.chartCard}>
          <h3 className={styles.chartTitle}>Projeção Financeira (Simulação)</h3>
          <Bar data={barChartData} options={barChartOptions} />
        </div>
        
        <div className={styles.chartCard}>
          <h3 className={styles.chartTitle}>Status de Contratos</h3>
          <Doughnut data={doughnutData} />
        </div>
      </div>

      <div className={styles.chartCard}>
        <h3 className={styles.chartTitle}>Últimas Execuções do Robô</h3>
        <div style={{ overflowX: 'auto' }}>
          <table className={styles.execucoesTable}>
            <thead>
              <tr>
                <th>Data / Hora</th>
                <th>Status</th>
                <th>Mensagem</th>
              </tr>
            </thead>
            <tbody>
              {execucoes.length === 0 ? (
                <tr>
                  <td colSpan={3} style={{ textAlign: 'center', color: '#888' }}>
                    Carregando execuções ou nenhuma encontrada...
                  </td>
                </tr>
              ) : (
                execucoes.slice(0, 10).map(ex => (
                  <tr key={ex.id}>
                    <td>{formatarData(ex.iniciado_em || ex.created_at || ex.data_extracao)}</td>
                    <td>
                      {ex.status === 'sucesso' && <span className={styles.statusSucesso}><CheckCircle2 size={16} /> Sucesso</span>}
                      {ex.status === 'falha' && <span className={styles.statusFalha}><XCircle size={16} /> Falha</span>}
                      {ex.status !== 'sucesso' && ex.status !== 'falha' && <span className={styles.statusPendente}><Clock size={16} /> Pendente</span>}
                    </td>
                    <td>{ex.mensagem || '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
