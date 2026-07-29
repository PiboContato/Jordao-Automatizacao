import React, { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Search, Download, Database } from 'lucide-react';
import { apiFetch } from '../../api/client';
import styles from './TabelaView.module.css';

interface ReportConfig {
  id: number;
  name: string;
  table: string;
  desc: string;
}

interface TableDataResponse {
  colunas: string[];
  linhas: any[];
  total: number;
}

export const TabelaView: React.FC = () => {
  const { tabela } = useParams<{ tabela: string }>();
  const [reportName, setReportName] = useState<string>('');
  
  const [colunas, setColunas] = useState<string[]>([]);
  const [linhas, setLinhas] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 50;

  useEffect(() => {
    if (tabela) {
      carregarMetadata();
      carregarDados();
    }
  }, [tabela]);

  const carregarMetadata = async () => {
    try {
      const res = await apiFetch<{ reports: ReportConfig[] }>('/api/relatorios/config');
      const r = res.reports?.find(x => x.table === tabela);
      if (r) {
        setReportName(r.name);
      } else {
        setReportName(tabela || 'Tabela Desconhecida');
      }
    } catch {
      setReportName(tabela || 'Tabela');
    }
  };

  const carregarDados = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<TableDataResponse>(`/api/supabase/dados?tabela=${tabela}`);
      
      // Filtra as colunas do sistema, focando nas colunas de negócio (chaves do json "dados")
      const cols = data.colunas.filter(c => !['__id', '__data_extracao', 'id'].includes(c));
      setColunas(['__data_extracao', ...cols]);
      setLinhas(data.linhas || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Filtro de busca na memória
  const linhasFiltradas = useMemo(() => {
    if (!searchTerm) return linhas;
    const lowerSearch = searchTerm.toLowerCase();
    return linhas.filter(row => {
      return colunas.some(col => {
        const val = row[col];
        if (val === null || val === undefined) return false;
        return String(val).toLowerCase().includes(lowerSearch);
      });
    });
  }, [linhas, searchTerm, colunas]);

  // Paginação
  const totalPages = Math.ceil(linhasFiltradas.length / itemsPerPage);
  const currentLines = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return linhasFiltradas.slice(start, start + itemsPerPage);
  }, [linhasFiltradas, currentPage]);

  // Reset page when search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  const exportarCSV = () => {
    if (linhasFiltradas.length === 0) return;
    
    // Header
    const csvRows = [];
    csvRows.push(colunas.join(';'));
    
    // Linhas
    for (const row of linhasFiltradas) {
      const vals = colunas.map(col => {
        let val = row[col];
        if (val === null || val === undefined) val = '';
        const strVal = String(val).replace(/"/g, '""');
        return `"${strVal}"`;
      });
      csvRows.push(vals.join(';'));
    }
    
    const blob = new Blob(["\uFEFF" + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${tabela || 'exportacao'}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const formatarValor = (col: string, val: any) => {
    if (val === null || val === undefined) return '-';
    if (col === '__data_extracao') {
      try {
        return new Date(val).toLocaleString('pt-BR');
      } catch {
        return val;
      }
    }
    if (typeof val === 'object') return JSON.stringify(val);
    return String(val);
  };

  return (
    <div className={styles.container}>
      <Link to="/tabelas" className={styles.backBtn}>
        <ArrowLeft size={18} /> Voltar para Tabelas
      </Link>

      <div className={styles.headerBox}>
        <div>
          <h2 className={styles.title}>
            <Database size={24} color="#3b82f6" />
            {reportName}
          </h2>
          <p className={styles.subtitle}>Base de dados completa extraída pelo robô da VM.</p>
        </div>
        <div className={styles.topActions}>
          <div className={styles.searchBox}>
            <Search size={18} className={styles.searchIcon} />
            <input 
              type="text" 
              className={styles.searchInput} 
              placeholder="Pesquisar registros..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <button className={`${styles.btn} ${styles.btnPrimary}`} onClick={exportarCSV}>
            <Download size={18} /> Exportar CSV
          </button>
        </div>
      </div>

      <div className={styles.tableCard}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
            <Database size={40} className="spinner" style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
            <p>Carregando registros do banco de dados...</p>
          </div>
        ) : (
          <>
            <div className={styles.tableContainer}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    {colunas.map(col => (
                      <th key={col}>{col === '__data_extracao' ? 'Data Extração' : col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {currentLines.length === 0 ? (
                    <tr>
                      <td colSpan={colunas.length} style={{ textAlign: 'center', padding: '2rem' }}>
                        Nenhum registro encontrado.
                      </td>
                    </tr>
                  ) : (
                    currentLines.map((row, idx) => (
                      <tr key={row.__id || idx}>
                        {colunas.map(col => (
                          <td key={col}>{formatarValor(col, row[col])}</td>
                        ))}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className={styles.pagination}>
              <div>
                Mostrando <strong>{linhasFiltradas.length === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1}</strong> até <strong>{Math.min(currentPage * itemsPerPage, linhasFiltradas.length)}</strong> de <strong>{linhasFiltradas.length}</strong> registros
              </div>
              <div className={styles.pageControls}>
                <button 
                  className={styles.pageBtn} 
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                >
                  Anterior
                </button>
                <span>Página {currentPage} de {totalPages || 1}</span>
                <button 
                  className={styles.pageBtn} 
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                >
                  Próxima
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
