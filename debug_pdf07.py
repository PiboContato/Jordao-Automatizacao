import pdfplumber

pdf_path = r'Relatorios\07 Relatorio de Cobranças Recebidas 2026_06 a 2026_06.pdf'
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()
    # Imprimir as 80 primeiras palavras com coordenadas x
    for w in words[:80]:
        print(f"x0={w['x0']:.1f} x1={w['x1']:.1f} top={w['top']:.1f} text={w['text']}")
