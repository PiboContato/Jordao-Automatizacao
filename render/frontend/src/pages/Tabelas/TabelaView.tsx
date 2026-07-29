import React, { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Search, Download, Database, ChevronDown } from 'lucide-react';
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

const customMappings: Record<string, string[]> = {
  '01': ['codigo', 'proprietario', 'endereco'],
  '02': ['contrato', 'imovel', 'locatario', 'valor'],
  '05': ['proprietario', 'forma'],
  '06': ['competencia', 'locatario', 'valor'],
  '07': ['competencia', 'taxa', 'valor', 'vencimento', 'pagamento'],
  '11': ['contrato', 'data', 'despesa', 'descricao', 'valor'],
  '12': ['nome', 'telefone', 'endereco'],
  '13': ['mes', 'ano', 'nome', 'pagamento', 'operacao', 'valor', 'tipo'],
  '14': ['mes', 'ano', 'me', 'contrato', 'historico', 'valor'],
  '15': ['tipo', 'nome', 'pessoa', 'valor', 'vencimento', 'pagamento']
};

const MobileRowCard: React.FC<{ row: any, colunas: string[], tabela?: string }> = ({ row, colunas, tabela }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  const colsWithoutExtracao = colunas.filter(c => c !== '__data_extracao');
  
  const getDisplayCols = () => {
    let reportKey = '';
    if (tabela) {
       const match = tabela.match(/\d{2}/);
       if (match) reportKey = match[0];
    }
    
    if (reportKey && customMappings[reportKey]) {
       const keywords = customMappings[reportKey];
       const foundCols = colsWithoutExtracao.filter(c => {
          const cLow = c.toLowerCase();
          return keywords.some(k => cLow.includes(k));
       });
       if (foundCols.length > 0) return new Set(foundCols);
    }
    
    // Fallback: Default original config
    const previewCols = colsWithoutExtracao.slice(0, 2);
    const dateCol = colsWithoutExtracao.find(c => ['mes_referencia', 'competencia', 'data', 'vencimento', 'inicio', 'fim'].some(k => c.toLowerCase().includes(k)));
    
    const displaySet = new Set([...previewCols]);
    if (dateCol) displaySet.add(dateCol);
    return displaySet;
  };

  const displayCols = getDisplayCols();

  return (
    <div className={styles.mobileCard}>
      <div className={styles.mobileHeader} onClick={() => setIsOpen(!isOpen)}>
        <div className={styles.mobileTitleBox}>
          {Array.from(displayCols).map(col => (
             <div key={col} className={styles.mobilePreviewLine}>
               <strong>{col === '__data_extracao' ? 'Data Extração' : col}:</strong> {formatarValor(col, row[col])}
             </div>
          ))}
        </div>
        <div className={`${styles.chevron} ${isOpen ? styles.open : ''}`}>
           <ChevronDown size={20} color="#64748b" />
        </div>
      </div>
      
      {isOpen && (
        <div className={styles.mobileBody}>
          {colunas.map(col => {
            if (displayCols.has(col)) return null; // já mostrou no preview (header)
            return (
              <div key={col} className={styles.mobileField}>
                <label>{col === '__data_extracao' ? 'Data Extração' : col}</label>
                <div>{formatarValor(col, row[col])}</div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

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

  // formatarValor moved outside component

  return (
    <div className={styles.container}>
      <div className="sticky-header">
        <Link to="/tabelas" className={styles.backBtn}>
          <ArrowLeft size={18} /> Voltar para Tabelas
        </Link>

        <div className={styles.headerBox} style={{ marginBottom: 0 }}>
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

            <div className={styles.mobileReportsCards}>
              {currentLines.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                  Nenhum registro encontrado.
                </div>
              ) : (
                currentLines.map((row, idx) => (
                  <MobileRowCard key={row.__id || idx} row={row} colunas={colunas} tabela={tabela} />
                ))
              )}
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
