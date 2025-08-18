# -*- coding: utf-8 -*-
"""
Visualizador offline simples para dados do FPGA decodificados.
Este programa carrega e plota o arquivo CSV gerado pelo main.py.
"""

import pandas as pd
import matplotlib.pyplot as plt
import os

# --- Configurações ---
NOME_ARQUIVO_CSV = 'data/IL2/dados_fpga_il2_25us.csv'

if __name__ == '__main__':
    # Verifica se o arquivo existe
    if not os.path.exists(NOME_ARQUIVO_CSV):
        print(f"Erro: Arquivo '{NOME_ARQUIVO_CSV}' não encontrado.")
        print("Execute primeiro o main.py para gerar os dados.")
        exit()
    
    # Carrega os dados
    try:
        df = pd.read_csv(NOME_ARQUIVO_CSV, sep=';', decimal=',')
        print(f"Dados carregados: {len(df)} pontos.")
    except Exception as e:
        print(f"Erro ao carregar o arquivo: {e}")
        exit()
    
    # Plota o gráfico
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['DadoReal'], linestyle='-')
    plt.title('Gráfico dos Dados Decodificados (Q14.28)')
    plt.xlabel('Amostra')
    plt.ylabel('Valor Real')
    plt.grid(True)
    plt.tight_layout()
    plt.show()
