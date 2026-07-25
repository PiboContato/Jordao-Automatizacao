# -*- coding: utf-8 -*-
with open('AGENTE.md', 'a', encoding='utf-8') as f:
    f.write("""

## 16. Otimização de Ingestão no Supabase e Regras de Datas dos Relatórios

### Aprendizados da Investigação de Limpeza do Banco (Julho/2026):
1. **Filtro de Arquivos em Ingestão (`_encontrar_excel_reports`)**:
   - Para relatórios estáticos/snapshots (1, 2, 4, 5, 8, 12), o orquestrador processa APENAS o arquivo mais recente baixado (`arquivos[0]`). Processar múltiplos arquivos antigos acumulados na pasta `Relatorios/` faz com que o método `limpar_tabela()` seja executado em loop, apagando e reescrevendo o banco repetidas vezes.
   - Para relatórios por período (6, 11, 13, 14, 15), o orquestrador considera apenas arquivos gerados na janela recente da execução atual (últimas 2 horas).

2. **Validação de Colunas no Relatório 02 (Contratos)**:
   - A classe `Ingestor02Contratos` teve seu parâmetro ajustado para `min_colunas = 7` (e não 8) para compatibilidade nativa com a planilha de 7 colunas gerada pelo sistema Jordão.

3. **Proteção contra Anos Fictícios (`0001`)**:
   - Na limpeza por período (`limpar_periodo`), o sistema filtra apenas datas com anos válidos entre `2000` e `2100`. Linhas de cabeçalho/totais sem data que viravam o ano `0001` são ignoradas antes dos comandos de exclusão.

4. **DIRETRIZ FUTURA (REVISÃO INDIVIDUAL POR RELATÓRIO)**:
   - **MUITO IMPORTANTE:** Precisaremos rever o robô individualmente para cada relatório e as regras de datas para extração (filtros de início/fim), garantindo que as premissas de filtro de cada tela combinem exatamente com a estratégia de persistência no Supabase.
""")
print("Section 16 appended to AGENTE.md successfully!")
