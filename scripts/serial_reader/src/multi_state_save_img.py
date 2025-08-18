# -*- coding: utf-8 -*-
"""
Script para ler pacotes de dados de MÚLTIPLOS ESTADOS da porta serial,
processar e plotar.
"""

import serial
import pandas as pd
import matplotlib.pyplot as plt
import time

# --- Bloco de Configuração ---
PORTA_SERIAL = 'COM4'
BAUD_RATE = 3000000  # Ajustado conforme seu novo script
NUM_PACOTES = 1000   # Renomeado para clareza (cada pacote contém 5 estados)
NOME_ARQUIVO_CSV = 'dados_multiplos_estados.csv'

# --- Configurações do Pacote de Dados ---
HEADER_BYTE = b'\xfa'
NUM_ESTADOS = 5
BYTES_POR_ESTADO = 6
TAMANHO_PAYLOAD_BYTES = NUM_ESTADOS * BYTES_POR_ESTADO # 5 estados * 6 bytes = 30 bytes

# --- Configurações do Formato Ponto Fixo (Q14.28) ---
TOTAL_BITS = 42
BITS_FRACIONARIOS = 28

# --- Fim do Bloco de Configuração ---


def to_signed(val, nbits):
    """
    Converte um inteiro de nbits para um valor com sinal (complemento de dois).
    """
    if val & (1 << (nbits - 1)):
        return val - (1 << nbits)
    else:
        return val


def ler_dados_serial():
    """
    Conecta-se à porta serial, sincroniza com o header 0xFA e lê 
    pacotes de dados, cada um contendo 5 estados.
    Retorna uma lista de listas. Ex: [[e0, e1, e2, e3, e4], [...], ...]
    """
    # Lista para armazenar todos os pacotes lidos
    dados_dos_pacotes = []
    ser = None
    
    try:
        ser = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=2)
        ser.set_buffer_size(rx_size=1048576) # 1MB de buffer
        
        print(f"Conectado à porta {PORTA_SERIAL} a {BAUD_RATE} de baudrate.")
        print(f"Procurando por {NUM_PACOTES} pacotes de dados (1 header + {NUM_ESTADOS} estados por pacote)...")
        time.sleep(1)
        ser.reset_input_buffer()

        pacotes_lidos = 0
        while pacotes_lidos < NUM_PACOTES:
            
            # 1. SINCRONIZAÇÃO: Procura pelo byte de header 0xFA
            byte_lido = ser.read(1)
            if byte_lido != HEADER_BYTE:
                continue

            # 2. LEITURA DO PAYLOAD: Lê todos os 30 bytes dos 5 estados de uma vez
            payload_bruto = ser.read(TAMANHO_PAYLOAD_BYTES)

            if len(payload_bruto) < TAMANHO_PAYLOAD_BYTES:
                print("\nAviso: Timeout após receber o header. Pacote incompleto.")
                continue

            # Lista para armazenar os 5 estados deste pacote específico
            estados_do_pacote_atual = []
            
            # 3. PROCESSAMENTO DO PAYLOAD: Itera 5 vezes, uma para cada estado
            for i in range(NUM_ESTADOS):
                # Extrai o "chunk" de 6 bytes correspondente ao estado atual
                inicio_chunk = i * BYTES_POR_ESTADO
                fim_chunk = inicio_chunk + BYTES_POR_ESTADO
                chunk_estado = payload_bruto[inicio_chunk:fim_chunk]
                
                # 4. RECONSTRUÇÃO DO NÚMERO DE 42 BITS (mesma lógica de antes)
                valor_completo_int = 0
                for j in range(5): # 5 bytes completos
                    valor_completo_int |= chunk_estado[j] << (j * 8)
                # 2 bits do último byte
                valor_completo_int |= (chunk_estado[5] & 0x03) << 40

                # 5. CONVERSÃO PARA SINAL
                valor_com_sinal = to_signed(valor_completo_int, TOTAL_BITS)
                estados_do_pacote_atual.append(valor_com_sinal)
            
            # Adiciona a lista com os 5 estados do pacote à lista principal
            dados_dos_pacotes.append(estados_do_pacote_atual)
            pacotes_lidos += 1
        
        print(f"\nLeitura de {pacotes_lidos} pacotes concluída com sucesso.")

    except serial.SerialException as e:
        print(f"Erro: Não foi possível abrir a porta serial {PORTA_SERIAL}.")
        print(f"Detalhe do erro: {e}")
        return None
    except KeyboardInterrupt:
        print("\nLeitura interrompida pelo usuário.")
    finally:
        if ser and ser.is_open:
            ser.close()
            print(f"Porta {PORTA_SERIAL} fechada.")
            
    return dados_dos_pacotes

def processar_e_plotar_dados(dados_dos_pacotes):
    """
    Processa a lista de pacotes, converte para real, salva em CSV e plota os 5 estados.
    """
    if not dados_dos_pacotes:
        print("Nenhum dado para processar.")
        return
        
    # Nomes das colunas para o DataFrame
    nomes_colunas = [f'Estado_{i}' for i in range(NUM_ESTADOS)]

    # Cria o DataFrame diretamente da lista de listas
    df = pd.DataFrame(dados_dos_pacotes, columns=nomes_colunas)
    print(f"\nDataFrame criado com {len(df)} amostras e {len(df.columns)} estados.")

    # Converte os dados de todos os estados para real
    fator_conversao = 2**BITS_FRACIONARIOS
    nomes_colunas_real = []
    for coluna in nomes_colunas:
        nome_nova_coluna = f'{coluna}_Real'
        df[nome_nova_coluna] = df[coluna] / fator_conversao
        nomes_colunas_real.append(nome_nova_coluna)
        
    print("Conversão de ponto fixo para real concluída para todos os estados.")

    # Salva apenas as colunas com os dados reais no arquivo .csv
    df[nomes_colunas_real].to_csv(NOME_ARQUIVO_CSV, index=False, sep=';', decimal=',')
    print(f"Dados salvos com sucesso em '{NOME_ARQUIVO_CSV}'.")
    
    # Plota os dados de todos os estados no mesmo gráfico
    plt.figure(figsize=(14, 7))
    
    for coluna in nomes_colunas_real:
        plt.plot(df.index, df[coluna], marker='.', linestyle='-', markersize=2, label=coluna)

    plt.title('Gráfico dos 5 Estados Decodificados')
    plt.xlabel('Amostra')
    plt.ylabel('Valor Real')
    plt.grid(True)
    plt.legend() # Adiciona a legenda para identificar cada estado
    plt.tight_layout()
    
    print("Exibindo o gráfico...")
    plt.show()


if __name__ == '__main__':
    dados_lidos = ler_dados_serial()
    
    if dados_lidos:
        processar_e_plotar_dados(dados_lidos)