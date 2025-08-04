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

use work.SolverPkg.all;

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

    signal Xvec_current_sig_tb  : vector_fp_t(0 to  4);

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
    -- HIL Top Instantiation 
    ----------------------------------------------------
    UUT_HIL : entity work.HIL_TOP
        port map (
            SYSCLK_P         => sysclk_p_tb,
            SYSCLK_N         => sysclk_n_tb,
            PMOD6_PIN1_R     => pmod_in_tb,
            FT4232_B_UART_RX => open,
            PMOD5_PIN1_R     => open,
            PMOD5_PIN2_R     => open,
            PMOD5_PIN3_R     => open,
            PMOD5_PIN4_R     => open,
            PMOD5_PIN7_R     => open,
            PMOD4_PIN1_R     => open,
            PMOD4_PIN2_R     => open,
            PMOD4_PIN3_R     => open,
            PMOD4_PIN4_R     => open,
            PMOD4_PIN7_R     => open,
            GPIO_LED0        => open
        );

    -- Note: Internal signal access may require simulator-specific syntax
    -- Xvec_current_sig_tb <= UUT_HIL.Xvec_current_o_sig;

    ----------------------------------------------------
    -- End simulation stimulus
    ----------------------------------------------------
    simulation_killer: process
    begin
        wait for 500 ms;
        finish;
    end process;

end architecture sim;