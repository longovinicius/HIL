library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.finish;

-- Importar o seu pacote para os tipos de dados
use work.Solver_pkg.all;

entity tb_HIL_TOP is
end entity tb_HIL_TOP;

architecture sim of tb_HIL_TOP is

    -- Constantes do Testbench
    constant CLK_FREQ_TB : integer := 100_000_000; -- Clock de 100MHz
    constant CLK_PERIOD  : time    := 10 ns;

    -- Sinais para o Clock e Reset
    signal clk_tb : std_logic := '0';
    signal rst_tb : std_logic;

    -- Sinais para conectar ao Gerador SPWM
    signal spwm_out_tb      : std_logic;
    signal sine_out_tb      : std_logic_vector(47 downto 0);
    signal triangular_out_tb: std_logic_vector(47 downto 0);

    -- Sinais para conectar ao HIL_TOP (UUT)
    signal sysclk_p_tb        : std_logic;
    signal sysclk_n_tb        : std_logic;
    signal pmod_in_tb         : std_logic;
    signal gpio_led0_tb       : std_logic;
    signal gpio_sw_c_tb       : std_logic := '0'; -- Não utilizado, mantido em '0'
    -- Sinal para visualizar os 5 estados de saída!
    signal xvec_out_tb        : vector_fp_t(0 to 5 - 1);

begin

    ----------------------------------------------------
    -- Geração de Clock e Reset
    ----------------------------------------------------
    -- Gera o clock principal de 100MHz
    clk_tb <= not clk_tb after CLK_PERIOD / 2;

    -- Gera um clock diferencial para o HIL_TOP
    sysclk_p_tb <= clk_tb;
    sysclk_n_tb <= not clk_tb;

    -- Gera um pulso de reset no início da simulação
    reset_process: process
    begin
        rst_tb <= '1';
        wait for CLK_PERIOD * 100;
        rst_tb <= '0';
        wait;
    end process;

    ----------------------------------------------------
    -- 1. Instanciação do Gerador de Estímulo (SPWM)
    ----------------------------------------------------
    SPWM_Generator_inst : entity work.spwm_top
        generic map (
            CLK_FREQ        => CLK_FREQ_TB, -- 100MHz
            SINE_FREQ       => 50,
            SWITCHING_FREQ  => 15_000,
            TABLE_SIZE      => 1024,
            DATA_WIDTH      => 48,
            CALC_WIDTH      => 32
        )
        port map (
            clk             => clk_tb,
            rst             => rst_tb,
            sine_out        => sine_out_tb,
            triangular_out  => triangular_out_tb,
            spwm_out        => spwm_out_tb
        );

    -- O sinal de entrada do PMOD do HIL é a saída do gerador SPWM
    pmod_in_tb <= spwm_out_tb;

    ----------------------------------------------------
    -- 2. Instanciação da Unidade Sob Teste (HIL_TOP)
    ----------------------------------------------------
    UUT_HIL : entity work.HIL_TOP
        port map (
            SYSCLK_P         => sysclk_p_tb,
            SYSCLK_N         => sysclk_n_tb,
            PMOD6_PIN1_R     => pmod_in_tb,
            GPIO_LED0        => gpio_led0_tb,
            GPIO_SW_C        => gpio_sw_c_tb,
            Xvec_current_o   => xvec_out_tb
        );

    ----------------------------------------------------
    -- Processo de Término da Simulação
    ----------------------------------------------------
    simulation_killer: process
    begin
        -- Deixa a simulação correr por 25ms para ver alguns ciclos do SPWM
        wait for 500 ms;
        finish;
    end process;

end architecture sim;