import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import os
PHASE_STEP = 1e-5

# Variáveis globais para os dados
dados_globais = {}

def get_script_directory():
    """
    Retorna o diretório onde está localizado este script
    """
    return os.path.dirname(os.path.abspath(__file__))

def encontrar_cruzamentos_zero_simples(tempo, dados, threshold=0.01):
    """
    Versão simplificada para encontrar cruzamentos por zero.
    """
    # Aplica threshold
    dados_threshold = np.where(np.abs(dados) < threshold, 0, dados)
    sinais = np.sign(dados_threshold)
    mudancas_sinal = np.diff(sinais)
    cruzamentos_asc = np.where(mudancas_sinal > 0)[0] + 1
    
    return cruzamentos_asc.tolist() if len(cruzamentos_asc) > 0 else []

def encontrar_pontos_referencia_simples(tempo, dados):
    """
    Versão simplificada sem filtros pesados.
    """
    cruzamentos = encontrar_cruzamentos_zero_simples(tempo, dados)
    
    if len(cruzamentos) == 0:
        return None
    
    idx_zero = cruzamentos[0]
    tempo_zero = tempo.iloc[idx_zero]
    
    # Procura pico em janela simples
    janela_size = min(len(dados) // 4, 1000)  # Limita tamanho da janela
    idx_fim = min(idx_zero + janela_size, len(dados))
    
    janela_dados = dados.iloc[idx_zero:idx_fim]
    idx_pico_rel = janela_dados.abs().idxmax()
    
    return {
        'tempo_zero': tempo_zero,
        'valor_pico': dados.iloc[idx_pico_rel],
        'tempo_pico': tempo.iloc[idx_pico_rel],
        'rms': np.sqrt(np.mean(dados**2))
    }

def carregar_dados_chunked(filename, **kwargs):
    """
    Carrega dados em chunks para economizar memória.
    """
    try:
        # Tenta carregar normalmente primeiro
        return pd.read_csv(filename, **kwargs)
    except:
        # Se falhar, carrega em chunks
        print(f"Carregando {filename} em chunks...")
        chunks = []
        chunksize = 10000
        
        for chunk in pd.read_csv(filename, chunksize=chunksize, **kwargs):
            chunks.append(chunk)
            
        return pd.concat(chunks, ignore_index=True)

def atualizar_graficos(val=None):
    """
    Updates plots when sliders move.
    """
    global dados_globais
    
    for i, var in enumerate(dados_globais['variaveis_validas']):
        slider_obj = dados_globais['sliders'][var]
        raw_val = slider_obj.val
        # Quantize to PHASE_STEP to guarantee 1e-5 resolution
        ajuste_fase = round(raw_val / PHASE_STEP) * PHASE_STEP

        deslocamento_original = dados_globais['resultados_sync'][var]['deslocamento']
        deslocamento_total = deslocamento_original + ajuste_fase
        
        # Atualiza dados
        df_fpga = dados_globais['fpga_data'][var]
        df_fpga['Time_Adjusted'] = df_fpga['Time'] + deslocamento_total
        
        # Atualiza gráfico
        linha_fpga = dados_globais['linhas_fpga'][var]
        linha_fpga.set_xdata(df_fpga['Time_Adjusted'])
        
        # Atualiza título
        axes = dados_globais['axes'][i]
        if ajuste_fase == 0:
            titulo = f'{var.upper()} - Deslocamento: {deslocamento_total:.6f}s'
        else:
            titulo = f'{var.upper()} - Total: {deslocamento_total:.6f}s (Auto: {deslocamento_original:.6f}s + Ajuste: {ajuste_fase:+.6f}s)'
        axes.set_title(titulo, fontsize=12, fontweight='bold')
    
    plt.draw()

def resetar_ajustes():
    """
    Reseta todos os ajustes para zero.
    """
    global dados_globais
    
    for var in dados_globais['variaveis_validas']:
        if var in dados_globais['sliders']:
            dados_globais['sliders'][var].reset()

def salvar_configuracao():
    """
    Salva a configuração atual dos ajustes.
    """
    global dados_globais
    
    print("\n" + "="*50)
    print("CONFIGURAÇÃO ATUAL DOS AJUSTES")
    print("="*50)
    
    # Ajuste: salva na pasta src/ (mesmo diretório do script)
    script_dir = get_script_directory()
    ajustes_path = os.path.join(script_dir, 'ajustes_fase.txt')
    
    # Salva em arquivo
    with open(ajustes_path, 'w') as f:
        f.write("# Ajustes de fase para cada variável (em segundos)\n")
        f.write("# Valores positivos atrasam o sinal da FPGA\n")
        f.write("# Valores negativos adiantam o sinal da FPGA\n\n")
        f.write("AJUSTES_FASE = {\n")
        
        for var in dados_globais['variaveis_validas']:
            if var in dados_globais['sliders']:
                ajuste_raw = dados_globais['sliders'][var].val
                ajuste = round(ajuste_raw / PHASE_STEP) * PHASE_STEP
                f.write(f"    '{var}': {ajuste:.6f},\n")
                print(f"{var.upper()}: {ajuste:+.6f}s")
    
    print(f"\nConfiguração salva em: {ajustes_path}")

def plotar_comparativo_interativo():
    """
    Versão interativa com sliders para ajuste de fase.
    """
    global dados_globais
    
    # --- 1. Definições ---
    script_dir = get_script_directory()
    # Volta um diretório (de src/ para analysis/) e vai para data/
    data_dir = os.path.join(os.path.dirname(script_dir), 'data')
    print(f"Procurando dados em: {data_dir}")
    
    # Ajuste: procura dados na pasta data/
    psim_filename = os.path.join(data_dir, 'psim_1us_sc.csv')
    variaveis = ['vcf', 'vcd', 'il1', 'il2', 'ild']
    taxa_amostragem_fpga = 25e-6
    DURACAO_ESTADO_ESTACIONARIO = 0.08
    
    mapa_colunas_psim = {'vcf': 'VCf', 'vcd': 'VCd', 'il1': 'IL1_1', 'il2': 'IL2_1', 'ild': 'ILd'}
    
    # --- 2. Verificação ---
    # Ajuste: procura dados na pasta data/
    arquivos_necessarios = [psim_filename] + [os.path.join(data_dir, f'dados_fpga_{v}_25us.csv') for v in variaveis]
    arquivos_existentes = [f for f in arquivos_necessarios if os.path.exists(f)]
    
    if not arquivos_existentes:
        print("ERRO: Nenhum arquivo encontrado na pasta data.")
        print("Arquivos procurados:")
        for arquivo in arquivos_necessarios:
            print(f"  - {arquivo}")
        
        # Lista arquivos realmente presentes na pasta data
        print(f"\nArquivos presentes em {data_dir}:")
        try:
            if os.path.exists(data_dir):
                for arquivo in os.listdir(data_dir):
                    if arquivo.endswith('.csv'):
                        print(f"  - {arquivo}")
            else:
                print(f"  Pasta {data_dir} não existe!")
        except Exception as e:
            print(f"  Erro ao listar arquivos: {e}")
        
        return
    
    print(f"Arquivos encontrados: {len(arquivos_existentes)}/{len(arquivos_necessarios)}")
    
    # --- 3. Carregamento ---
    print("Carregando dados (modo interativo)...")
    
    try:
        # Carrega PSIM
        psim_df = carregar_dados_chunked(psim_filename)
        tempo_final_psim = psim_df['Time'].iloc[-1]
        tempo_inicio_ss = tempo_final_psim - DURACAO_ESTADO_ESTACIONARIO
        psim_ss = psim_df[psim_df['Time'] >= tempo_inicio_ss].copy().reset_index(drop=True)
        del psim_df
        
        print(f"PSIM carregado: {len(psim_ss)} pontos no estado estacionário")
        
        # Carrega dados da FPGA
        fpga_data = {}
        variaveis_validas = []
        
        for v in variaveis:
            fpga_filename = os.path.join(data_dir, f'dados_fpga_{v}_25us.csv')
            if os.path.exists(fpga_filename):
                print(f"Carregando {v.upper()}...")
                df_fpga = carregar_dados_chunked(fpga_filename, sep=';', decimal=',')
                
                # Reduz dados se muito grande
                if len(df_fpga) > 50000:
                    print(f"  Reduzindo dados de {len(df_fpga)} para 50000 pontos")
                    step = len(df_fpga) // 50000
                    df_fpga = df_fpga.iloc[::step].reset_index(drop=True)
                
                df_fpga['Time'] = df_fpga.index * taxa_amostragem_fpga
                fpga_data[v] = df_fpga
                variaveis_validas.append(v)
        
        if not variaveis_validas:
            print("ERRO: Nenhum dado da FPGA foi carregado.")
            return
            
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        return
    
    # --- 4. Sincronização inicial ---
    print("Calculando sincronização inicial...")
    resultados_sync = {}
    
    for var in variaveis_validas:
        df_fpga = fpga_data[var]
        
        ref_psim = encontrar_pontos_referencia_simples(
            psim_ss['Time'], psim_ss[mapa_colunas_psim[var]]
        )
        ref_fpga = encontrar_pontos_referencia_simples(
            df_fpga['Time'], df_fpga['DadoReal']
        )
        
        if ref_psim is None or ref_fpga is None:
            print(f"  AVISO: Falha ao encontrar referências para {var.upper()}")
            deslocamento = 0
        else:
            deslocamento = ref_psim['tempo_zero'] - ref_fpga['tempo_zero']
            print(f"  {var.upper()}: Deslocamento inicial = {deslocamento:.6f}s")
        
        df_fpga['Time_Aligned'] = df_fpga['Time'] + deslocamento
        df_fpga['Time_Adjusted'] = df_fpga['Time_Aligned'].copy()
        
        resultados_sync[var] = {
            'deslocamento': deslocamento,
            'ref_psim': ref_psim,
            'ref_fpga': ref_fpga
        }
    
    # --- 5. Criação da interface ---
    print("Criando interface interativa...")
    
    # Figura principal
    fig = plt.figure(figsize=(20, 14))
    
    # Área dos gráficos (deixa espaço para controles à direita)
    gs = fig.add_gridspec(len(variaveis_validas), 1, 
                         left=0.08, right=0.65, top=0.95, bottom=0.08,
                         hspace=0.3)
    
    axes = []
    linhas_fpga = {}
    
    for i, var in enumerate(variaveis_validas):
        ax = fig.add_subplot(gs[i, 0])
        axes.append(ax)
        
        # Plot PSIM
        ax.plot(psim_ss['Time'], psim_ss[mapa_colunas_psim[var]], 
                label='PSIM', color='blue', linewidth=2.5, alpha=0.8)
        
        # Plot FPGA (linha que será atualizada)
        df_fpga = fpga_data[var]
        
        # Reduz pontos para plotting se necessário
        step = max(1, len(df_fpga) // 5000)
        linha, = ax.plot(df_fpga['Time_Adjusted'].iloc[::step], 
                        df_fpga['DadoReal'].iloc[::step], 
                        label='FPGA', color='red', linestyle='--', 
                        marker='o', markersize=0.8, alpha=0.7)
        linhas_fpga[var] = linha
        
        ax.set_title(f'{var.upper()} - Deslocamento: {resultados_sync[var]["deslocamento"]:.6f}s', 
                     fontsize=12, fontweight='bold')
        ax.set_ylabel('Amplitude', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        ax.set_xlim(tempo_inicio_ss, tempo_final_psim)
        
        # Adiciona referências visuais
        if resultados_sync[var]['ref_psim']:
            ax.axvline(x=resultados_sync[var]['ref_psim']['tempo_zero'], 
                      color='blue', linestyle=':', alpha=0.6, linewidth=1)
    
    axes[-1].set_xlabel('Tempo (s)', fontsize=12, fontweight='bold')
    fig.suptitle('Comparativo PSIM vs FPGA - Ajuste Interativo de Fase', 
                fontsize=16, fontweight='bold')
    
    # --- 6. Controles ---
    # Área dos sliders (lado direito)
    sliders = {}
    slider_height = 0.03
    slider_width = 0.2
    
    # Título dos controles
    fig.text(0.72, 0.92, 'AJUSTES DE FASE', fontsize=14, fontweight='bold', ha='center')
    fig.text(0.72, 0.89, '(em segundos)', fontsize=10, ha='center', style='italic')
    
    for i, var in enumerate(variaveis_validas):
        # Posição do slider
        y_pos = 0.8 - i*0.12
        ax_slider = fig.add_axes([0.68, y_pos, slider_width, slider_height])
        
        # Slider (-0.02s a +0.02s, que é aproximadamente um período)
        slider = Slider(ax_slider, f'{var.upper()}',
                       -0.02, 0.02, valinit=0,
                       valfmt='%+.6f', valstep=PHASE_STEP,
                       facecolor='lightblue', alpha=0.8)
        slider.on_changed(atualizar_graficos)
        sliders[var] = slider
        
        # Adiciona indicação de RMS
        if resultados_sync[var]['ref_psim'] and resultados_sync[var]['ref_fpga']:
            rms_psim = resultados_sync[var]['ref_psim']['rms']
            rms_fpga = resultados_sync[var]['ref_fpga']['rms']
            fig.text(0.68, y_pos - 0.04, f'RMS: PSIM={rms_psim:.3f} | FPGA={rms_fpga:.3f}', 
                    fontsize=8, alpha=0.7)
    
    # Botões
    ax_reset = fig.add_axes([0.70, 0.15, 0.08, 0.04])
    btn_reset = Button(ax_reset, 'Reset', color='lightcoral', hovercolor='red')
    btn_reset.on_clicked(lambda x: resetar_ajustes())
    
    ax_save = fig.add_axes([0.80, 0.15, 0.08, 0.04])
    btn_save = Button(ax_save, 'Salvar', color='lightgreen', hovercolor='green')
    btn_save.on_clicked(lambda x: salvar_configuracao())
    
    # Instruções
    instrucoes = (
        'INSTRUÇÕES:\n\n'
        '• Use os sliders para ajustar\n'
        '  a fase de cada sinal\n\n'
        '• Valores positivos atrasam\n'
        '  o sinal da FPGA\n\n'
        '• Valores negativos adiantam\n'
        '  o sinal da FPGA\n\n'
        '• Para inverter fase (180°),\n'
        '  use ±0.010s (meio período)\n\n'
        '• "Reset" volta todos os\n'
        '  ajustes para zero\n\n'
        '• "Salvar" grava a configuração\n'
        '  atual em arquivo'
    )
    
    fig.text(0.72, 0.45, instrucoes, fontsize=9, 
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8),
            verticalalignment='top', horizontalalignment='center')
    
    # Armazena dados globais
    dados_globais = {
        'variaveis_validas': variaveis_validas,
        'fpga_data': fpga_data,
        'resultados_sync': resultados_sync,
        'sliders': sliders,
        'linhas_fpga': linhas_fpga,
        'axes': axes,
        'psim_ss': psim_ss,
        'mapa_colunas_psim': mapa_colunas_psim
    }
    
    print("\nInterface interativa criada!")
    print("Use os sliders à direita para ajustar a fase de cada sinal.")
    plt.show()

if __name__ == '__main__':
    plotar_comparativo_interativo()