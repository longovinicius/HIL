--! \file		tb_FixedToPwmConverter.vhd
--!
--! \brief		
--!
--! \author		Vinícius de Carvalho Monteiro Longo (longo.vinicius@gmail.com)
--! \date       01-08-2025
--!
--! \version    1.0
--!
--! \copyright	Copyright (c) 2025 - All Rights reserved.
--!
--! \note		Target devices : No specific target
--! \note		Tool versions  : No specific tool
--! \note		Dependencies   : No specific dependencies
--!
--! \ingroup	None
--! \warning	None
--!
--! \note		Revisions:
--!				- 1.0	01-08-2025	<longo.vinicius@gmail.com>
--!				First revision.
--------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.finish;

--------------------------------------------------------------------------
-- Entity declaration
--------------------------------------------------------------------------
entity tb_FixedToPwmConverter is
end entity tb_FixedToPwmConverter;

--------------------------------------------------------------------------
-- Architecture
--------------------------------------------------------------------------
architecture sim of tb_FixedToPwmConverter is

    --------------------------------------------------------------------------
    -- Constants
    --------------------------------------------------------------------------
    constant CLK_FREQ_TB            : integer := 200_000_000;
    constant PWM_RESOLUTION_BITS_TB : integer := 10;
    constant FP_INPUT_BITS_TB       : integer := 42;
    constant FP_FRACTION_BITS_TB    : integer := 28;
    constant CLK_PERIOD             : time    := 5 ns;

    -- Value +256.0
    constant C_FP_P256 : std_logic_vector(FP_INPUT_BITS_TB - 1 downto 0) := B"0_0000100000000_0000000000000000000000000000";
    -- Value -256.0 2s complement
    constant C_FP_N256 : std_logic_vector(FP_INPUT_BITS_TB - 1 downto 0) := B"1_1111011111111_0000000000000000000000000000";
    -- Value +600.0
    constant C_FP_P600 : std_logic_vector(FP_INPUT_BITS_TB - 1 downto 0) := B"0_0010010110000_0000000000000000000000000000";
    -- Value -600.0 2s complement
    constant C_FP_N600 : std_logic_vector(FP_INPUT_BITS_TB - 1 downto 0) := B"1_1101101010000_0000000000000000000000000000";
    -- Value +511.0
    constant C_FP_P511 : std_logic_vector(FP_INPUT_BITS_TB - 1 downto 0) := B"0_0001111111111_0000000000000000000000000000";
    -- Value 0.0
    constant C_FP_ZERO : std_logic_vector(FP_INPUT_BITS_TB - 1 downto 0) := (others => '0');

    --------------------------------------------------------------------------
    -- Signals
    --------------------------------------------------------------------------
    signal clk_tb             : std_logic := '0';
    signal reset_n_tb         : std_logic;
    signal fixed_point_in_tb  : std_logic_vector(FP_INPUT_BITS_TB - 1 downto 0);
    signal pwm_out_tb         : std_logic;

begin

    --------------------------------------------------------------------------
    -- Clock gen
    --------------------------------------------------------------------------
    clk_tb <= not clk_tb after CLK_PERIOD / 2;

    --------------------------------------------------------------------------
    -- DUT
    --------------------------------------------------------------------------
    UUT : entity work.FixedToPwmConverter
        generic map (
            CLK_FREQ                => CLK_FREQ_TB,
            PWM_RESOLUTION_BITS     => PWM_RESOLUTION_BITS_TB,
            FP_INPUT_BITS           => FP_INPUT_BITS_TB,
            FP_FRACTION_BITS        => FP_FRACTION_BITS_TB
        )
        port map (
            sysclk            => clk_tb,
            reset_n           => reset_n_tb,
            fixed_point_in    => fixed_point_in_tb,
            pwm_out           => pwm_out_tb
        );

    --------------------------------------------------------------------------
    -- DUT input Stimulus
    --------------------------------------------------------------------------
    Stimulus : process
    begin
        reset_n_tb <= '0';
        fixed_point_in_tb <= C_FP_ZERO;
        wait for CLK_PERIOD * 10;
        
        reset_n_tb <= '1';
        report "TEST: Input 0.0 - Expected Duty Cycle 50%";
        fixed_point_in_tb <= C_FP_ZERO;
        wait for CLK_PERIOD * 10000;

        report "TEST: Input +256.0 - Expected Duty Cycle 75%";
        fixed_point_in_tb <= C_FP_P256;
        wait for CLK_PERIOD * 10000;

        report "TEST: Input -256.0 - Expected Duty Cycle 25%";
        fixed_point_in_tb <= C_FP_N256;
        wait for CLK_PERIOD * 10000;

        report "TEST: Input +600.0 - Expected Duty Cycle 100% (saturated)";
        fixed_point_in_tb <= C_FP_P600;
        wait for CLK_PERIOD * 10000;

        report "TEST: Input -600.0 - Expected Duty Cycle 0% (saturated)";
        fixed_point_in_tb <= C_FP_N600;
        wait for CLK_PERIOD * 10000;

        report "TEST: Input +511.0 - Expected Duty Cycle ~99.9%";
        fixed_point_in_tb <= C_FP_P511;
        wait for CLK_PERIOD * 10000;

        report "End of tests.";
        finish;
        wait;
    end process Stimulus;

end architecture sim;