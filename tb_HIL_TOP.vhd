--! \file		tb_HIL_TOP.vhd
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

library std; 
use std.textio.all;

use work.Solver_pkg.all;

entity tb_HIL_TOP is
end entity tb_HIL_TOP;

architecture sim of tb_HIL_TOP is

    constant CLK_FREQ_TB        : integer := 200_000_000; -- Clock de 100MHz
    constant CLK_PERIOD         : time    := 5 ns;

    signal clk_tb               : std_logic := '0';
    signal rst_tb               : std_logic;

    signal spwm_out_tb          : std_logic;
    signal sine_out_tb          : std_logic_vector(47 downto 0);
    signal triangular_out_tb    : std_logic_vector(47 downto 0);

    signal sysclk_p_tb          : std_logic;
    signal sysclk_n_tb          : std_logic;
    signal pmod_in_tb           : std_logic;
    signal gpio_led0_tb         : std_logic;
    signal gpio_sw_c_tb         : std_logic := '0'; 

    signal serial_data_out_tb   : std_logic_vector(0 to 4);
    signal serial_curr_L2_out_tb: std_logic;

begin

    ----------------------------------------------------
    -- Clock and Reset Generation
    ----------------------------------------------------
    clk_tb <= not clk_tb after CLK_PERIOD / 2;

    sysclk_p_tb <= clk_tb;
    sysclk_n_tb <= not clk_tb;

    reset_process: process
    begin
        rst_tb <= '1';
        wait for CLK_PERIOD * 100;
        rst_tb <= '0';
        wait;
    end process;

    ----------------------------------------------------
    -- SPWM Generator Instantiation 
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

    pmod_in_tb <= spwm_out_tb;

    ----------------------------------------------------
    -- UUT HIL instantiation
    ----------------------------------------------------
    -- UUT_HIL : entity work.HIL_TOP
    --     port map (
    --         SYSCLK_P         => sysclk_p_tb,
    --         SYSCLK_N         => sysclk_n_tb,
    --         PMOD6_PIN1_R     => pmod_in_tb,
    --         GPIO_LED0        => gpio_led0_tb,
    --         GPIO_SW_C        => gpio_sw_c_tb,
    --         Serial_data_out  => serial_data_out_tb
    --     );

    UUT_HIL : entity work.HIL_TOP
        port map (
            SYSCLK_P         => sysclk_p_tb,
            SYSCLK_N         => sysclk_n_tb,
            PMOD6_PIN1_R     => pmod_in_tb,
            GPIO_LED0        => gpio_led0_tb,
            GPIO_SW_C        => gpio_sw_c_tb,
            FT4232_B_UART_RX  => serial_curr_L2_out_tb,
            PMOD6_PIN3_R => open
        );

    -- tb_HIL_TOP.vhd (dentro da arquitetura)

    ----------------------------------------------------
    -- Processo para salvar os dados em .csv
    ----------------------------------------------------
    -- csv_writer_process: process
    --     -- Variáveis para manipulação de ficheiros de texto
    --     file csv_file           : TEXT;
    --     variable L              : LINE;
    --     -- Variável para controlar o intervalo de amostragem
    --     variable sample_counter : integer := 0;
    --     constant SAMPLE_PERIOD_CYCLES : integer := 200; -- Amostrar a cada 200 ciclos (200 * 5ns = 1us)
    -- begin
    --     -- Abrir o ficheiro para escrita e escrever o cabeçalho
    --     file_open(csv_file, "output_data.csv", WRITE_MODE);
    --     write(L, string'("Tempo(us),SPWM_In,Busy_Out"));
    --     -- Adicionar cabeçalhos para os 5 sinais seriais
    --     for i in 0 to 4 loop
    --         write(L, string'(",Serial_Out_") & integer'image(i));
    --     end loop;
    --     writeline(csv_file, L);

    --     -- Loop principal de amostragem e escrita
    --     loop
    --         wait until rising_edge(clk_tb);
    --         if rst_tb = '0' then -- Só começa a escrever depois do reset
    --             if sample_counter < SAMPLE_PERIOD_CYCLES - 1 then
    --                 sample_counter := sample_counter + 1;
    --             else
    --                 sample_counter := 0; -- Reinicia o contador

    --                 -- Escreve o tempo atual em microssegundos
    --                 write(L, real(NOW / 1 us));

    --                 -- Escreve os sinais de 1 bit
    --                 write(L, string'("," & std_ulogic'image(spwm_out_tb)(2)));
    --                 write(L, string'("," & std_ulogic'image(gpio_led0_tb)(2)));

    --                 -- Escreve os 5 sinais de saída serial
    --                 for i in 0 to 4 loop
    --                     write(L, string'("," & std_ulogic'image(serial_data_out_tb(i))(2)));
    --                 end loop;

    --                 -- Escreve a linha completa no ficheiro
    --                 writeline(csv_file, L);
    --             end if;
    --         end if;
    --     end loop;
    -- end process;

    ----------------------------------------------------
    -- End simulation stimulus
    ----------------------------------------------------
    simulation_killer: process
    begin
        wait for 500 ms;
        finish;
    end process;

end architecture sim;