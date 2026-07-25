import pandas as pd
import glob

# Encontrar o excel mais recente do relatorio 07
files = sorted(glob.glob('Relatorios/07*.xlsx'), key=lambda x: __import__('os').path.getmtime(x), reverse=True)
print("Excel files:", files[:5])

if files:
    df = pd.read_excel(files[0])
    print("Colunas:", df.columns.tolist())
    print()
    print("Linha 0:")
    print(df.iloc[0].to_dict())
