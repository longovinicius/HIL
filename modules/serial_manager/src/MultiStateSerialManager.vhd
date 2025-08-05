--! \file		SerialManager.vhd
--!
--! \brief		Serial manager for transmitting 5 state values
--!
--! \author		Vinícius de Carvalho Monteiro Longo (longo.vinicius@gmail.com)
--! \date       05-08-2025
--!
--! \version    2.1
--!
--! \copyright	Copyright (c) 2024 WEG - All Rights reserved.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.SolverPkg.all;

entity MultiStateSerialManager is
    generic (
        CLK_FREQ          : integer := 200_000_000;
        SEND_INTERVAL_US  : integer := 500;
        BAUD_RATE         : integer := 1_042_000
    );
    port (
        sysclk            : in std_logic;
        reset_n           : in std_logic;
        states_data_i     : in vector_fp_t(0 to 4);
        tx_o              : out std_logic
    );
end entity MultiStateSerialManager;

architecture rtl of MultiStateSerialManager is

--------------------------------------------------------------------------
-- Constants
--------------------------------------------------------------------------
    constant SEND_INTERVAL_CYCLES : integer := (CLK_FREQ / 1_000_000) * SEND_INTERVAL_US;
    constant BAUD_DIVISOR_C       : integer := (CLK_FREQ / BAUD_RATE) - 1;
    constant HEADER_BYTE          : std_logic_vector(7 downto 0) := x"FA"; 
    constant TOTAL_BYTES_TO_SEND  : integer := 31; -- 1 header + (5 states × 6 bytes each)

--------------------------------------------------------------------------
-- Signals
--------------------------------------------------------------------------
    type state_t is (S_IDLE, S_LATCH_DATA, S_SEND_BYTE, S_WAIT_DONE);
    signal fsm_state              : state_t := S_IDLE;

    signal timer_ctr              : integer range 0 to SEND_INTERVAL_CYCLES - 1 := 0;
    signal send_trigger           : std_logic := '0';
    signal latched_packets        : vector_fp_t(0 to 4);
    signal tx_byte_counter        : integer range 0 to TOTAL_BYTES_TO_SEND - 1 := 0;
    signal byte_to_send           : std_logic_vector(7 downto 0);
    signal uart_start             : std_logic := '0';
    signal uart_done              : std_logic;
    signal baud_divisor_sig       : std_logic_vector(15 downto 0);

begin

    baud_divisor_sig <= std_logic_vector(to_unsigned(BAUD_DIVISOR_C, 16));

    --------------------------------------------------------------------------
    -- Timer periódico para disparar transmissões
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
    -- Máquina de estados principal
    --------------------------------------------------------------------------
    Sequencer_FSM: process(sysclk)
    begin
        if rising_edge(sysclk) then
            if reset_n = '0' then
                fsm_state <= S_IDLE;
                tx_byte_counter <= 0;
                uart_start <= '0';
            else
                case fsm_state is
                    when S_IDLE =>
                        uart_start <= '0';
                        if send_trigger = '1' then
                            fsm_state <= S_LATCH_DATA;
                        end if;

                    when S_LATCH_DATA =>
                        latched_packets <= states_data_i;  -- Captura os 5 estados
                        tx_byte_counter <= 0;
                        fsm_state <= S_SEND_BYTE;

                    when S_SEND_BYTE =>
                        uart_start <= '1';
                        fsm_state <= S_WAIT_DONE;

                    when S_WAIT_DONE =>
                        uart_start <= '0';
                        if uart_done = '1' then
                            if tx_byte_counter < TOTAL_BYTES_TO_SEND - 1 then
                                tx_byte_counter <= tx_byte_counter + 1;
                                fsm_state <= S_SEND_BYTE;
                            else
                                fsm_state <= S_IDLE;
                            end if;
                        end if;
                end case;
            end if;
        end if;
    end process;

    --------------------------------------------------------------------------
    -- Seletor de bytes para transmissão
    --------------------------------------------------------------------------
    Byte_Selector_Process: process(tx_byte_counter, latched_packets)
        variable packet_index : integer range 0 to 4;
        variable byte_index   : integer range 0 to 5;
        variable current_packet : fixed_point_data_t;
    begin
        if tx_byte_counter = 0 then
            byte_to_send <= HEADER_BYTE;  -- Primeiro byte é o header (0xFA)
        else
            packet_index := (tx_byte_counter - 1) / 6;  -- Qual estado (0-4)
            byte_index   := (tx_byte_counter - 1) mod 6; -- Qual byte do estado (0-5)
            current_packet := latched_packets(packet_index);

            case byte_index is
                when 0 => byte_to_send <= current_packet(7 downto 0);
                when 1 => byte_to_send <= current_packet(15 downto 8);
                when 2 => byte_to_send <= current_packet(23 downto 16);
                when 3 => byte_to_send <= current_packet(31 downto 24);
                when 4 => byte_to_send <= current_packet(39 downto 32);
                when 5 => byte_to_send <= "000000" & current_packet(41 downto 40);
                when others => byte_to_send <= (others => '0');
            end case;
        end if;
    end process;
    
    --------------------------------------------------------------------------
    -- Instância do transmissor UART
    --------------------------------------------------------------------------
    uart_tx_inst : entity work.UartTX
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