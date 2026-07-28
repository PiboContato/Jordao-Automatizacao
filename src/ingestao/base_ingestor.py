from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Any
import math
import json
import re
import unicodedata

import pandas as pd
from src.supabase_client import get_supabase
from src.logger import logger


TABELA_BACKUPS = "backups_execucoes"
RETENCAO_BACKUPS_DIAS = 30
SNAPSHOT_REPORTS = {1, 2, 4, 5, 12}


def _normalizar_texto(texto: str) -> str:
    """Normaliza texto para comparação: lowercase, remove acentos e espaços extras.

    Exemplos:
        "Mes / Ano" → "mes/ano"
        "Vencimento" → "vencimento"
        "Mês/Ano" → "mes/ano"
        "Pagamento" → "pagamento"
    """
    texto = str(texto).lower().strip()
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(sem_acentos.split())


def _limpar_valor(valor):
    """Substitui NaN, inf e -inf por None para serialização JSON."""
    if isinstance(valor, float) and (math.isnan(valor) or math.isinf(valor)):
        return None
    return valor


def _limpar_registros(registros: list[dict]) -> list[dict]:
    """Limpa todos os valores problemáticos nos registros."""
    return [
        {k: _limpar_valor(v) for k, v in reg.items()}
        for reg in registros
    ]


def _limpar_backups_antigos_supabase() -> None:
    """Remove backups com mais de RETENCAO_BACKUPS_DIAS dias da tabela backups_execucoes."""
    try:
        supabase = get_supabase()
        data_limite = (datetime.now() - timedelta(days=RETENCAO_BACKUPS_DIAS)).isoformat()
        resp = (
            supabase.table(TABELA_BACKUPS)
            .delete()
            .lt("created_at", data_limite)
            .execute()
        )
        if hasattr(resp, 'count') and resp.count and resp.count > 0:
            logger.info(f"Backups antigos removidos do Supabase: {resp.count}")
    except Exception as e:
        logger.warning(f"Falha ao limpar backups antigos do Supabase: {e}")


def restaurar_backup_por_id(backup_id: int) -> dict:
    """Restaura uma tabela do Supabase a partir do ID na tabela backups_execucoes."""
    supabase = get_supabase()
    resp = (
        supabase.table(TABELA_BACKUPS)
        .select("id, table_name, dados, total_registros, created_at")
        .eq("id", backup_id)
        .execute()
    )

    if not resp.data:
        raise ValueError(f"Backup ID {backup_id} não encontrado.")

    backup = resp.data[0]
    table_name = backup["table_name"]
    dados = backup.get("dados") or []
    total = backup.get("total_registros") or len(dados)

    # 1. Limpa dados atuais da tabela de destino
    supabase.table(table_name).delete().gte("id", 0).execute()

    # 2. Re-insere os dados do backup em lotes de 100
    lote = []
    inseridos = 0
    for reg in dados:
        item = {
            "dados": reg.get("dados", {}),
            "data_extracao": reg.get("data_extracao", ""),
        }
        lote.append(item)
        if len(lote) >= 100:
            supabase.table(table_name).insert(lote).execute()
            inseridos += len(lote)
            lote = []

    if lote:
        supabase.table(table_name).insert(lote).execute()
        inseridos += len(lote)

    logger.info(f"Restauração do backup ID {backup_id} ({table_name}) concluída com sucesso: {inseridos} registros.")
    return {
        "table_name": table_name,
        "total_restaurado": inseridos,
        "backup_id": backup_id,
        "created_at": backup["created_at"]
    }


class BaseIngestor:
    report_id: int = 0
    table_name: str = ""
    min_colunas: int = 3

    def _obter_contagem_banco(self) -> int:
        """Retorna o número atual de registros na tabela no Supabase."""
        try:
            supabase = get_supabase()
            resp = supabase.table(self.table_name).select("id", count="exact").limit(1).execute()
            return resp.count if resp.count is not None else 0
        except Exception as e:
            logger.warning(f"Falha ao contar registros em {self.table_name}: {e}")
            return -1

    def _backup_antes_deletar(self) -> bool:
        """Exporta todos os registros atuais da tabela para a tabela backups_execucoes no Supabase.

        Retorna True se o backup foi criado com sucesso, False se falhar.
        """
        try:
            _limpar_backups_antigos_supabase()

            supabase = get_supabase()
            todos_registros = []
            limit = 1000
            offset = 0
            while True:
                resp = (
                    supabase.table(self.table_name)
                    .select("id, dados, data_extracao")
                    .range(offset, offset + limit - 1)
                    .execute()
                )
                if not resp.data:
                    break
                todos_registros.extend(resp.data)
                if len(resp.data) < limit:
                    break
                offset += limit

            if not todos_registros:
                logger.info(f"Tabela {self.table_name} vazia — backup ignorado")
                return False

            supabase.table(TABELA_BACKUPS).insert({
                "table_name": self.table_name,
                "dados": todos_registros,
                "total_registros": len(todos_registros),
            }).execute()

            logger.info(
                f"Backup criado no Supabase: {self.table_name} "
                f"({len(todos_registros)} registros)"
            )
            return True

        except Exception as e:
            logger.error(f"Falha ao criar backup de {self.table_name}: {e}")
            return False

    def _validar_colunas(self, df: pd.DataFrame) -> None:
        """Verifica se o DataFrame tem colunas suficientes.

        Se o site mudar a estrutura do relatório, a quantidade de colunas
        muda e essa validação detecta antes que dados errados entrem no banco.
        """
        if len(df.columns) < self.min_colunas:
            msg = (
                f"DataFrame para {self.table_name} tem apenas {len(df.columns)} coluna(s), "
                f"esperado no mínimo {self.min_colunas}. "
                f"Colunas encontradas: {list(df.columns)}"
            )
            logger.error(msg)
            raise ValueError(msg)

    def _verificar_seguranca_antes_deletar(
        self, registros_novos: list[dict]
    ) -> None:
        """Verificações de segurança antes de deletar dados existentes.

        1. Contagem mínima: aborta se novos registros < 10% do banco
        2. Backup: salva dados atuais antes de deletar
        """
        contagem_banco = self._obter_contagem_banco()

        if contagem_banco == -1:
            logger.warning(
                f"Não foi possível contar registros em {self.table_name}. "
                "Prosseguindo com cautela..."
            )
            self._backup_antes_deletar()
            return

        if contagem_banco == 0:
            logger.info(f"Tabela {self.table_name} vazia — sem dados para backup")
            return

        n_novos = len(registros_novos)
        if n_novos == 0:
            msg = (
                f"ABORTANDO: {self.table_name} tem {contagem_banco} registros "
                f"no banco mas o Excel novo tem 0 registros válidos. "
                "Nenhum dado será apagado."
            )
            logger.error(msg)
            raise RuntimeError(msg)

        if self.report_id in SNAPSHOT_REPORTS:
            ratio = n_novos / contagem_banco if contagem_banco > 0 else 1
            if ratio < 0.3:
                msg = (
                    f"ABORTANDO: {self.table_name} (snapshot) tem {contagem_banco} "
                    f"registros no banco mas o Excel novo tem apenas {n_novos} "
                    f"({ratio:.0%}). Possível extração incorreta. "
                    "Nenhum dado será apagado."
                )
                logger.error(msg)
                raise RuntimeError(msg)

        self._backup_antes_deletar()

    def limpar_tabela(self) -> None:
        """Remove todos os registros da tabela antes de inserir dados novos.

        Evita duplicatas entre execuções diárias que extraem períodos sobrepostos
        (ex: últimos 30 dias). A tabela fica limpa a cada execução bem-sucedida.
        """
        try:
            supabase = get_supabase()
            resp = (
                supabase.table(self.table_name)
                .delete()
                .gte("id", 0)
                .execute()
            )
            logger.info(f"Tabela {self.table_name} limpa antes de nova ingestão")
        except Exception as e:
            logger.warning(f"Falha ao limpar tabela {self.table_name}: {e}")

    @staticmethod
    def _extrair_meses_do_nome(caminho: Path) -> list[str]:
        """Extrai a lista de meses (MM/YYYY) do nome do arquivo.

        Reconhece padrões como:
        - '... 2026_02_01 a 2026_02_28.xlsx' → ['02/2026']
        - '... 2026_06_01 a 2026_07_31.xlsx' → ['06/2026', '07/2026']
        - '... 2026_07_01.xlsx'               → ['07/2026']
        """
        nome = caminho.stem
        padrao_range = re.search(r'(\d{4})_(\d{2})_\d{2}\s*a\s*(\d{4})_(\d{2})_\d{2}', nome)
        if padrao_range:
            ano_ini, mes_ini = int(padrao_range.group(1)), int(padrao_range.group(2))
            ano_fim, mes_fim = int(padrao_range.group(3)), int(padrao_range.group(4))
        else:
            padrao_unico = re.search(r'(\d{4})_(\d{2})_\d{2}', nome)
            if padrao_unico:
                ano_ini = mes_ini = ano_fim = mes_fim = None
                ano_ini = int(padrao_unico.group(1))
                mes_ini = int(padrao_unico.group(2))
                ano_fim, mes_fim = ano_ini, mes_ini
            else:
                return []

        meses = []
        ano, mes = ano_ini, mes_ini
        while (ano < ano_fim) or (ano == ano_fim and mes <= mes_fim):
            meses.append(f"{mes:02d}/{ano}")
            mes += 1
            if mes > 12:
                mes = 1
                ano += 1
        return meses

    def limpar_periodo(self, df: pd.DataFrame, meses_alvo: list[str] | None = None) -> None:
        """Limpa apenas os meses/anos do período-alvo (extraído do nome do arquivo).

        Se meses_alvo for fornecido, limpa APENAS esses meses,
        evitando deletar dados de meses adjacentes que apareçam incidentalmente nos dados.
        Se não for fornecido, usa o comportamento anterior (extrair meses dos dados).
        """
        if self.report_id in SNAPSHOT_REPORTS:
            logger.info(f"Tabela {self.table_name} é um snapshot (Relatório Estático). Limpando dados antigos...")
            self.limpar_tabela()
            return

        padroes_data = ['data', 'date', 'pagamento', 'vencimento', 'mes/ano', 'mesano', 'periodo', 'competencia', 'competência']
        colunas_data = [c for c in df.columns if any(p in _normalizar_texto(c) for p in padroes_data)]
        if not colunas_data:
            logger.info(f"Tabela {self.table_name} identificada como snapshot por ausência de datas. Limpando dados antigos...")
            self.limpar_tabela()
            return

        cols_pag = [c for c in colunas_data if 'pagamento' in _normalizar_texto(c)]
        cols_venc = [c for c in colunas_data if 'vencimento' in _normalizar_texto(c)]
        cols_mesano = [c for c in colunas_data if 'mes/ano' in _normalizar_texto(c) or 'mesano' in _normalizar_texto(c) or 'periodo' in _normalizar_texto(c)]
        cols_despesa = [c for c in colunas_data if 'despesa' in _normalizar_texto(c)]
        cols_comp = [c for c in colunas_data if 'compet' in _normalizar_texto(c)]

        if 'relatorio_15' in self.table_name and cols_venc:
            col_data = cols_venc[0]
        elif 'relatorio_13' in self.table_name and cols_pag:
            col_data = cols_pag[0]
        elif 'relatorio_11' in self.table_name and cols_despesa:
            col_data = cols_despesa[0]
        elif 'relatorio_07' in self.table_name and cols_comp:
            col_data = cols_comp[0]
        elif 'relatorio_07' in self.table_name and cols_pag:
            col_data = cols_pag[0]
        elif 'relatorio_06' in self.table_name and cols_comp:
            col_data = cols_comp[0]
        elif 'relatorio_14' in self.table_name and cols_mesano:
            col_data = cols_mesano[0]
        elif cols_comp:
            col_data = cols_comp[0]
        elif cols_pag:
            col_data = cols_pag[0]
        elif cols_venc:
            col_data = cols_venc[0]
        else:
            col_data = colunas_data[0]

        if not meses_alvo:
            meses_alvo = self._extrair_meses_dos_dados(df, col_data)

        try:
            supabase = get_supabase()
            for ma in meses_alvo:
                logger.info(f"Limpando registros do período {ma} na tabela {self.table_name} (coluna {col_data})...")
                supabase.table(self.table_name).delete().like("dados->>" + col_data, f"%{ma}").execute()
        except Exception as e:
            logger.error(f"Erro ao limpar período específico na tabela {self.table_name}: {e}. A ingestão será abortada.")
            raise RuntimeError(f"Falha na limpeza de período: {e}")

    @staticmethod
    def _extrair_meses_dos_dados(df: pd.DataFrame, col_data: str) -> list[str]:
        """Fallback: extrai meses únicos dos dados (comportamento original)."""
        datas_convertidas = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce').dropna()
        if datas_convertidas.empty:
            logger.error(f"Sem datas válidas na coluna {col_data}. Abortando para evitar exclusão acidental do banco.")
            raise RuntimeError(f"Coluna {col_data} não possui datas válidas.")

        datas_validas = datas_convertidas[(datas_convertidas.dt.year >= 2000) & (datas_convertidas.dt.year <= 2100)]
        if datas_validas.empty:
            logger.warning(f"Nenhuma data válida entre os anos 2000 e 2100 encontrada em {col_data}. Pulando limpeza por período.")
            return []

        return sorted(set(datas_validas.dt.strftime('%m/%Y').tolist()))

    def ler_excel(self, caminho: Path) -> pd.DataFrame:
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
        df = pd.read_excel(caminho, engine="openpyxl")
        logger.info(f"Excel lido: {caminho.name} — {len(df)} linhas, {len(df.columns)} colunas")
        return df

    def validar_linhas(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            logger.warning(f"DataFrame vazio para {self.table_name}")
            return df

        if self.report_id in SNAPSHOT_REPORTS:
            return df

        padroes_data = ['data', 'date', 'pagamento', 'vencimento', 'mes/ano', 'mesano', 'periodo', 'competencia', 'competência']
        colunas_data = [c for c in df.columns if any(p in _normalizar_texto(c) for p in padroes_data)]
        if colunas_data:
            cols_pag = [c for c in colunas_data if 'pagamento' in _normalizar_texto(c)]
            cols_venc = [c for c in colunas_data if 'vencimento' in _normalizar_texto(c)]
            cols_mesano = [c for c in colunas_data if 'mes/ano' in _normalizar_texto(c) or 'mesano' in _normalizar_texto(c) or 'periodo' in _normalizar_texto(c)]
            cols_despesa = [c for c in colunas_data if 'despesa' in _normalizar_texto(c)]
            cols_comp = [c for c in colunas_data if 'compet' in _normalizar_texto(c)]

            col_data = None
            if 'relatorio_15' in self.table_name and cols_venc:
                col_data = cols_venc[0]
            elif 'relatorio_13' in self.table_name and cols_pag:
                col_data = cols_pag[0]
            elif 'relatorio_11' in self.table_name and cols_despesa:
                col_data = cols_despesa[0]
            elif 'relatorio_07' in self.table_name and cols_comp:
                col_data = cols_comp[0]
            elif 'relatorio_07' in self.table_name and cols_pag:
                col_data = cols_pag[0]
            elif 'relatorio_06' in self.table_name and cols_comp:
                col_data = cols_comp[0]
            elif 'relatorio_14' in self.table_name and cols_mesano:
                col_data = cols_mesano[0]
            elif cols_pag:
                col_data = cols_pag[0]
            elif cols_venc:
                col_data = cols_venc[0]
            else:
                col_data = colunas_data[0]

            if col_data:
                df_filtrado = df.dropna(subset=[col_data])
                df_filtrado = df_filtrado[df_filtrado[col_data].astype(str).str.strip() != '']
                df_filtrado = df_filtrado[df_filtrado[col_data].astype(str).str.strip().str.lower() != 'nan']
                df_filtrado = df_filtrado[df_filtrado[col_data].astype(str).str.strip().str.lower() != 'nat']

                linhas_removidas = len(df) - len(df_filtrado)
                if linhas_removidas > 0:
                    logger.info(f"Removidas {linhas_removidas} linhas inválidas/totais (sem data em {col_data}) na tabela {self.table_name}")
                return df_filtrado

        return df

    def df_para_registros(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        records = df.to_dict(orient="records")
        records = _limpar_registros(records)
        logger.info(f"{len(records)} registros preparados para {self.table_name}")
        return records

    def inserir_supabase(self, registros: list[dict[str, Any]]) -> int:
        if not registros:
            return 0

        supabase = get_supabase()
        data_extracao = date.today().isoformat()

        linhas_inseridas = 0
        lote = []
        for reg in registros:
            lote.append({
                "dados": reg,
                "data_extracao": data_extracao,
            })
            if len(lote) >= 100:
                linhas_inseridas += self._inserir_lote(supabase, lote)
                lote = []

        if lote:
            linhas_inseridas += self._inserir_lote(supabase, lote)

        logger.info(f"{linhas_inseridas} linhas inseridas em {self.table_name}")
        return linhas_inseridas

    def _inserir_lote(self, supabase, lote: list[dict]) -> int:
        try:
            resp = supabase.table(self.table_name).insert(lote).execute()
            return len(lote)
        except Exception as e:
            logger.error(f"Erro ao inserir lote em {self.table_name}: {e}")
            return 0

    def _obter_coluna_ordenacao(self, df: pd.DataFrame) -> str | None:
        """Determina a coluna de data principal para ordenação/estatísticas."""
        try:
            padroes_data = ['data', 'date', 'pagamento', 'vencimento', 'mes/ano', 'mesano', 'periodo', 'competencia', 'competência']
            colunas_data = [c for c in df.columns if any(p in _normalizar_texto(c) for p in padroes_data)]
            if not colunas_data:
                return None

            cols_pag = [c for c in colunas_data if 'pagamento' in _normalizar_texto(c)]
            cols_venc = [c for c in colunas_data if 'vencimento' in _normalizar_texto(c)]
            cols_mesano = [c for c in colunas_data if 'mes/ano' in _normalizar_texto(c) or 'mesano' in _normalizar_texto(c) or 'periodo' in _normalizar_texto(c)]
            cols_despesa = [c for c in colunas_data if 'despesa' in _normalizar_texto(c)]
            cols_comp = [c for c in colunas_data if 'compet' in _normalizar_texto(c)]

            if 'relatorio_15' in self.table_name and cols_venc:
                return cols_venc[0]
            elif 'relatorio_13' in self.table_name and cols_pag:
                return cols_pag[0]
            elif 'relatorio_11' in self.table_name and cols_despesa:
                return cols_despesa[0]
            elif 'relatorio_07' in self.table_name and cols_comp:
                return cols_comp[0]
            elif 'relatorio_07' in self.table_name and cols_pag:
                return cols_pag[0]
            elif 'relatorio_06' in self.table_name and cols_comp:
                return cols_comp[0]
            elif 'relatorio_14' in self.table_name and cols_mesano:
                return cols_mesano[0]
            elif cols_pag:
                return cols_pag[0]
            elif cols_venc:
                return cols_venc[0]
            else:
                return colunas_data[0]
        except Exception:
            return None

    def executar(self, caminho: Path, dry_run: bool = False) -> dict:
        logger.info(f"Iniciando ingestão para {self.table_name} ({caminho.name})")
        df = self.ler_excel(caminho)

        # Injeta a coluna Competência dinamicamente para o Relatório 06 baseada no nome do arquivo
        if 'relatorio_06' in self.table_name:
            import re
            match = re.search(r'(\d{4})_(\d{2})', caminho.name)
            if match:
                ano = match.group(1)
                mes = match.group(2)
                # Inserimos no índice 0 com formato DD/MM/YYYY para ser parseado corretamente pelo pandas
                df.insert(0, 'Competência', f'01/{mes}/{ano}')
                logger.info(f"Injetada coluna Competência: 01/{mes}/{ano} baseada no nome do arquivo.")
            else:
                logger.warning("Não foi possível extrair a Competência do nome do arquivo para o relatorio_06.")

        df = self.validar_linhas(df)

        self._validar_colunas(df)

        registros = self.df_para_registros(df)

        if dry_run:
            logger.info(f"[DRY RUN] {len(registros)} registros prontos para {self.table_name}")
            return {"total_excel": len(registros), "inseridos": len(registros), "duplicados": 0}

        if not registros:
            logger.warning(f"Nenhum registro para inserir em {self.table_name}")
            return {"total_excel": 0, "inseridos": 0, "duplicados": 0}

        self._verificar_seguranca_antes_deletar(registros)

        if self.report_id in SNAPSHOT_REPORTS:
            total = self.inserir_supabase(registros)
            self.limpar_tabela()
        else:
            meses_alvo = self._extrair_meses_do_nome(caminho)
            if not meses_alvo:
                logger.warning(f"Não foi possível extrair meses do nome do arquivo {caminho.name}. Usando fallback dos dados.")
            self.limpar_periodo(df, meses_alvo=meses_alvo or None)
            total = self.inserir_supabase(registros)

        duplicados = len(registros) - total

        col_ordenacao = self._obter_coluna_ordenacao(df)
        total_banco, data_min_banco, data_max_banco = self._obter_estatisticas_banco(col_ordenacao)

        if total_banco == 0 and total > 0:
            total_banco = total

        logger.info(f"Ingestão concluída: {total} linhas em {self.table_name}. Total real na tabela: {total_banco}")
        return {
            "total_excel": len(registros),
            "inseridos": total,
            "duplicados": duplicados,
            "total_supabase": total_banco,
            "data_min": data_min_banco,
            "data_max": data_max_banco
        }

    def _obter_estatisticas_banco(self, col_ordenacao: str) -> tuple[int, str, str]:
        """Busca o total real de registros e o range de datas da tabela inteira no Supabase."""
        try:
            supabase = get_supabase()

            count_resp = supabase.table(self.table_name).select('id', count='exact').limit(1).execute()
            total_count = count_resp.count if count_resp.count is not None else 0

            if total_count == 0 or not col_ordenacao:
                return total_count, None, None

            all_dates = []
            limit = 1000
            offset = 0
            while True:
                resp = supabase.table(self.table_name).select('dados').range(offset, offset + limit - 1).execute()
                if not resp.data:
                    break

                for row in resp.data:
                    dados = row.get("dados", {})
                    if col_ordenacao in dados:
                        all_dates.append(dados[col_ordenacao])

                if len(resp.data) < limit:
                    break
                offset += limit

            if not all_dates:
                return total_count, None, None

            s = pd.Series(all_dates)
            datas = pd.to_datetime(s, dayfirst=True, errors='coerce').dropna()

            if datas.empty:
                return total_count, None, None

            if 'mês' in col_ordenacao.lower() or 'mes' in col_ordenacao.lower():
                dmin = datas.min().strftime('%m/%Y')
                dmax = datas.max().strftime('%m/%Y')
            else:
                dmin = datas.min().strftime('%d/%m/%Y')
                dmax = datas.max().strftime('%d/%m/%Y')

            return total_count, dmin, dmax

        except Exception as e:
            logger.warning(f"Falha ao obter estatísticas do banco para {self.table_name}: {e}")
            return 0, None, None
