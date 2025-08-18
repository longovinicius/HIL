--! \file		FixedToPwmConverter.vhd
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

entity FixedToPwmConverter is
    generic (
        CLK_FREQ                : integer := 200_000_000;
        PWM_RESOLUTION_BITS     : integer := 10;
        FP_INPUT_BITS           : integer := 42;
        FP_FRACTION_BITS        : integer := 28
    );
    port (
        sysclk            : in std_logic;
        reset_n           : in std_logic;
        fixed_point_in    : in std_logic_vector(FP_INPUT_BITS - 1 downto 0);
        pwm_out           : out std_logic
    );
end entity FixedToPwmConverter;

architecture rtl of FixedToPwmConverter is

    --------------------------------------------------------------------------
    -- Constants
    --------------------------------------------------------------------------
    constant PWM_PERIOD         : integer := 2**PWM_RESOLUTION_BITS;
    constant PWM_MAX_COMP_VAL   : integer := PWM_PERIOD - 1;
    constant SIGNED_UPPER_LIMIT : integer := 2**(PWM_RESOLUTION_BITS - 1) - 1;
    constant SIGNED_LOWER_LIMIT : integer := -2**(PWM_RESOLUTION_BITS - 1);

    --------------------------------------------------------------------------
    -- Signals
    --------------------------------------------------------------------------
    signal pwm_counter          : integer range 0 to PWM_PERIOD - 1 := 0;
    signal next_compare_value   : unsigned(PWM_RESOLUTION_BITS - 1 downto 0); 
    signal active_compare_reg   : unsigned(PWM_RESOLUTION_BITS - 1 downto 0); 

begin

    --------------------------------------------------------------------------
    -- Input Signal Mapping and Scaling
    --------------------------------------------------------------------------
    Input_Mapping_Process: process(fixed_point_in)
        variable int_part_signed : signed(FP_INPUT_BITS - 1 downto 0);
        variable int_val         : integer;
    begin
        int_part_signed := signed(fixed_point_in);
        int_val := to_integer(shift_right(int_part_signed, FP_FRACTION_BITS));

        if int_val > SIGNED_UPPER_LIMIT then
            next_compare_value <= to_unsigned(PWM_MAX_COMP_VAL, PWM_RESOLUTION_BITS);
        elsif int_val < SIGNED_LOWER_LIMIT then
            next_compare_value <= (others => '0');
        else
            next_compare_value <= to_unsigned(int_val + (PWM_PERIOD / 2), PWM_RESOLUTION_BITS);
        end if;
    end process;

    --------------------------------------------------------------------------
    -- PWM Generator and Double-Buffering Logic
    --------------------------------------------------------------------------
    PWM_Generator_Process: process(sysclk)
    begin
        if rising_edge(sysclk) then
            if reset_n = '0' then
                pwm_counter <= 0;
                active_compare_reg <= to_unsigned(PWM_PERIOD / 2, PWM_RESOLUTION_BITS);
            else
                if pwm_counter = PWM_PERIOD - 1 then
                    pwm_counter <= 0;
                    active_compare_reg <= next_compare_value;
                else
                    pwm_counter <= pwm_counter + 1;
                end if;
            end if;
        end if;
    end process;

    pwm_out <= '1' when pwm_counter < to_integer(active_compare_reg) else '0';

end architecture rtl;