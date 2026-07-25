import pandas as pd
import glob
import os

# Verificar TODOS os excel do relatorio 07 gerados nas ultimas 2h
import time
agora = time.time()

files = sorted(glob.glob('Relatorios/07*.xlsx'), key=os.path.getmtime, reverse=True)
print(f"Todos os arquivos Excel do relatorio 07:")
for f in files:
    idade_min = (agora - os.path.getmtime(f)) / 60
    recente = "RECENTE <2h" if idade_min < 120 else "antigo"
    print(f"  {os.path.basename(f)} ({idade_min:.0f} min atras) [{recente}]")
    df = pd.read_excel(f)
    comp_cols = [c for c in df.columns if 'comp' in c.lower() or 'compet' in c.lower()]
    print(f"    Colunas comp/compet: {comp_cols}")
    if 'Competência' in df.columns:
        print(f"    Competência valor: {df['Competência'].iloc[0] if len(df) > 0 else 'vazio'}")
    elif 'Comp.' in df.columns:
        print(f"    Comp. valor: {df['Comp.'].iloc[0] if len(df) > 0 else 'vazio'}")
    print()
