# -*- coding: utf-8 -*-
"""
Visualizador em tempo real para dados do FPGA.
Este programa lê dados da porta serial e plota em tempo real.
"""

import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import time
from collections import deque

# --- Configurações (mesmos parâmetros do main.py) ---
PORTA_SERIAL = 'COM4'
BAUD_RATE = 3000000
HEADER_BYTE = b'\xfa'
TAMANHO_DADOS_BYTES = 6
TOTAL_BITS = 42
BITS_FRACIONARIOS = 28

# --- Configurações da Visualização ---
JANELA_DADOS = 500  # Número de pontos a mostrar na tela (reduzido para performance)
INTERVALO_ATUALIZACAO = 100  # ms entre atualizações do gráfico (aumentado para performance)
DECIMACAO = 2  # Mostra apenas 1 a cada N pontos para reduzir carga visual

# --- Variáveis Globais ---
dados_buffer = deque(maxlen=JANELA_DADOS * DECIMACAO)  # Buffer maior para permitir decimação
ser = None
line = None  # Referência da linha do gráfico para reutilização

def to_signed(val, nbits):
    """
    Converte um inteiro de nbits para um valor com sinal
    usando a representação de complemento de dois.
    """
    if val & (1 << (nbits - 1)):
        return val - (1 << nbits)
    else:
        return val

def conectar_serial():
    """
    Conecta à porta serial.
    """
    global ser
    try:
        ser = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=0.1)
        ser.set_buffer_size(rx_size=1048576)
        print(f"Conectado à porta {PORTA_SERIAL} a {BAUD_RATE} de baudrate.")
        time.sleep(1)
        ser.reset_input_buffer()
        return True
    except serial.SerialException as e:
        print(f"Erro: Não foi possível abrir a porta serial {PORTA_SERIAL}.")
        print(f"Detalhe do erro: {e}")
        return False

def ler_dados():
    """
    Lê dados da porta serial e adiciona ao buffer.
    Versão otimizada para melhor performance.
    Retorna True se conseguiu ler dados, False caso contrário.
    """
    global ser, dados_buffer
    
    if not ser or not ser.is_open:
        return False
    
    try:
        # Lê múltiplos bytes de uma vez para melhor eficiência
        bytes_disponiveis = ser.in_waiting
        if bytes_disponiveis < 7:  # Precisa de pelo menos header + 6 bytes
            return False
        
        # Lê um bloco maior de dados
        bloco_dados = ser.read(min(bytes_disponiveis, 70))  # Lê até 10 pacotes por vez
        
        i = 0
        pacotes_processados = 0
        
        while i < len(bloco_dados) - 6 and pacotes_processados < 5:  # Limita a 5 pacotes por chamada
            # 1. SINCRONIZAÇÃO: Procura pelo byte de header 0xFA
            if bloco_dados[i] != 0xFA:
                i += 1
                continue
            
            # Verifica se há bytes suficientes para um pacote completo
            if i + 6 >= len(bloco_dados):
                break
            
            # 2. EXTRAI OS 6 BYTES DE DADOS
            dados_brutos = bloco_dados[i+1:i+7]
            
            # 3. RECONSTRUÇÃO DO NÚMERO DE 42 BITS
            valor_completo_int = 0
            # Processa os 5 primeiros bytes completos (40 bits)
            for j in range(5):
                valor_completo_int |= dados_brutos[j] << (j * 8)
            # Processa os 2 bits restantes do sexto byte
            valor_completo_int |= (dados_brutos[5] & 0x03) << 40
            
            # 4. CONVERSÃO PARA SINAL E PONTO FIXO
            valor_com_sinal = to_signed(valor_completo_int, TOTAL_BITS)
            fator_conversao = 2**BITS_FRACIONARIOS
            valor_real = valor_com_sinal / fator_conversao
            
            # 5. ADICIONA AO BUFFER
            dados_buffer.append(valor_real)
            
            i += 7  # Avança para o próximo possível pacote
            pacotes_processados += 1
        
        return pacotes_processados > 0
        
    except Exception as e:
        print(f"Erro na leitura: {e}")
        return False

def atualizar_grafico(frame):
    """
    Função chamada pelo matplotlib para atualizar o gráfico.
    Otimizada para melhor performance.
    """
    global line
    
    # Lê vários pontos por frame para melhor performance
    for _ in range(20):  # Aumentado para processar mais dados por frame
        ler_dados()
    
    if len(dados_buffer) > 0:
        # Aplica decimação nos dados para reduzir pontos plotados
        y_data = list(dados_buffer)[::DECIMACAO]  # Pega apenas 1 a cada DECIMACAO pontos
        x_data = range(0, len(dados_buffer), DECIMACAO)[:len(y_data)]
        
        if line is None:
            # Primeira vez: cria o gráfico
            line, = ax.plot(x_data, y_data, 'b-', linewidth=0.8)
            ax.set_xlabel('Amostras')
            ax.set_ylabel('Valor Real')
            ax.grid(True, alpha=0.3)
        else:
            # Atualiza apenas os dados da linha existente (muito mais rápido)
            line.set_data(x_data, y_data)
        
        # Ajusta os limites dos eixos
        if len(y_data) > 1:
            ax.set_xlim(0, len(dados_buffer))
            
            y_min, y_max = min(y_data), max(y_data)
            if y_min != y_max:  # Evita divisão por zero
                margin = (y_max - y_min) * 0.1
                ax.set_ylim(y_min - margin, y_max + margin)
        
        # Atualiza título com estatísticas (menos frequentemente para performance)
        if frame % 5 == 0:  # Atualiza título apenas a cada 5 frames
            if len(dados_buffer) > 0:
                valor_atual = dados_buffer[-1]
                ax.set_title(f'Tempo Real - FPGA (Q14.28) | Atual: {valor_atual:.6f} | Pontos: {len(dados_buffer)} | Taxa: {len(dados_buffer)/DECIMACAO} viz.', 
                            fontsize=12)

def fechar_serial():
    """
    Fecha a conexão serial.
    """
    global ser
    if ser and ser.is_open:
        ser.close()
        print(f"\nPorta {PORTA_SERIAL} fechada.")

if __name__ == '__main__':
    print("Visualizador em Tempo Real - Dados FPGA")
    print("Pressione Ctrl+C para sair")
    
    # Conecta à porta serial
    if not conectar_serial():
        exit()
    
    try:
        # Configuração do matplotlib para melhor performance
        plt.ion()  # Modo interativo
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Otimizações do matplotlib para tempo real
        fig.canvas.toolbar_visible = False  # Remove toolbar para performance
        ax.set_xlim(0, JANELA_DADOS * DECIMACAO)
        ax.set_ylim(-1, 1)  # Limites iniciais, serão ajustados automaticamente
        
        # Configuração da animação
        ani = animation.FuncAnimation(fig, atualizar_grafico, 
                                    interval=INTERVALO_ATUALIZACAO, 
                                    blit=False, cache_frame_data=False,
                                    repeat=True)
        
        plt.tight_layout()
        print("Gráfico em tempo real iniciado. Feche a janela ou pressione Ctrl+C para sair.")
        plt.show(block=True)
        
    except KeyboardInterrupt:
        print("\nVisualizador interrompido pelo usuário.")
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        fechar_serial()
        plt.close('all')