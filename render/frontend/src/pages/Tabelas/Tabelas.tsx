import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Database, ArrowRight } from 'lucide-react';
import { apiFetch } from '../../api/client';
import styles from './Tabelas.module.css';

interface ReportConfig {
  id: number;
  name: string;
  table: string;
  desc: string;
}

export const Tabelas: React.FC = () => {
  const [reports, setReports] = useState<ReportConfig[]>([]);

  useEffect(() => {
    carregarRelatorios();
  }, []);

  const carregarRelatorios = async () => {
    try {
      const res = await apiFetch<{ reports: ReportConfig[] }>('/api/relatorios/config');
      setReports(res.reports || []);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.headerBox}>
        <h2 className={styles.title}>Visualizador de Tabelas Supabase</h2>
        <p className={styles.subtitle}>
          Selecione uma tabela abaixo para consultar e baixar o histórico de extrações gravadas no banco de dados em nuvem.
        </p>
      </div>

      <div className={styles.tabelasGrid}>
        {reports.map((r) => (
          <Link key={r.id} to={`/tabelas/${r.table}`} className={styles.tabelaCard}>
            <div>
              <div className={styles.cardHeader}>
                <div className={styles.iconWrapper}>
                  <Database size={20} />
                </div>
                <div className={styles.cardTitle}>{r.name}</div>
              </div>
              <div className={styles.cardDesc}>{r.desc}</div>
            </div>
            <div className={styles.cardFooter}>
              <span>Acessar Registros</span>
              <ArrowRight size={16} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
};
