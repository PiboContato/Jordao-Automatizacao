from pathlib import Path
from datetime import date
from typing import Any

import pandas as pd
from src.supabase_client import get_supabase
from src.logger import logger


class BaseIngestor:
    report_id: int = 0
    table_name: str = ""

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

    def df_para_registros(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        records = df.to_dict(orient="records")
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

    def executar(self, caminho: Path, dry_run: bool = False) -> int:
        logger.info(f"Iniciando ingestão para {self.table_name} ({caminho.name})")
        df = self.ler_excel(caminho)
        df = self.validar_linhas(df)
        registros = self.df_para_registros(df)

        if dry_run:
            logger.info(f"[DRY RUN] {len(registros)} registros prontos para {self.table_name}")
            return len(registros)

        if not registros:
            logger.warning(f"Nenhum registro para inserir em {self.table_name}")
            return 0

        total = self.inserir_supabase(registros)
        logger.info(f"Ingestão concluída: {total} linhas em {self.table_name}")
        return total
