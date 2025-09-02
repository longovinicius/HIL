--! \file       grid_gen.vhd
--! \brief      Gerador de tensão senoidal da rede elétrica em ponto fixo.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.SolverPkg.all;

entity GridGen is
    generic (
        CLK_FREQ          : integer := 250_000_000; 
        GRID_FREQ         : real    := 50.0;       
        GRID_PEAK_VOLTAGE : real    := 311.13      
    );
    port (
        clk               : in  std_logic;
        reset_n           : in  std_logic;
        grid_voltage_o    : out fixed_point_data_t 
    );
end entity GridGen;

architecture rtl of GridGen is

    constant LUT_SIZE           : integer := 256;
    constant LUT_ADDR_WIDTH     : integer := 8; 
    constant PHASE_ACC_WIDTH    : integer := 32;

    -- 2^32 = 4294967296, divided by 1000 so it doesn't cause overflow
    constant SCALE_FACTOR       : integer := 1000;
    constant FREQ_RATIO_SCALED  : integer := integer((GRID_FREQ * real(SCALE_FACTOR)) / real(CLK_FREQ) * 4294967296.0);
    
    constant PHASE_INCREMENT    : unsigned(PHASE_ACC_WIDTH-1 downto 0) := 
        to_unsigned(FREQ_RATIO_SCALED / SCALE_FACTOR, PHASE_ACC_WIDTH);

    constant GRID_PEAK_FP       : fixed_point_data_t := to_fp(GRID_PEAK_VOLTAGE);

    type sine_lut_t is array (0 to LUT_SIZE-1) of signed(15 downto 0);
    constant SINE_LUT : sine_lut_t := (
        to_signed(0, 16), to_signed(804, 16), to_signed(1608, 16), to_signed(2410, 16), to_signed(3212, 16), to_signed(4011, 16), 
        to_signed(4808, 16), to_signed(5602, 16), to_signed(6393, 16), to_signed(7179, 16), to_signed(7962, 16), to_signed(8739, 16), 
        to_signed(9512, 16), to_signed(10278, 16), to_signed(11039, 16), to_signed(11793, 16), to_signed(12539, 16), to_signed(13279, 16), 
        to_signed(14010, 16), to_signed(14732, 16), to_signed(15446, 16), to_signed(16151, 16), to_signed(16846, 16), to_signed(17530, 16), 
        to_signed(18204, 16), to_signed(18868, 16), to_signed(19519, 16), to_signed(20159, 16), to_signed(20787, 16), to_signed(21403, 16), 
        to_signed(22005, 16), to_signed(22594, 16), to_signed(23170, 16), to_signed(23731, 16), to_signed(24279, 16), to_signed(24811, 16), 
        to_signed(25329, 16), to_signed(25832, 16), to_signed(26319, 16), to_signed(26790, 16), to_signed(27245, 16), to_signed(27683, 16), 
        to_signed(28105, 16), to_signed(28510, 16), to_signed(28898, 16), to_signed(29268, 16), to_signed(29621, 16), to_signed(29956, 16), 
        to_signed(30273, 16), to_signed(30571, 16), to_signed(30852, 16), to_signed(31113, 16), to_signed(31356, 16), to_signed(31580, 16), 
        to_signed(31785, 16), to_signed(31971, 16), to_signed(32137, 16), to_signed(32285, 16), to_signed(32412, 16), to_signed(32521, 16), 
        to_signed(32609, 16), to_signed(32678, 16), to_signed(32728, 16), to_signed(32757, 16), to_signed(32767, 16), to_signed(32757, 16), 
        to_signed(32728, 16), to_signed(32678, 16), to_signed(32609, 16), to_signed(32521, 16), to_signed(32412, 16), to_signed(32285, 16), 
        to_signed(32137, 16), to_signed(31971, 16), to_signed(31785, 16), to_signed(31580, 16), to_signed(31356, 16), to_signed(31113, 16), 
        to_signed(30852, 16), to_signed(30571, 16), to_signed(30273, 16), to_signed(29956, 16), to_signed(29621, 16), to_signed(29268, 16), 
        to_signed(28898, 16), to_signed(28510, 16), to_signed(28105, 16), to_signed(27683, 16), to_signed(27245, 16), to_signed(26790, 16), 
        to_signed(26319, 16), to_signed(25832, 16), to_signed(25329, 16), to_signed(24811, 16), to_signed(24279, 16), to_signed(23731, 16), 
        to_signed(23170, 16), to_signed(22594, 16), to_signed(22005, 16), to_signed(21403, 16), to_signed(20787, 16), to_signed(20159, 16), 
        to_signed(19519, 16), to_signed(18868, 16), to_signed(18204, 16), to_signed(17530, 16), to_signed(16846, 16), to_signed(16151, 16), 
        to_signed(15446, 16), to_signed(14732, 16), to_signed(14010, 16), to_signed(13279, 16), to_signed(12539, 16), to_signed(11793, 16), 
        to_signed(11039, 16), to_signed(10278, 16), to_signed(9512, 16), to_signed(8739, 16), to_signed(7962, 16), to_signed(7179, 16), 
        to_signed(6393, 16), to_signed(5602, 16), to_signed(4808, 16), to_signed(4011, 16), to_signed(3212, 16), to_signed(2410, 16), 
        to_signed(1608, 16), to_signed(804, 16), to_signed(0, 16), to_signed(-804, 16), to_signed(-1608, 16), to_signed(-2410, 16), 
        to_signed(-3212, 16), to_signed(-4011, 16), to_signed(-4808, 16), to_signed(-5602, 16), to_signed(-6393, 16), to_signed(-7179, 16), 
        to_signed(-7962, 16), to_signed(-8739, 16), to_signed(-9512, 16), to_signed(-10278, 16), to_signed(-11039, 16), to_signed(-11793, 16), 
        to_signed(-12539, 16), to_signed(-13279, 16), to_signed(-14010, 16), to_signed(-14732, 16), to_signed(-15446, 16), to_signed(-16151, 16), 
        to_signed(-16846, 16), to_signed(-17530, 16), to_signed(-18204, 16), to_signed(-18868, 16), to_signed(-19519, 16), to_signed(-20159, 16), 
        to_signed(-20787, 16), to_signed(-21403, 16), to_signed(-22005, 16), to_signed(-22594, 16), to_signed(-23170, 16), to_signed(-23731, 16), 
        to_signed(-24279, 16), to_signed(-24811, 16), to_signed(-25329, 16), to_signed(-25832, 16), to_signed(-26319, 16), to_signed(-26790, 16), 
        to_signed(-27245, 16), to_signed(-27683, 16), to_signed(-28105, 16), to_signed(-28510, 16), to_signed(-28898, 16), to_signed(-29268, 16), 
        to_signed(-29621, 16), to_signed(-29956, 16), to_signed(-30273, 16), to_signed(-30571, 16), to_signed(-30852, 16), to_signed(-31113, 16), 
        to_signed(-31356, 16), to_signed(-31580, 16), to_signed(-31785, 16), to_signed(-31971, 16), to_signed(-32137, 16), to_signed(-32285, 16), 
        to_signed(-32412, 16), to_signed(-32521, 16), to_signed(-32609, 16), to_signed(-32678, 16), to_signed(-32728, 16), to_signed(-32757, 16), 
        to_signed(-32767, 16), to_signed(-32757, 16), to_signed(-32728, 16), to_signed(-32678, 16), to_signed(-32609, 16), to_signed(-32521, 16), 
        to_signed(-32412, 16), to_signed(-32285, 16), to_signed(-32137, 16), to_signed(-31971, 16), to_signed(-31785, 16), to_signed(-31580, 16), 
        to_signed(-31356, 16), to_signed(-31113, 16), to_signed(-30852, 16), to_signed(-30571, 16), to_signed(-30273, 16), to_signed(-29956, 16), 
        to_signed(-29621, 16), to_signed(-29268, 16), to_signed(-28898, 16), to_signed(-28510, 16), to_signed(-28105, 16), to_signed(-27683, 16), 
        to_signed(-27245, 16), to_signed(-26790, 16), to_signed(-26319, 16), to_signed(-25832, 16), to_signed(-25329, 16), to_signed(-24811, 16), 
        to_signed(-24279, 16), to_signed(-23731, 16), to_signed(-23170, 16), to_signed(-22594, 16), to_signed(-22005, 16), to_signed(-21403, 16), 
        to_signed(-20787, 16), to_signed(-20159, 16), to_signed(-19519, 16), to_signed(-18868, 16), to_signed(-18204, 16), to_signed(-17530, 16), 
        to_signed(-16846, 16), to_signed(-16151, 16), to_signed(-15446, 16), to_signed(-14732, 16), to_signed(-14010, 16), to_signed(-13279, 16), 
        to_signed(-12539, 16), to_signed(-11793, 16), to_signed(-11039, 16), to_signed(-10278, 16), to_signed(-9512, 16), to_signed(-8739, 16), 
        to_signed(-7962, 16), to_signed(-7179, 16), to_signed(-6393, 16), to_signed(-5602, 16), to_signed(-4808, 16), to_signed(-4011, 16), 
        to_signed(-3212, 16), to_signed(-2410, 16), to_signed(-1608, 16), to_signed(-804, 16)
    );

    signal phase_accumulator : unsigned(PHASE_ACC_WIDTH-1 downto 0);
    signal lut_address       : unsigned(LUT_ADDR_WIDTH-1 downto 0);
    signal sine_from_lut     : signed(15 downto 0);
    signal temp_mult_res     : signed(FP_TOTAL_BITS + 15 downto 0);
    signal temp_mult_res2     : signed(FP_TOTAL_BITS + 15 downto 0);

begin

    Grid_Voltage_Process: process(clk)

    begin
        if rising_edge(clk) then
            if reset_n = '0' then
                phase_accumulator <= (others => '0');
                grid_voltage_o    <= (others => '0');
            else
                phase_accumulator <= phase_accumulator + PHASE_INCREMENT;
                lut_address <= phase_accumulator(PHASE_ACC_WIDTH-1 downto PHASE_ACC_WIDTH-LUT_ADDR_WIDTH);
                sine_from_lut <= SINE_LUT(to_integer(lut_address));
                temp_mult_res <= sine_from_lut * signed(GRID_PEAK_FP);
                temp_mult_res2 <= temp_mult_res;
                grid_voltage_o <= std_logic_vector(resize(shift_right(temp_mult_res2, 15), FP_TOTAL_BITS));
            end if;
        end if;
    end process Grid_Voltage_Process;

end architecture rtl;