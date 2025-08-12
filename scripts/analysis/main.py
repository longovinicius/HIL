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

# --- Métricas de comparação de formas de onda ---
def sincronizar_e_interpolar(t_ref: np.ndarray, y_ref: np.ndarray,
                             t_tst: np.ndarray, y_tst: np.ndarray):
    """
    Recorta para a interseção temporal e interpola y_tst em t_ref.
    Retorna (t_common, y_ref_c, y_tst_i) ou (None, None, None) se não houver interseção.
    """
    if len(t_ref) < 2 or len(t_tst) < 2:
        return None, None, None

    t0 = max(np.min(t_ref), np.min(t_tst))
    t1 = min(np.max(t_ref), np.max(t_tst))
    if not (np.isfinite(t0) and np.isfinite(t1)) or t1 <= t0:
        return None, None, None

    mask_ref = (t_ref >= t0) & (t_ref <= t1)
    if not np.any(mask_ref):
        return None, None, None

    t_common = t_ref[mask_ref]
    y_ref_c = y_ref[mask_ref]

    # Garante monotonicidade antes da interpolação
    order = np.argsort(t_tst)
    t_tst_sorted = t_tst[order]
    y_tst_sorted = y_tst[order]

    # Interpola teste para a grade do ref
    y_tst_i = np.interp(t_common, t_tst_sorted, y_tst_sorted)
    return t_common, y_ref_c, y_tst_i

def _zero_cross_freq(time_s: np.ndarray, x: np.ndarray):
    """Estimativa de frequência a partir de cruzamentos ascendentes por zero."""
    if time_s.size < 2 or x.size < 2:
        return np.nan
    s = np.sign(x)
    s[s == 0] = 1  # evita (-1,0,+1)
    cross_up_idx = np.where((s[:-1] <= 0) & (s[1:] > 0))[0]
    if cross_up_idx.size >= 2:
        zt = time_s[cross_up_idx]
        periods = np.diff(zt)
        periods = periods[np.isfinite(periods) & (periods > 0)]
        if periods.size:
            return 1.0 / np.mean(periods)
    return np.nan

def calcular_metricas(time_s: np.ndarray, ref: np.ndarray, tst: np.ndarray):
    """
    Calcula métricas de similaridade entre ref (PSIM) e tst (FPGA).
    Retorna um dicionário com métricas chave.
    """
    # Sanitização
    m = min(ref.size, tst.size)
    ref = ref[:m].astype(float)
    tst = tst[:m].astype(float)
    time_s = time_s[:m].astype(float)

    duration = float(time_s[-1] - time_s[0]) if m > 1 else 0.0
    dt = float(np.median(np.diff(time_s))) if m > 1 else np.nan

    # Erros
    err = tst - ref
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    p2p_ref = float(np.max(ref) - np.min(ref)) if m else 0.0
    nrmse = float(rmse / p2p_ref) if p2p_ref > 0 else np.nan
    nrmse_pct = float(nrmse * 100.0) if np.isfinite(nrmse) else np.nan

    # Correlação
    try:
        corr = float(np.corrcoef(ref, tst)[0, 1])
    except Exception:
        corr = np.nan

    # Estatísticas de amplitude
    rms_ref = float(np.sqrt(np.mean(ref**2)))
    rms_tst = float(np.sqrt(np.mean(tst**2)))
    mean_ref = float(np.mean(ref))
    mean_tst = float(np.mean(tst))
    max_ref = float(np.max(ref)); min_ref = float(np.min(ref))
    max_tst = float(np.max(tst)); min_tst = float(np.min(tst))
    p2p_tst = float(max_tst - min_tst)
    crest_ref = float(np.max(np.abs(ref)) / rms_ref) if rms_ref > 0 else np.nan
    crest_tst = float(np.max(np.abs(tst)) / rms_tst) if rms_tst > 0 else np.nan

    # Relação de ganho (ajuste linear tst ≈ a*ref + b)
    var_ref = float(np.var(ref))
    cov = float(np.mean((ref - mean_ref) * (tst - mean_tst)))
    if var_ref > 0:
        amp_ratio = float(cov / var_ref)
        offset = float(mean_tst - amp_ratio * mean_ref)
    else:
        amp_ratio, offset = np.nan, np.nan

    # Defasagem via correlação cruzada
    ref_zm = ref - mean_ref
    tst_zm = tst - mean_tst
    denom = np.linalg.norm(ref_zm) * np.linalg.norm(tst_zm)
    phase_lag_s = np.nan
    if denom > 0 and m > 1 and np.isfinite(dt):
        xcorr = np.correlate(tst_zm, ref_zm, mode='full') / denom
        lag_idx = int(np.argmax(xcorr) - (m - 1))
        phase_lag_s = float(lag_idx * dt)

    # Frequência fundamental estimada (ref)
    f0 = _zero_cross_freq(time_s, ref)
    phase_lag_deg = float(phase_lag_s * f0 * 360.0) if np.isfinite(f0) else np.nan

    return {
        'duration_s': duration,
        'dt_s': dt,
        'mae': mae,
        'rmse': rmse,
        'nrmse_pct': nrmse_pct,
        'corr': corr,
        'mean_ref': mean_ref,
        'mean_tst': mean_tst,
        'rms_ref': rms_ref,
        'rms_tst': rms_tst,
        'crest_ref': crest_ref,
        'crest_tst': crest_tst,
        'p2p_ref': p2p_ref,
        'p2p_tst': p2p_tst,
        'amp_ratio': amp_ratio,
        'offset': offset,
        'phase_lag_s': phase_lag_s,
        'phase_lag_ms': (phase_lag_s * 1e3) if np.isfinite(phase_lag_s) else np.nan,
        'phase_lag_deg': phase_lag_deg,
        'f0_est_hz': float(f0) if np.isfinite(f0) else np.nan,
    }

def plotar_comparativo_lite():
    """
    Versão lite que realiza subamostragem do PSIM para a taxa da FPGA,
    proporcionando comparação justa (mesmo passo temporal) e mostrando
    simultaneamente PSIM original, PSIM subamostrado e FPGA.
    """
    # --- 1. Diretórios ---
    script_dir = get_script_directory()
    data_dir = os.path.join(script_dir, 'data')
    print(f"Procurando dados em: {data_dir}")

    # --- 2. Ajustes de fase ---
    ajustes_fase = carregar_ajustes_fase()

    # --- 3. Definições ---
    psim_filename = os.path.join(data_dir, 'psim_1us_sc.csv')
    variaveis = ['vcf', 'vcd', 'il1', 'il2', 'ild']
    taxa_amostragem_fpga = 25e-6  # 25 microsegundos
    DURACAO_ESTADO_ESTACIONARIO = 0.08  # 80 ms finais
    mapa_colunas_psim = {'vcf': 'VCf', 'vcd': 'VCd', 'il1': 'IL1_1', 'il2': 'IL2_1', 'ild': 'ILd'}
    unidades = {'vcf': 'V', 'vcd': 'V', 'il1': 'A', 'il2': 'A', 'ild': 'A'}

    # --- 4. Verificação básica ---
    arquivos_necessarios = [psim_filename] + [os.path.join(data_dir, f'dados_fpga_{v}_25us.csv') for v in variaveis]
    faltantes = [a for a in arquivos_necessarios if not os.path.exists(a)]
    if faltantes:
        print('ERRO: Arquivos ausentes:')
        for f in faltantes:
            print('  -', f)
        return

    # --- 5. Carregamento + Subamostragem do PSIM ---
    print('\nCarregando dados PSIM (alta resolução)...')
    try:
        psim_df = carregar_dados_chunked(psim_filename)
        if 'Time' not in psim_df.columns:
            print('ERRO: Arquivo PSIM sem coluna Time.')
            return
        tempo_final_psim = float(psim_df['Time'].iloc[-1])
        tempo_inicio_ss = tempo_final_psim - DURACAO_ESTADO_ESTACIONARIO
        psim_ss_original = psim_df[psim_df['Time'] >= tempo_inicio_ss].copy().reset_index(drop=True)
        del psim_df
        print(f"PSIM original carregado: {len(psim_ss_original)} pontos")

        # Subamostragem
        print(f"Subamostrando PSIM para passo {taxa_amostragem_fpga*1e6:.0f}µs ...")
        psim_resample = psim_ss_original.copy()
        psim_resample['Time'] = pd.to_timedelta(psim_resample['Time'], unit='s')
        psim_resample = psim_resample.set_index('Time')
        freq_str = f"{int(taxa_amostragem_fpga * 1e6)}us"  # ex: '25us'
        psim_ss = psim_resample.resample(freq_str).mean().reset_index()
        psim_ss['Time'] = psim_ss['Time'].dt.total_seconds()
        print(f"PSIM subamostrado: {len(psim_ss)} pontos")
    except Exception as e:
        print(f"Erro ao carregar ou subamostrar PSIM: {e}")
        return

    # --- 6. Processamento das variáveis ---
    resultados_sync = {}
    variaveis_processadas = [v for v in variaveis if os.path.exists(os.path.join(data_dir, f'dados_fpga_{v}_25us.csv')) and mapa_colunas_psim[v] in psim_ss.columns]
    if not variaveis_processadas:
        print('ERRO: Nenhuma variável válida encontrada.')
        return
    print('Variáveis a processar:', [v.upper() for v in variaveis_processadas])

    fig, axes = plt.subplots(len(variaveis_processadas), 1, figsize=(16, 4*len(variaveis_processadas)), sharex=True)
    if len(variaveis_processadas) == 1:
        axes = [axes]
    fig.suptitle('Comparativo PSIM vs FPGA', fontsize=16, fontweight='bold')

    for i, var in enumerate(variaveis_processadas):
        print(f"\nProcessando '{var.upper()}' ...")
        try:
            # Carrega FPGA
            fpga_path = os.path.join(data_dir, f'dados_fpga_{var}_25us.csv')
            df_fpga = carregar_dados_chunked(fpga_path, sep=';', decimal=',')
            if 'DadoReal' not in df_fpga.columns:
                print(f"  ERRO: Arquivo FPGA sem coluna 'DadoReal' para {var}.")
                continue
            df_fpga['Time'] = df_fpga.index * taxa_amostragem_fpga
            print(f"  FPGA carregado: {len(df_fpga)} pontos")

            # Referências para sincronização (PSIM subamostrado vs FPGA)
            ref_psim = encontrar_pontos_referencia_simples(psim_ss['Time'], psim_ss[mapa_colunas_psim[var]])
            ref_fpga = encontrar_pontos_referencia_simples(df_fpga['Time'], df_fpga['DadoReal'])
            deslocamento_auto = ref_psim['tempo_zero'] - ref_fpga['tempo_zero'] if (ref_psim and ref_fpga) else 0.0
            ajuste_manual = ajustes_fase.get(var, 0.0)
            deslocamento_total = deslocamento_auto + ajuste_manual
            df_fpga['Time_Aligned'] = df_fpga['Time'] + deslocamento_total

            # Interpolação / Métricas (agora passos próximos/iguais)
            t_common, y_ref_c, y_tst_i = sincronizar_e_interpolar(
                psim_ss['Time'].to_numpy(float),
                psim_ss[mapa_colunas_psim[var]].to_numpy(float),
                df_fpga['Time_Aligned'].to_numpy(float),
                df_fpga['DadoReal'].to_numpy(float)
            )

            metrics = None
            if t_common is not None and len(t_common) > 1:
                metrics = calcular_metricas(t_common, y_ref_c, y_tst_i)
                print('  [Métricas (Subamostrado)]')
                print(f"    NRMSE: {metrics['nrmse_pct']:.2f}% | Corr: {metrics['corr']:.4f} | Ganho: {metrics['amp_ratio']:.4f}")
                print(f"    RMS (PSIM/FPGA): {metrics['rms_ref']:.3f}/{metrics['rms_tst']:.3f} {unidades.get(var,'')}")
            else:
                print('  AVISO: Sem intervalo comum para métricas.')

            resultados_sync[var] = {
                'deslocamento_total': deslocamento_total,
                'metrics': metrics
            }

            # Plot triple
            ax = axes[i]
            # ax.plot(psim_ss_original['Time'], psim_ss_original[mapa_colunas_psim[var]], label='PSIM (Original)', color='lightblue', linewidth=1.2)
            ax.plot(psim_ss['Time'], psim_ss[mapa_colunas_psim[var]], label='PSIM (Subamostrado)', color='blue', linestyle='--', marker='.', markersize=3)
            ax.plot(df_fpga['Time_Aligned'], df_fpga['DadoReal'], label='FPGA', color='red', linestyle=':', marker='.', markersize=3, alpha=0.85)
            ax.set_title(var.upper(), fontsize=12, fontweight='bold')
            ax.set_ylabel(f"Amp ({unidades.get(var,'')})")
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=9)
            ax.set_xlim(tempo_inicio_ss, tempo_final_psim)
        except Exception as e:
            print(f"  ERRO ao processar {var}: {e}")
            continue

    axes[-1].set_xlabel('Tempo (s)', fontsize=12, fontweight='bold')
    plt.tight_layout(rect=[0,0.03,1,0.96])
    out_png = os.path.join(script_dir, 'comparacao_subamostrada.png')
    plt.savefig(out_png, dpi=150, bbox_inches='tight')
    plt.show()

    # --- 7. Relatório Final ---
    print('\n' + '='*70)
    print('RELATÓRIO FINAL (PSIM Subamostrado vs FPGA)')
    print('='*70)
    rows = []
    for var in variaveis_processadas:
        info = resultados_sync.get(var)
        if not info or not info.get('metrics'):
            continue
        m = info['metrics']
        print(f"\n{var.upper()}: deslocamento_total={info['deslocamento_total']:.6f}s")
        print(f"  NRMSE: {m['nrmse_pct']:.2f}% | Corr: {m['corr']:.4f} | Ganho: {m['amp_ratio']:.4f} | Offset: {m['offset']:.4g}")
        print(f"  RMS_ref/FPGA: {m['rms_ref']:.4f}/{m['rms_tst']:.4f} | P2P_ref/FPGA: {m['p2p_ref']:.4f}/{m['p2p_tst']:.4f}")
        print(f"  Defasagem: {m['phase_lag_ms']:.3f} ms ({m['phase_lag_deg']:.2f}°)  f0_est: {m['f0_est_hz']:.2f} Hz")
        rows.append({
            'variavel': var,
            'deslocamento_s': info['deslocamento_total'],
            'nrmse_pct': m['nrmse_pct'],
            'corr': m['corr'],
            'amp_ratio': m['amp_ratio'],
            'offset': m['offset'],
            'rms_ref': m['rms_ref'],
            'rms_tst': m['rms_tst'],
            'p2p_ref': m['p2p_ref'],
            'p2p_tst': m['p2p_tst'],
            'phase_lag_ms': m['phase_lag_ms'],
            'phase_lag_deg': m['phase_lag_deg'],
            'f0_est_hz': m['f0_est_hz']
        })

    if rows:
        csv_path = os.path.join(script_dir, 'metrics_report_subsampled.csv')
        try:
            pd.DataFrame(rows).to_csv(csv_path, index=False)
            print(f"\nRelatório CSV salvo em: {csv_path}")
        except Exception as e:
            print('Falha ao salvar CSV:', e)

    print(f"\nGráfico salvo em: {out_png}")

if __name__ == '__main__':
    plotar_comparativo_lite()