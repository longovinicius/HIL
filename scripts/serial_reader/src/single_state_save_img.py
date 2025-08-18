# -*- coding: utf-8 -*-
"""
Script para ler pacotes de dados binários (Header + 42 bits) da porta serial,
processar e plotar.
"""

import serial
import pandas as pd
import matplotlib.pyplot as plt
import time

# --- Bloco de Configuração ---
PORTA_SERIAL = 'COM4'
BAUD_RATE = 3000000
NUM_PONTOS = 5000
NOME_ARQUIVO_CSV = 'dados_fpga.csv'

# --- Configurações do Pacote de Dados (baseado no seu exemplo) ---
HEADER_BYTE = b'\xfa'  # O byte de início do pacote (0xFA)
TAMANHO_DADOS_BYTES = 6 # 6 bytes para os 42 bits de dados

# --- Configurações do Formato Ponto Fixo (Q14.28) ---
TOTAL_BITS = 42
BITS_FRACIONARIOS = 28

# --- Fim do Bloco de Configuração ---


def to_signed(val, nbits):
    """
    Função fornecida para converter um inteiro de nbits para um valor com sinal
    usando a representação de complemento de dois.
    """
    # Verifica se o bit de sinal (o bit mais significativo) está ativo
    if val & (1 << (nbits - 1)):
        # Se estiver, subtrai 2^nbits para obter o valor negativo
        return val - (1 << nbits)
    else:
        # Caso contrário, o valor já é positivo
        return val


def ler_dados_serial():
    """
    Conecta-se à porta serial, sincroniza com o header 0xFA e lê 
    os pacotes de dados de 42 bits.
    Retorna uma lista com os números inteiros (com sinal) lidos.
    """
    dados_inteiros_com_sinal = []
    ser = None
    
    try:
        ser = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=2)
        # ser.set_buffer_size(rx_size = 4294967296)
        ser.set_buffer_size(rx_size = 1048576)
        print(f"Conectado à porta {PORTA_SERIAL} a {BAUD_RATE} de baudrate.")
        print(f"Procurando por {NUM_PONTOS} pacotes de dados (iniciando com 0xFA)...")
        time.sleep(1)
        ser.reset_input_buffer()

        pontos_lidos = 0
        while pontos_lidos < NUM_PONTOS:
            
            # 1. SINCRONIZAÇÃO: Procura pelo byte de header 0xFA
            # Lê byte a byte até encontrar o header correto.
            byte_lido = ser.read(1)
            if byte_lido != HEADER_BYTE:
                continue # Se não for o header, ignora e procura o próximo

            # 2. LEITURA DO PACOTE: Se encontrou o header, lê os 6 bytes de dados
            dados_brutos = ser.read(TAMANHO_DADOS_BYTES)

            if len(dados_brutos) < TAMANHO_DADOS_BYTES:
                print("\nAviso: Timeout após receber o header. Pacote incompleto.")
                continue # Volta ao início para procurar um novo header

            # 3. RECONSTRUÇÃO DO NÚMERO DE 42 BITS (lógica do seu exemplo)
            # A ordem é little-endian: o primeiro byte é o menos significativo.
            valor_completo_int = 0
            # Processa os 5 primeiros bytes completos (40 bits)
            for i in range(5):
                valor_completo_int |= dados_brutos[i] << (i * 8)
            # Processa os 2 bits restantes do sexto byte
            # (dados_brutos[5] & 0x03) pega apenas os 2 bits menos significativos
            valor_completo_int |= (dados_brutos[5] & 0x03) << 40

            # 4. CONVERSÃO PARA SINAL
            valor_com_sinal = to_signed(valor_completo_int, TOTAL_BITS)
            
            dados_inteiros_com_sinal.append(valor_com_sinal)
            pontos_lidos += 1
            # print(f"Pacote {pontos_lidos}/{NUM_PONTOS} recebido. Valor: {valor_com_sinal}")

    except serial.SerialException as e:
        print(f"Erro: Não foi possível abrir a porta serial {PORTA_SERIAL}.")
        print(f"Detalhe do erro: {e}")
        return None
    except KeyboardInterrupt:
        print("\nLeitura interrompida pelo usuário.")
    finally:
        if ser and ser.is_open:
            ser.close()
            print(f"\nPorta {PORTA_SERIAL} fechada.")
            
    return dados_inteiros_com_sinal

def processar_e_plotar_dados(dados_inteiros):
    """
    Processa a lista de dados inteiros, converte para real, salva em CSV e plota.
    """
    if not dados_inteiros:
        print("Nenhum dado para processar.")
        return

    df = pd.DataFrame(dados_inteiros, columns=['DadoBrutoInt_ComSinal'])
    print(f"\nDataFrame criado com {len(df)} pontos.")

    fator_conversao = 2**BITS_FRACIONARIOS
    df['DadoReal'] = df['DadoBrutoInt_ComSinal'] / fator_conversao
    print("Conversão de ponto fixo para real (Q14.28) concluída.")

    df.to_csv(NOME_ARQUIVO_CSV, index=False, sep=';', decimal=',')
    print(f"Dados salvos com sucesso em '{NOME_ARQUIVO_CSV}'.")
    
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['DadoReal'], marker='.', linestyle='-')
    plt.title('Gráfico dos Dados Decodificados (Q14.28)')
    plt.xlabel('Amostra')
    plt.ylabel('Valor Real')
    plt.grid(True)
    plt.tight_layout()
    
    print("Exibindo o gráfico...")
    plt.show()


if __name__ == '__main__':
    dados_lidos = ler_dados_serial()
    
    if dados_lidos:
        processar_e_plotar_dados(dados_lidos)