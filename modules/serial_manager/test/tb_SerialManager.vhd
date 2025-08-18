--! \file		tb_SerialManager.vhd
--!
--! \brief		
--!
--! \author		Vinicius Longo (longo.vinicius@gmail.com)
--! \date       25-07-2025
--!
--! \version    1.0
--!
--! \copyright	Copyright (c) 2025 WEG - All Rights reserved.
--!
--! \note		Target devices : No specific target
--! \note		Tool versions  : No specific tool
--! \note		Dependencies   : No specific dependencies
--!
--! \ingroup	None
--! \warning	None
--!
--! \note		Revisions:
--!				- 1.0	25-07-2025	<longo.vinicius@gmail.com>
--!				First revision.


library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.finish;

-- Importar o seu pacote para os tipos de dados, como 'fixed_point_data_t'
use work.SolverPkg.all;

entity tb_SerialManager is
end entity tb_SerialManager;

architecture sim of tb_SerialManager is

    -- Constantes do Testbench
    constant CLK_FREQ_TB      : integer := 250_000_000; -- Clock de 100MHz
    constant CLK_PERIOD       : time    := 4 ns;
    constant BAUD_RATE_TB     : integer := 921600;

    -- Um pacote de dados de 42 bits constante para o teste
    -- 42 bits = 10.5 dígitos hexadecimais. O 11º dígito só pode ir até 3.
    constant TEST_DATA_42BIT  : fixed_point_data_t := B"01" & x"23456789AB";

    -- Sinais para o Clock e Reset
    signal clk_tb     : std_logic := '0';
    signal reset_n_tb : std_logic;

    -- Sinais para conectar ao SerialManager (UUT)
    signal data_in_tb : fixed_point_data_t;
    signal tx_out_tb  : std_logic;

begin

    ----------------------------------------------------
    -- Instanciação da Unidade Sob Teste (SerialManager)
    ----------------------------------------------------
    UUT_SerialManager : entity work.SerialManager
        generic map (
            CLK_FREQ          => CLK_FREQ_TB,
            SEND_INTERVAL_US  => 200,
            BAUD_RATE         => BAUD_RATE_TB
        )
        port map (
            sysclk            => clk_tb,
            reset_n           => reset_n_tb,
            data_in_i         => data_in_tb,
            tx_o              => tx_out_tb
        );

    ----------------------------------------------------
    -- Geração de Clock e Reset
    ----------------------------------------------------
    -- Gera o clock principal de 100MHz
    clk_tb <= not clk_tb after CLK_PERIOD / 2;

    -- Gera um pulso de reset ativo-baixo no início da simulação
    reset_process: process
    begin
        reset_n_tb <= '0';
        wait for CLK_PERIOD * 10;
        reset_n_tb <= '1';
        wait;
    end process;

    ----------------------------------------------------
    -- Processo de Estímulo (muito simples)
    ----------------------------------------------------
    stimulus_process: process
    begin
        -- Apenas fornece o dado constante na entrada.
        -- O Manager irá capturá-lo a cada 200us.
        data_in_tb <= TEST_DATA_42BIT;
        wait; -- Espera para sempre, o processo não precisa de fazer mais nada
    end process;

    ----------------------------------------------------
    -- Processo de Término da Simulação
    ----------------------------------------------------
    simulation_killer: process
    begin
        -- Deixa a simulação correr por 1ms para ver várias transmissões
        wait for 1 ms;
        finish;
    end process;

end architecture sim;