import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def get_script_directory():
    """
    Retorna o diretório onde está localizado este script
    """
    return os.path.dirname(os.path.abspath(__file__))

def carregar_ajustes_fase():
    """
    Carrega os ajustes de fase salvos do arquivo ajustes_fase.txt
    """
    ajustes = {}
    script_dir = get_script_directory()
    # Ajuste: procura ajustes_fase.txt na pasta src/
    ajustes_path = os.path.join(script_dir, 'src', 'ajustes_fase.txt')
    
    if not os.path.exists(ajustes_path):
        print(f"Arquivo 'ajustes_fase.txt' não encontrado em: {os.path.join(script_dir, 'src')}")
        print("Usando ajustes padrão (zero).")
        return ajustes
    
    try:
        with open(ajustes_path, 'r') as f:
            conteudo = f.read()
        
        # Procura pela definição do dicionário AJUSTES_FASE
        linhas = conteudo.split('\n')
        dentro_dict = False
        
        for linha in linhas:
            linha = linha.strip()
            
            if 'AJUSTES_FASE = {' in linha:
                dentro_dict = True
                continue
            
            if dentro_dict and '}' in linha:
                break
            
            if dentro_dict and ':' in linha:
                # Extrai variável e valor
                partes = linha.split(':')
                if len(partes) == 2:
                    var_name = partes[0].strip().strip("'\"")
                    valor_str = partes[1].strip().rstrip(',')
                    try:
                        valor = float(valor_str)
                        ajustes[var_name] = valor
                    except ValueError:
                        continue
        
        print(f"Ajustes de fase carregados de: {ajustes_path}")
        for var, ajuste in ajustes.items():
            print(f"  {var.upper()}: {ajuste:+.6f}s")
            
    except Exception as e:
        print(f"Erro ao ler 'ajustes_fase.txt': {e}")
        print("Usando ajustes padrão (zero).")
    
    return ajustes

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

def plotar_comparativo_lite():
    """
    Versão lite com menor uso de memória e ajustes de fase automáticos.
    """
    
    # --- 1. Define diretório do script ---
    script_dir = get_script_directory()
    data_dir = os.path.join(script_dir, 'data')
    print(f"Procurando dados em: {data_dir}")
    
    # --- 2. Carrega ajustes de fase ---
    ajustes_fase = carregar_ajustes_fase()
    
    # --- 3. Definições ---
    # Ajuste: procura dados na pasta data/
    psim_filename = os.path.join(data_dir, 'psim_1us_sc.csv')
    variaveis = ['vcf', 'vcd', 'il1', 'il2', 'ild']
    taxa_amostragem_fpga = 25e-6
    DURACAO_ESTADO_ESTACIONARIO = 0.08
    
    mapa_colunas_psim = {'vcf': 'VCf', 'vcd': 'VCd', 'il1': 'IL1_1', 'il2': 'IL2_1', 'ild': 'ILd'}
    
    # Mapeamento de unidades por variável
    unidades = {
        'vcf': 'V',  # Tensão
        'vcd': 'V',  # Tensão
        'il1': 'A',  # Corrente
        'il2': 'A',  # Corrente
        'ild': 'A'   # Corrente
    }
    
    # --- 4. Verificação ---
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
    
    print(f"\nArquivos encontrados: {len(arquivos_existentes)}/{len(arquivos_necessarios)}")
    
    # --- 5. Carregamento com Controle de Memória ---
    print("\nCarregando dados (modo econômico de memória)...")
    
    try:
        # Carrega PSIM
        psim_df = carregar_dados_chunked(psim_filename)
        
        # Estado estacionário do PSIM
        tempo_final_psim = psim_df['Time'].iloc[-1]
        tempo_inicio_ss = tempo_final_psim - DURACAO_ESTADO_ESTACIONARIO
        psim_ss = psim_df[psim_df['Time'] >= tempo_inicio_ss].copy().reset_index(drop=True)
        
        # Libera memória
        del psim_df
        
        print(f"PSIM carregado: {len(psim_ss)} pontos no estado estacionário")
        
    except Exception as e:
        print(f"Erro ao carregar PSIM: {e}")
        return
    
    # --- 6. Processamento por Variável ---
    resultados_sync = {}
    variaveis_processadas = []
    
    # Primeiro, identifica quais variáveis podem ser processadas
    for var in variaveis:
        fpga_filename = os.path.join(data_dir, f'dados_fpga_{var}_25us.csv')
        if os.path.exists(fpga_filename) and mapa_colunas_psim[var] in psim_ss.columns:
            variaveis_processadas.append(var)
    
    if not variaveis_processadas:
        print("ERRO: Nenhuma variável pode ser processada.")
        return
    
    print(f"Variáveis a processar: {[v.upper() for v in variaveis_processadas]}")
    
    # Cria figura
    fig, axes = plt.subplots(len(variaveis_processadas), 1, figsize=(16, 4*len(variaveis_processadas)), sharex=True)
    if len(variaveis_processadas) == 1:
        axes = [axes]  # Garante que axes seja sempre uma lista
    
    fig.suptitle('Comparativo PSIM vs FPGA', fontsize=16, fontweight='bold')
    
    for i, var in enumerate(variaveis_processadas):
        print(f"\nProcessando '{var.upper()}'...")
        
        try:
            # Carrega dados da FPGA da pasta data/
            fpga_filename = os.path.join(data_dir, f'dados_fpga_{var}_25us.csv')
            df_fpga = carregar_dados_chunked(fpga_filename, sep=';', decimal=',')
            
            # Reduz dados da FPGA se muito grande
            if len(df_fpga) > 50000:
                print(f"  Reduzindo dados da FPGA de {len(df_fpga)} para 50000 pontos")
                step = len(df_fpga) // 50000
                df_fpga = df_fpga.iloc[::step].reset_index(drop=True)
            
            df_fpga['Time'] = df_fpga.index * taxa_amostragem_fpga
            
            print(f"  FPGA carregado: {len(df_fpga)} pontos")
            
            # Encontra pontos de referência
            ref_psim = encontrar_pontos_referencia_simples(
                psim_ss['Time'], psim_ss[mapa_colunas_psim[var]]
            )
            ref_fpga = encontrar_pontos_referencia_simples(
                df_fpga['Time'], df_fpga['DadoReal']
            )
            
            if ref_psim is None or ref_fpga is None:
                print(f"  AVISO: Falha ao encontrar referências para '{var.upper()}'")
                deslocamento_auto = 0
            else:
                # Sincronização automática
                deslocamento_auto = ref_psim['tempo_zero'] - ref_fpga['tempo_zero']
                print(f"  RMS PSIM: {ref_psim['rms']:.3f}")
                print(f"  RMS FPGA: {ref_fpga['rms']:.3f}")
                print(f"  Deslocamento automático: {deslocamento_auto:.6f}s")
            
            # Aplica ajuste de fase salvo
            ajuste_manual = ajustes_fase.get(var, 0.0)
            deslocamento_total = deslocamento_auto + ajuste_manual
            
            if ajuste_manual != 0:
                print(f"  Ajuste de fase aplicado: {ajuste_manual:+.6f}s")
                print(f"  Deslocamento total: {deslocamento_total:.6f}s")
            
            df_fpga['Time_Aligned'] = df_fpga['Time'] + deslocamento_total
            
            # Salva resultados
            resultados_sync[var] = {
                'deslocamento_auto': deslocamento_auto,
                'ajuste_manual': ajuste_manual,
                'deslocamento_total': deslocamento_total,
                'ref_psim': ref_psim,
                'ref_fpga': ref_fpga
            }
            
            # Plot
            ax = axes[i]
            ax.plot(psim_ss['Time'], psim_ss[mapa_colunas_psim[var]], 
                    label='PSIM', color='blue', linewidth=2.5, alpha=0.8)
            
            # Reduz pontos para plotting se necessário
            step_plot = max(1, len(df_fpga) // 5000)
            ax.plot(df_fpga['Time_Aligned'].iloc[::step_plot], df_fpga['DadoReal'].iloc[::step_plot], 
                    label='FPGA', color='red', linestyle='--', 
                    marker='o', markersize=0.8, alpha=0.7)
            
            # Título simplificado - apenas o nome da variável
            ax.set_title(f'{var.upper()}', fontsize=12, fontweight='bold')
            
            # Unidade no eixo Y baseada no tipo de variável
            unidade = unidades.get(var, 'Amplitude')
            ax.set_ylabel(f'Amplitude ({unidade})', fontsize=10)
            
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.set_xlim(tempo_inicio_ss, tempo_final_psim)
            
            # Remove os marcadores de referência (ponto azul e linha vertical)
            # Comentando as linhas que adicionavam os marcadores:
            # if ref_psim is not None:
            #     ax.axvline(x=ref_psim['tempo_zero'], color='blue', 
            #               linestyle=':', alpha=0.6, linewidth=1)
            #     ax.plot(ref_psim['tempo_pico'], ref_psim['valor_pico'], 
            #            'bo', markersize=6, alpha=0.8)
            
        except Exception as e:
            print(f"  ERRO ao processar {var}: {e}")
            continue
    
    axes[-1].set_xlabel('Tempo (s)', fontsize=12, fontweight='bold')
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    
    # Salva e mostra (no diretório do script)
    nome_arquivo = os.path.join(script_dir, 'comparacao_lite_com_ajustes.png')
    plt.savefig(nome_arquivo, dpi=150, bbox_inches='tight')
    plt.show()
    
    # --- 7. Relatório ---
    print("\n" + "="*60)
    print("RELATÓRIO DE SINCRONIZAÇÃO")
    print("="*60)
    
    ajustes_aplicados = False
    for var in variaveis_processadas:
        if var in resultados_sync:
            info = resultados_sync[var]
            print(f"\n{var.upper()}:")
            print(f"  Deslocamento automático: {info['deslocamento_auto']:.6f}s")
            print(f"  Ajuste manual: {info['ajuste_manual']:+.6f}s")
            print(f"  Deslocamento total: {info['deslocamento_total']:.6f}s")
            
            if info['ajuste_manual'] != 0:
                ajustes_aplicados = True
            
            if info['ref_psim'] and info['ref_fpga']:
                print(f"  RMS PSIM: {info['ref_psim']['rms']:.4f}")
                print(f"  RMS FPGA: {info['ref_fpga']['rms']:.4f}")
                diferenca_rms = abs(info['ref_psim']['rms'] - info['ref_fpga']['rms'])
                print(f"  Diferença RMS: {diferenca_rms:.4f}")
    
    print(f"\nGráfico salvo: {nome_arquivo}")
    
    if ajustes_aplicados:
        print(f"\n✓ Ajustes de fase do arquivo 'ajustes_fase.txt' foram aplicados!")
    else:
        print(f"\n• Nenhum ajuste de fase foi aplicado (valores zero ou arquivo não encontrado)")
        print(f"• Para aplicar ajustes, use primeiro a versão interativa para configurá-los")

if __name__ == '__main__':
    plotar_comparativo_lite()