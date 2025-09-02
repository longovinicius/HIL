library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.finish;
use work.SolverPkg.all;

entity tb_GridGen is
end entity tb_GridGen;

architecture sim of tb_GridGen is

    -- Constantes para configurar o teste
    constant CLK_FREQ_TB          : integer := 250_000_000;
    constant CLK_PERIOD_TB        : time    := 4 ns; -- 1 / 250MHz
    constant GRID_FREQ_TB         : real    := 50.0;
    constant GRID_PEAK_VOLTAGE_TB : real    := 311.13;
    
    -- Sinais do Testbench
    signal clk_tb               : std_logic := '0';
    signal reset_n_tb           : std_logic;
    signal grid_voltage_fp_tb   : fixed_point_data_t;
    -- Sinal REAL para fácil visualização na forma de onda
    signal grid_voltage_real_tb : real;

begin

    -- Instanciação da Unidade Sob Teste (UUT)
    UUT_Grid_Gen : entity work.GridGen
        generic map (
            CLK_FREQ          => CLK_FREQ_TB,
            GRID_FREQ         => GRID_FREQ_TB,
            GRID_PEAK_VOLTAGE => GRID_PEAK_VOLTAGE_TB
        )
        port map (
            clk               => clk_tb,
            reset_n           => reset_n_tb,
            grid_voltage_o    => grid_voltage_fp_tb
        );
    

    -- Geração de Clock e Reset
    clk_tb <= not clk_tb after CLK_PERIOD_TB / 2;
    reset_process: process
    begin
        reset_n_tb <= '0';
        wait for CLK_PERIOD_TB * 100;
        reset_n_tb <= '1';
        wait;
    end process;

    
    
    -- Processo para terminar a simulação após 2 ciclos de 50Hz
    simulation_killer: process
    begin
        wait for 40 ms; -- 2 ciclos de 50Hz = 2 * (1/50) = 40ms
        report "Simulação de 2 ciclos (40ms) da senoide concluída." severity note;
        finish;
    end process;

end architecture sim;