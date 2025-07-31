--! \file		SerialManager.vhd
--!
--! \brief		
--!
--! \author		Vinícius de Carvalho Monteiro Longo (longo.vinicius@gmail.com)
--! \date       24-07-2025
--!
--! \version    1.0
--!
--! \copyright	Copyright (c) 2024 WEG - All Rights reserved.
--!
--! \note		Target devices : No specific target
--! \note		Tool versions  : No specific tool
--! \note		Dependencies   : No specific dependencies
--!
--! \ingroup	None
--! \warning	None
--!
--! \note		Revisions:
--!				- 1.0	24-07-2025	<longo.vinicius@gmail.com>
--!				First revision.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.SolverPkg.all;

entity SerialManager is
    generic (
        CLK_FREQ          : integer := 100_000_000;
        SEND_INTERVAL_US  : integer := 200;
        BAUD_RATE         : integer := 1_042_000
    );
    port (
        sysclk            : in std_logic;
        reset_n           : in std_logic;
        data_in_i         : in fixed_point_data_t;
        tx_o              : out std_logic
    );
end entity SerialManager;

architecture rtl of SerialManager is

    --------------------------------------------------------------------------
    -- Constants
    --------------------------------------------------------------------------
    constant SEND_INTERVAL_CYCLES : integer := (CLK_FREQ / 1_000_000) * SEND_INTERVAL_US;
    constant BAUD_DIVISOR_C       : integer := (CLK_FREQ / BAUD_RATE);

    --------------------------------------------------------------------------
    -- Signals
    --------------------------------------------------------------------------
    type state_t is (S_IDLE, S_LATCH_DATA, S_SEND_BYTE, S_WAIT_DONE); --S_HEADER 
    signal fsm_state              : state_t := S_IDLE;
    signal timer_ctr              : integer range 0 to SEND_INTERVAL_CYCLES - 1 := 0;
    signal send_trigger           : std_logic := '0';
    signal latched_data           : fixed_point_data_t;
    signal byte_index             : integer range 0 to 6 := 0;
    signal byte_to_send           : std_logic_vector(7 downto 0);
    signal uart_start             : std_logic := '0';
    signal uart_done              : std_logic;
    signal baud_divisor_sig       : std_logic_vector(15 downto 0);

begin

    baud_divisor_sig <= std_logic_vector(to_unsigned(BAUD_DIVISOR_C, 16));

    --------------------------------------------------------------------------
    -- Data transfer trigger
    --------------------------------------------------------------------------
    Periodic_Trigger_Process: process(sysclk)
    begin
        if rising_edge(sysclk) then
            if reset_n = '0' then
                timer_ctr <= 0;
                send_trigger <= '0';
            else
                send_trigger <= '0';
                if timer_ctr < SEND_INTERVAL_CYCLES - 1 then
                    timer_ctr <= timer_ctr + 1;
                else
                    timer_ctr <= 0;
                    send_trigger <= '1';
                end if;
            end if;
        end if;
    end process;

    --------------------------------------------------------------------------
    -- FSM 
    --------------------------------------------------------------------------
    Sequencer_FSM: process(sysclk)
    begin
        if rising_edge(sysclk) then
            if reset_n = '0' then
                fsm_state <= S_IDLE;
                byte_index <= 0;
                uart_start <= '0';
            else
                case fsm_state is
                    when S_IDLE =>
                        uart_start <= '0';
                        if send_trigger = '1' then
                            fsm_state <= S_LATCH_DATA;
                        end if;
                    when S_LATCH_DATA =>
                        latched_data <= data_in_i;
                        byte_index <= 0;
                        fsm_state <= S_SEND_BYTE;
                    when S_SEND_BYTE =>
                        uart_start <= '1';
                        fsm_state <= S_WAIT_DONE;
                    when S_WAIT_DONE =>
                        uart_start <= '0';
                        if uart_done = '1' then
                            if byte_index < 6 then
                                byte_index <= byte_index + 1;
                                fsm_state <= S_SEND_BYTE;
                            else
                                fsm_state <= S_IDLE;
                            end if;
                        end if;
                end case;
            end if;
        end if;
    end process;

    with byte_index select
        byte_to_send <= X"FA"                                   when 0,
                        latched_data(7 downto 0)                when 1,
                        latched_data(15 downto 8)               when 2,
                        latched_data(23 downto 16)              when 3,
                        latched_data(31 downto 24)              when 4,
                        latched_data(39 downto 32)              when 5,
                        "000000" & latched_data(41 downto 40)   when 6,
                        (others => '0')            when others;

    --------------------------------------------------------------------------
    -- Uart TX Instantiation
    --------------------------------------------------------------------------
    uart_tx_inst : entity work.Uart_TX
    generic map(
        DATA_WIDTH      => 8,
        START_BIT       => '0',
        STOP_BIT        => '1'
    )
    port map(
        sysclk          => sysclk,
        reset_n         => reset_n,
        start_i         => uart_start,
        baudrate_i      => baud_divisor_sig, 
        data_i          => byte_to_send,
        tx_o            => tx_o,
        tx_done_o       => uart_done
    );

end architecture rtl;