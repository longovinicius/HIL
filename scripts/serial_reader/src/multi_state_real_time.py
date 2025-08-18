# -*- coding: utf-8 -*-
"""
VISUALIZADOR EM TEMPO REAL para 5 estados, com configurações de tela.
"""

import serial
import time
import collections
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button

# --- Bloco de Configuração ---
PORTA_SERIAL = 'COM4'
BAUD_RATE = 3000000

# --- Configurações do Pacote de Dados ---
HEADER_BYTE_INT = 0xFA
NUM_ESTADOS = 5
BYTES_POR_ESTADO = 6
TAMANHO_PAYLOAD_BYTES = NUM_ESTADOS * BYTES_POR_ESTADO
TAMANHO_PACOTE_COMPLETO = 1 + TAMANHO_PAYLOAD_BYTES

# --- Configurações do Formato Ponto Fixo (Q14.28) ---
TOTAL_BITS = 42
BITS_FRACIONARIOS = 28
FATOR_CONVERSAO = 2**BITS_FRACIONARIOS

# --- NOVAS CONFIGURAÇÕES DE GRÁFICO ---
# Tamanho da janela do gráfico em polegadas
FIG_WIDTH_INCHES = 14
FIG_HEIGHT_INCHES = 7

# Quantos pontos de dados mostrar no eixo X
GRAPH_WINDOW_SIZE = 1000

# Intervalo de atualização em milissegundos
UPDATE_INTERVAL_MS = 100 # Reduzido para uma resposta mais rápida

# Controle do Eixo Y (o "zoom")
Y_AXIS_FIXED = False   # Mude para False para habilitar o auto-ajuste
Y_AXIS_MIN = -0.5
Y_AXIS_MAX = 0.5

# NOVO: Taxa de amostragem para conversão de amostras para tempo
TAXA_AMOSTRAGEM_US = 150  # 150 microsegundos
TAXA_AMOSTRAGEM_MS = TAXA_AMOSTRAGEM_US / 1000  # 0.15 ms

# NOVO: Configurações de fonte (aumentadas)
FONTSIZE_TITLE = 20
FONTSIZE_LABELS = 16
FONTSIZE_LEGEND = 14

# --- Fim do Bloco de Configuração ---


def to_signed(val, nbits):
    if val & (1 << (nbits - 1)):
        return val - (1 << nbits)
    else:
        return val

# --- Estrutura de Dados ---
dados_estados = [collections.deque(maxlen=GRAPH_WINDOW_SIZE) for _ in range(NUM_ESTADOS)]
buffer_de_bytes = bytearray()

# --- Variável de Controle de Pausa ---
pausado = False

# --- Conexão Serial ---
try:
    ser = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=0.1)
    ser.set_buffer_size(rx_size=1048576)
    time.sleep(1)
    ser.reset_input_buffer()
    print(f"Conectado à porta {PORTA_SERIAL} a {BAUD_RATE} de baudrate.")
except Exception as e:
    print(f"Erro ao abrir a porta serial: {e}")
    exit()

# --- Configuração do Gráfico ---
# Usa as novas constantes para o tamanho da figura
fig, ax = plt.subplots(figsize=(FIG_WIDTH_INCHES, FIG_HEIGHT_INCHES))

# Ajusta o layout para dar espaço ao botão
plt.subplots_adjust(bottom=0.15)

# Nomes personalizados para a legenda
nomes_estados = ['Corrente L1', 'Corrente Ld', 'Corrente L2', 'Tensão Cf', 'Tensão Cd']

linhas = [ax.plot([], [], label=nomes_estados[i])[0] for i in range(NUM_ESTADOS)]
ax.set_title('Visualizador em Tempo Real', fontsize=FONTSIZE_TITLE, fontweight='bold')
ax.set_xlabel('Tempo (ms)', fontsize=FONTSIZE_LABELS, fontweight='bold')
ax.set_ylabel('Corrente(A)/Tensão(V)', fontsize=FONTSIZE_LABELS, fontweight='bold')
ax.legend(loc='upper right', fontsize=FONTSIZE_LEGEND)
ax.grid(True)

# Configura eixo X em milissegundos
tempo_max_ms = GRAPH_WINDOW_SIZE * TAXA_AMOSTRAGEM_MS
ax.set_xlim(0, tempo_max_ms)

# Usa as novas constantes para fixar o eixo Y
if Y_AXIS_FIXED:
    ax.set_ylim(Y_AXIS_MIN, Y_AXIS_MAX)

# --- Configuração do Botão de Pausa ---
# Cria um eixo para o botão (posição: [left, bottom, width, height])
ax_button = plt.axes([0.45, 0.02, 0.1, 0.05])
button_pause = Button(ax_button, 'Pausar')

def toggle_pause(event):
    """Função chamada quando o botão é clicado."""
    global pausado
    pausado = not pausado
    if pausado:
        button_pause.label.set_text('Retomar')
        print("Visualizador PAUSADO")
    else:
        button_pause.label.set_text('Pausar')
        print("Visualizador RETOMADO")

# Conecta a função ao botão
button_pause.on_clicked(toggle_pause)


def update(frame):
    """Lê todos os pacotes disponíveis no buffer e atualiza o gráfico."""
    global pausado
    
    # Se estiver pausado, não processa novos dados mas ainda atualiza o gráfico
    if not pausado:
        if ser.in_waiting > 0:
            novos_dados = ser.read(ser.in_waiting)
            buffer_de_bytes.extend(novos_dados)

        while len(buffer_de_bytes) >= TAMANHO_PACOTE_COMPLETO:
            try:
                indice_header = buffer_de_bytes.index(HEADER_BYTE_INT)
            except ValueError:
                buffer_de_bytes.clear()
                break

            if indice_header > 0:
                del buffer_de_bytes[:indice_header]

            if len(buffer_de_bytes) < TAMANHO_PACOTE_COMPLETO:
                break

            payload_bruto = buffer_de_bytes[1:TAMANHO_PACOTE_COMPLETO]
            
            for i in range(NUM_ESTADOS):
                chunk_estado = payload_bruto[i*BYTES_POR_ESTADO : (i+1)*BYTES_POR_ESTADO]
                
                valor_completo_int = 0
                for j in range(5):
                    valor_completo_int |= chunk_estado[j] << (j * 8)
                valor_completo_int |= (chunk_estado[5] & 0x03) << 40

                valor_com_sinal = to_signed(valor_completo_int, TOTAL_BITS)
                valor_real = valor_com_sinal / FATOR_CONVERSAO
                dados_estados[i].append(valor_real)
            
            del buffer_de_bytes[:TAMANHO_PACOTE_COMPLETO]
    
    # ATUALIZAÇÃO DO GRÁFICO (sempre acontece, pausado ou não)
    for i, linha in enumerate(linhas):
        # Converte amostras para tempo em milissegundos
        tempo_ms = [j * TAXA_AMOSTRAGEM_MS for j in range(len(dados_estados[i]))]
        linha.set_data(tempo_ms, dados_estados[i])
    
    # Atualiza o título para mostrar o status
    if pausado:
        ax.set_title('Visualizador em Tempo Real - PAUSADO', fontsize=FONTSIZE_TITLE, fontweight='bold')
    else:
        ax.set_title('Visualizador em Tempo Real', fontsize=FONTSIZE_TITLE, fontweight='bold')
    
    # Se o eixo Y não estiver fixo, permite o auto-ajuste
    if not Y_AXIS_FIXED:
        ax.relim()
        ax.autoscale_view(True, True, True)
    
    return linhas

# --- Inicia a Animação ---
ani = animation.FuncAnimation(
    fig,
    update,
    interval=UPDATE_INTERVAL_MS,
    blit=False,
    cache_frame_data=False
)

try:
    print("Iniciando visualizador... Feche a janela do gráfico para parar.")
    print("Use o botão 'Pausar' para congelar a imagem.")
    plt.show()
finally:
    ser.close()
    print("Porta serial fechada.")