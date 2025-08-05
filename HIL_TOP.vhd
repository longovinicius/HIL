--! \file		HIL_TOP.vhd
--!
--! \brief		
--!
--! \author		Vinícius de Carvalho Monteiro Longo (longo.vinicius@gmail.com)
--! \date       23-07-2025
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
--!				- 1.0	23-07-2025	<longo.vinicius@gmail.com>
--!				First revision.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.SolverPkg.all;

entity HIL_TOP is
    port (
        SYSCLK_P                : in std_logic;
        SYSCLK_N                : in std_logic;

        -- Digital Input
        PMOD6_PIN1_R            : in std_logic;

        -- Digital Output
        FT4232_B_UART_RX        : out std_logic;

        -- Analog Output
        PMOD4_PIN1_R            : out std_logic;
        PMOD4_PIN2_R            : out std_logic;
        PMOD4_PIN3_R            : out std_logic;
        PMOD4_PIN4_R            : out std_logic;
        PMOD4_PIN7_R            : out std_logic;
        
        -- LED
        GPIO_LED0               : out std_logic
);
end entity HIL_TOP;

architecture arch of HIL_TOP is
    --------------------------------------------------------------------------
    -- Constants
    --------------------------------------------------------------------------
    constant CLK_FREQ           : integer := 250_000_000;
    constant RESET_TRSHD        : integer := 100;

    constant N_SS               : natural := 5;
    constant N_IN               : natural := 2;
    constant VDC_VOLTAGE        : integer := 400;

    constant SIMUL_PERIOD       : real    := 1.0e-7;  
    constant START_PERIOD       : integer := integer(SIMUL_PERIOD * real(CLK_FREQ));

    constant SERIAL_BAUD_RATE   : integer := 3_000_000; 
    constant SERIAL_INTERVAL_US : integer := 25;
    constant SERIAL_STATE_SENT  : integer := 4; 
    constant PWM_RESOLUTION     : integer := 12;
    
    constant L1                 : real := 1.0e-3;
    constant R1                 : real := 0.1;
    constant Cf                 : real := 3.3e-6;
    constant L2                 : real := 0.92e-3;
    constant R2                 : real := 0.1;
    constant Cd                 : real := 1.65e-6;
    constant Rd                 : real := 25.9;
    constant Ld                 : real := 5.1e-3;
    constant Ts                 : real := SIMUL_PERIOD;

    constant a00                : real := 1.0 - (R1/L1)*Ts; 
    constant a03                : real := (-1.0/L1)*Ts; 
    constant a13                : real := (1.0/Ld)*Ts;  
    constant a14                : real := (-1.0/Ld)*Ts; 
    constant a22                : real := 1.0 - (R2/L2)*Ts; 
    constant a23                : real := (1.0/L2)*Ts; 
    constant a30                : real := (1.0/Cf)*Ts; 
    constant a31                : real := (-1.0/Cf)*Ts; 
    constant a32                : real := (-1.0/Cf)*Ts; 
    constant a33                : real := 1.0 - (1.0/(Cf*Rd))*Ts; 
    constant a34                : real := (1.0/(Cf*Rd))*Ts; 
    constant a41                : real := (1.0/Cd)*Ts;
    constant a43                : real := (1.0/(Cd*Rd))*Ts; 
    constant a44                : real := 1.0 - (1.0/(Cd*Rd))*Ts; 
    constant b00                : real := (1.0/L1)*Ts;


    constant AMATRIX_C : matrix_fp_t(0 to N_SS - 1, 0 to N_SS - 1) := (
        (to_fp(a00), to_fp(0.0), to_fp(0.0), to_fp(a03), to_fp(0.0)),
        (to_fp(0.0), to_fp(1.0), to_fp(0.0), to_fp(a13), to_fp(a14)),
        (to_fp(0.0), to_fp(0.0), to_fp(a22), to_fp(a23), to_fp(0.0)),
        (to_fp(a30), to_fp(a31), to_fp(a32), to_fp(a33), to_fp(a34)),
        (to_fp(0.0), to_fp(a41), to_fp(0.0), to_fp(a43), to_fp(a44))
    );
    constant BMATRIX_C : matrix_fp_t(0 to N_SS - 1, 0 to N_IN - 1) := (
        (to_fp(b00), to_fp(0.0)),
        (to_fp(0.0), to_fp(0.0)),
        (to_fp(0.0), to_fp(0.0)),
        (to_fp(0.0), to_fp(0.0)),
        (to_fp(0.0), to_fp(0.0))
    );
    constant XVEC_INITIAL_C : vector_fp_t(0 to N_SS - 1) := (
        to_fp(0.0), to_fp(0.0), to_fp(0.0), to_fp(0.0), to_fp(0.0)
    );

    --------------------------------------------------------------------------
    -- Signals
    --------------------------------------------------------------------------
    signal sysclk_250mhz        : std_logic;
    signal reset_n              : std_logic := '0';
    signal reset_ctr            : unsigned(16 downto 0) := (others => '0');
    signal inverver_signal      : std_logic_vector(FP_TOTAL_BITS-1 downto 0);
    signal Xvec_current_o_sig   : vector_fp_t(0 to N_SS - 1);
    signal busy_o_sig           : std_logic;
    signal start_signal         : std_logic;
    signal start_ctr            : unsigned(26 downto 0) := (others => '0');
    signal Uvector              : vector_fp_t(0 to N_IN - 1) := (others => (others => '0') );
    signal pmod_sync_s1         : std_logic;
    signal pmod_sync_s2         : std_logic;

    signal serial_out_vector    : std_logic_vector(0 to N_SS - 1);
    signal pwm_out_vector       : std_logic_vector(0 to N_SS - 1);

begin

    Synchronizer_Process: process (sysclk_250mhz)
    begin
        if rising_edge(sysclk_250mhz) then
            pmod_sync_s1 <= PMOD6_PIN1_R;
            pmod_sync_s2 <= pmod_sync_s1;
        end if;
    end process;

    --------------------------------------------------------------------------
    -- PLL
    --------------------------------------------------------------------------
    clock_gen_inst : entity work.clk_wiz_0
        port map(
            clk_in1_p => SYSCLK_P,
            clk_in1_n => SYSCLK_N,
            clk_out1  => sysclk_250mhz
        );

    --------------------------------------------------------------------------
    -- reset_n inicialization
    --------------------------------------------------------------------------
    process (sysclk_250mhz)
    begin
        if rising_edge(sysclk_250mhz) then
            if reset_ctr < RESET_TRSHD then
                reset_ctr <= reset_ctr + 1;
                reset_n   <= '0';
            else
                reset_n   <= '1';
            end if;
        end if;
    end process;

    --------------------------------------------------------------------------
    -- Periodic start signal
    --------------------------------------------------------------------------
    process (sysclk_250mhz)
    begin
        if rising_edge(sysclk_250mhz) then
            if reset_n = '1' then
                if start_ctr < START_PERIOD - 1 then
                    start_ctr     <= start_ctr + 1;
                    start_signal  <= '0';
                else
                    start_ctr     <= (others => '0');
                    start_signal  <= '1'; 
                end if;
            else
                start_ctr     <= (others => '0');
                start_signal  <= '0';
            end if;
        end if;
    end process;

    --------------------------------------------------------------------------
    -- PWM to Voltage
    --------------------------------------------------------------------------
    PWMToVoltage_inst : entity work.PWMToVoltage
    generic map (
        VDC_VOLTAGE         => VDC_VOLTAGE,
        OUTPUT_BIT_WIDTH    => FP_TOTAL_BITS,
        FP_FRACTION_BITS    => FP_FRACTION_BITS
    )
    port map (
        sysclk              => sysclk_250mhz,
        pwm_signal          => pmod_sync_s2,
        v_in                => inverver_signal
    );
    Uvector(0) <= inverver_signal;

    --------------------------------------------------------------------------
    -- LSM
    --------------------------------------------------------------------------
    LSM_inst : entity work.LinearSolverManager
    generic map (
        N_SS            => N_SS,
        N_IN            => N_IN
    )
    port map (
        sysclk         => sysclk_250mhz,
        reset_n        => reset_n,
        init_calc_i    => start_signal,
        Amatrix_i      => AMATRIX_C,
        Bmatrix_i      => BMATRIX_C,
        Xvec_initial   => XVEC_INITIAL_C,
        Uvector_i      => Uvector,
        Xvec_current_o => Xvec_current_o_sig,
        busy_o         => busy_o_sig
    );
    
    --------------------------------------------------------------------------
    -- Serial Manager Generators 
    --------------------------------------------------------------------------
    Serial_Generators: for i in 0 to N_SS - 1 generate
        SerialManager_inst : entity work.SerialManager
            generic map (
                CLK_FREQ          => CLK_FREQ,
                SEND_INTERVAL_US  => SERIAL_INTERVAL_US,
                BAUD_RATE         => SERIAL_BAUD_RATE
            )
            port map (
                sysclk            => sysclk_250mhz,
                reset_n           => reset_n,
                data_in_i         => Xvec_current_o_sig(i),
                tx_o              => serial_out_vector(i)
            );
    end generate Serial_Generators;

    --------------------------------------------------------------------------
    -- Fixed Point to PWM Converter Generators 
    --------------------------------------------------------------------------
    PWM_Generators: for i in 0 to N_SS - 1 generate
        PWM_Converter_inst : entity work.FixedToPwmConverter
            generic map (
                CLK_FREQ                => CLK_FREQ,
                PWM_RESOLUTION_BITS     => PWM_RESOLUTION,
                FP_INPUT_BITS           => FP_TOTAL_BITS,
                FP_FRACTION_BITS        => FP_FRACTION_BITS
            )
            port map (
                sysclk            => sysclk_250mhz,
                reset_n           => reset_n,
                fixed_point_in    => Xvec_current_o_sig(i),
                pwm_out           => pwm_out_vector(i)
            );
    end generate PWM_Generators;

    --------------------------------------------------------------------------
    -- Output signals
    --------------------------------------------------------------------------
    GPIO_LED0 <= busy_o_sig;

    FT4232_B_UART_RX <= serial_out_vector(SERIAL_STATE_SENT);

    PMOD4_PIN1_R <= pwm_out_vector(0);
    PMOD4_PIN2_R <= pwm_out_vector(1);
    PMOD4_PIN3_R <= pwm_out_vector(2);
    PMOD4_PIN4_R <= pwm_out_vector(3);
    PMOD4_PIN7_R <= pwm_out_vector(4);

end architecture arch;
