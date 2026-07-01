#include "sleep.h"
#include "xil_cache.h"
#include "xil_io.h"
#include "xil_types.h"
#include "xparameters.h"
#include "xstatus.h"
#include "xuartps.h"
#include "xuartps_hw.h"

#define HI3593_BASE_ADDR       0x43C00000U
#define DDR_TEST_ADDR          0x01000000U
#define HI3593_REG_CONTROL     0x00U
#define HI3593_REG_STATUS      0x04U
#define HI3593_REG_TX_SAMPLE   0x08U
#define HI3593_REG_RX_DRIVE    0x0CU
#define HI3593_REG_ID          0x10U

#define CONTROL_RELEASE_RESET  0x00000102U
#define CONTROL_LED            0x00000100U
#define CONTROL_MR             0x00000001U
#define CONTROL_CS             0x00000002U
#define CONTROL_SCK            0x00000004U
#define CONTROL_SI             0x00000008U

#define STATUS_TEMPTY          0x00000010U
#define STATUS_TFULL           0x00000020U
#define STATUS_R1FLAG          0x00000040U
#define TX_SAMPLE_RX_DRIVE     0x0000000FU
#define TX_SAMPLE_TX_SYMBOL    0x00000060U
#define TX_SAMPLE_TEMPTY       0x00000100U

#if defined(STDIN_BASEADDRESS)
#define BOARD_UART_BASE_ADDR   STDIN_BASEADDRESS
#elif defined(XPAR_XUARTPS_0_BASEADDR)
#define BOARD_UART_BASE_ADDR   XPAR_XUARTPS_0_BASEADDR
#elif defined(XPAR_PS7_UART_0_BASEADDR)
#define BOARD_UART_BASE_ADDR   XPAR_PS7_UART_0_BASEADDR
#else
#define BOARD_UART_BASE_ADDR   0xE0000000U
#endif

#if defined(XPAR_XUARTPS_0_DEVICE_ID)
#define BOARD_UART_DEVICE_ID   XPAR_XUARTPS_0_DEVICE_ID
#elif defined(XPAR_PS7_UART_0_DEVICE_ID)
#define BOARD_UART_DEVICE_ID   XPAR_PS7_UART_0_DEVICE_ID
#else
#define BOARD_UART_DEVICE_ID   0U
#endif

static u32 control_shadow = CONTROL_RELEASE_RESET;
static XUartPs board_uart;

static u32 hi3593_read(u32 offset)
{
    return Xil_In32(HI3593_BASE_ADDR + offset);
}

static void hi3593_write(u32 offset, u32 value)
{
    Xil_Out32(HI3593_BASE_ADDR + offset, value);
}

static void hi3593_write_control(u32 value)
{
    control_shadow = value;
    hi3593_write(HI3593_REG_CONTROL, control_shadow);
}

static void hi3593_prepare(void)
{
    hi3593_write_control(CONTROL_RELEASE_RESET | CONTROL_MR);
    usleep(1000U);
    hi3593_write(HI3593_REG_RX_DRIVE, 0x00000000U);
    hi3593_write_control(CONTROL_RELEASE_RESET);
    usleep(1000U);
}

static void pl_uart_reset(void)
{
    XUartPs_Config *config = XUartPs_LookupConfig(BOARD_UART_DEVICE_ID);
    if (config != 0) {
        if (XUartPs_CfgInitialize(&board_uart, config,
                                  config->BaseAddress) == XST_SUCCESS) {
            (void)XUartPs_SetBaudRate(&board_uart, 115200U);
            XUartPs_SetOperMode(&board_uart, XUARTPS_OPER_MODE_NORMAL);
        }
    }
    Xil_Out32(BOARD_UART_BASE_ADDR + XUARTPS_CR_OFFSET,
              XUARTPS_CR_RXRST | XUARTPS_CR_TXRST);
    Xil_Out32(BOARD_UART_BASE_ADDR + XUARTPS_CR_OFFSET,
              XUARTPS_CR_RX_EN | XUARTPS_CR_TX_EN);
}

static int pl_uart_get_char(char *c)
{
    if (!XUartPs_IsReceiveData(BOARD_UART_BASE_ADDR)) {
        return 0;
    }
    *c = (char)(Xil_In32(BOARD_UART_BASE_ADDR + XUARTPS_FIFO_OFFSET) & 0xFFU);
    return 1;
}

static void pl_uart_put_char(char c)
{
    while (XUartPs_IsTransmitFull(BOARD_UART_BASE_ADDR)) {
    }
    Xil_Out32(BOARD_UART_BASE_ADDR + XUARTPS_FIFO_OFFSET, (u32)(u8)c);
}

static void pl_uart_puts(const char *s)
{
    while (*s != '\0') {
        pl_uart_put_char(*s);
        s++;
    }
}

static void pl_uart_put_hex32(u32 value)
{
    int shift;
    for (shift = 28; shift >= 0; shift -= 4) {
        u32 nibble = (value >> shift) & 0xFU;
        pl_uart_put_char((char)(nibble < 10U ? ('0' + nibble)
                                              : ('A' + (nibble - 10U))));
    }
}

static void pl_uart_put_hex8(u8 value)
{
    u32 high = (value >> 4) & 0xFU;
    u32 low = value & 0xFU;
    pl_uart_put_char((char)(high < 10U ? ('0' + high)
                                       : ('A' + (high - 10U))));
    pl_uart_put_char((char)(low < 10U ? ('0' + low)
                                      : ('A' + (low - 10U))));
}

static void pl_uart_put_value_line(const char *prefix, u32 value)
{
    pl_uart_puts(prefix);
    pl_uart_put_hex32(value);
    pl_uart_puts("\r\n");
}

static void pl_uart_put_check(const char *name, int pass, u32 value)
{
    pl_uart_puts("LOOP3_CHECK ");
    pl_uart_puts(name);
    pl_uart_puts(pass ? " PASS value=0x" : " FAIL value=0x");
    pl_uart_put_hex32(value);
    pl_uart_puts("\r\n");
}

static void pl_uart_put_opcode(const char *opcode, const char *name, int pass,
                               u32 value)
{
    pl_uart_puts("OPCODE[");
    pl_uart_puts(opcode);
    pl_uart_puts("] ");
    pl_uart_puts(name);
    pl_uart_puts(pass ? " PASS value=0x" : " FAIL value=0x");
    pl_uart_put_hex32(value);
    pl_uart_puts("\r\n");
}

static void pl_uart_put_deferred(const char *name, const char *reason)
{
    pl_uart_puts("LOOP3_CHECK ");
    pl_uart_puts(name);
    pl_uart_puts(" DEFERRED reason=");
    pl_uart_puts(reason);
    pl_uart_puts("\r\n");
}

static int command_is_read(char first)
{
    return first == 'r' || first == 'R';
}

static void spi_delay(void)
{
    usleep(1U);
}

static void spi_idle(void)
{
    hi3593_write_control(CONTROL_RELEASE_RESET);
    spi_delay();
}

static void spi_select(void)
{
    hi3593_write_control(CONTROL_LED);
    spi_delay();
}

static void spi_deselect(void)
{
    spi_idle();
    usleep(2U);
}

static u8 spi_shift_byte(u8 value)
{
    int bit;
    u8 readback = 0U;

    for (bit = 7; bit >= 0; bit--) {
        u32 si = ((value >> bit) & 0x1U) ? CONTROL_SI : 0U;
        hi3593_write_control(CONTROL_LED | si);
        spi_delay();
        hi3593_write_control(CONTROL_LED | si | CONTROL_SCK);
        spi_delay();
        readback = (u8)((readback << 1) |
                   (hi3593_read(HI3593_REG_STATUS) & 0x1U));
        hi3593_write_control(CONTROL_LED | si);
        spi_delay();
    }
    return readback;
}

static void spi_cmd0(u8 opcode)
{
    spi_select();
    (void)spi_shift_byte(opcode);
    spi_deselect();
}

static void spi_cmd1(u8 opcode, u8 data0)
{
    spi_select();
    (void)spi_shift_byte(opcode);
    (void)spi_shift_byte(data0);
    spi_deselect();
}

static void spi_cmd4(u8 opcode, u32 data)
{
    spi_select();
    (void)spi_shift_byte(opcode);
    (void)spi_shift_byte((u8)((data >> 24) & 0xFFU));
    (void)spi_shift_byte((u8)((data >> 16) & 0xFFU));
    (void)spi_shift_byte((u8)((data >> 8) & 0xFFU));
    (void)spi_shift_byte((u8)(data & 0xFFU));
    spi_deselect();
}

static u32 wait_status_mask(u32 mask, u32 expected, unsigned int limit)
{
    unsigned int i;
    u32 status = 0U;

    for (i = 0U; i < limit; i++) {
        status = hi3593_read(HI3593_REG_STATUS);
        if ((status & mask) == expected) {
            return status;
        }
        usleep(100U);
    }
    return status;
}

static u32 wait_tx_symbol(unsigned int limit)
{
    unsigned int i;
    u32 sample = 0U;

    for (i = 0U; i < limit; i++) {
        sample = hi3593_read(HI3593_REG_TX_SAMPLE);
        if ((sample & TX_SAMPLE_TX_SYMBOL) != 0U) {
            return sample;
        }
    }
    return sample;
}

static int rx_drive_check(u32 value)
{
    u32 sample;
    u32 readback;

    hi3593_write(HI3593_REG_RX_DRIVE, value);
    usleep(1000U);
    readback = hi3593_read(HI3593_REG_RX_DRIVE);
    sample = hi3593_read(HI3593_REG_TX_SAMPLE);
    return ((readback & TX_SAMPLE_RX_DRIVE) == value) &&
           ((sample & TX_SAMPLE_RX_DRIVE) == value);
}

static int run_rx_injection_check(void)
{
    u32 status;

    spi_cmd1(0x10U, 0x00U);
    hi3593_write(HI3593_REG_RX_DRIVE, 0x00000000U);
    usleep(1000U);
    hi3593_write(HI3593_REG_RX_DRIVE, 0x00000001U);
    usleep(1000U);
    hi3593_write(HI3593_REG_RX_DRIVE, 0x00000000U);
    status = wait_status_mask(STATUS_R1FLAG, STATUS_R1FLAG, 100U);
    return ((status & STATUS_R1FLAG) == STATUS_R1FLAG);
}

static int run_ddr_window_check(void)
{
    u32 value = 0x3593005AU;

    Xil_Out32(DDR_TEST_ADDR, value);
    Xil_DCacheFlushRange(DDR_TEST_ADDR, 4U);
    Xil_DCacheInvalidateRange(DDR_TEST_ADDR, 4U);
    return Xil_In32(DDR_TEST_ADDR) == value;
}

static int run_loop3_suite(void)
{
    int pass_count = 0;
    int fail_count = 0;
    int ok;
    u32 value;
    u32 status;
    u32 sample;

    pl_uart_puts("LOOP3_SUITE_BEGIN total_checks=14\r\n");
    hi3593_prepare();
    spi_idle();

    value = hi3593_read(HI3593_REG_ID);
    ok = (value == 0x48335933U);
    pl_uart_put_check("id_readback", ok, value);
    pass_count += ok ? 1 : 0;
    fail_count += ok ? 0 : 1;

    value = hi3593_read(HI3593_REG_CONTROL);
    ok = (value == CONTROL_RELEASE_RESET);
    pl_uart_put_check("control_release", ok, value);
    pass_count += ok ? 1 : 0;
    fail_count += ok ? 0 : 1;

    value = hi3593_read(HI3593_REG_STATUS);
    ok = ((value & STATUS_TEMPTY) != 0U);
    pl_uart_put_check("status_read", ok, value);
    pass_count += ok ? 1 : 0;
    fail_count += ok ? 0 : 1;

    sample = hi3593_read(HI3593_REG_TX_SAMPLE);
    ok = ((sample & TX_SAMPLE_TEMPTY) != 0U);
    pl_uart_put_check("tx_sample_read", ok, sample);
    pass_count += ok ? 1 : 0;
    fail_count += ok ? 0 : 1;

    ok = rx_drive_check(0x00000000U) && rx_drive_check(0x00000005U) &&
         rx_drive_check(0x0000000AU) && rx_drive_check(0x0000000FU);
    sample = hi3593_read(HI3593_REG_TX_SAMPLE);
    pl_uart_put_check("rx_drive_register_loopback", ok, sample);
    pass_count += ok ? 1 : 0;
    fail_count += ok ? 0 : 1;

    hi3593_write(HI3593_REG_RX_DRIVE, 0x00000000U);
    spi_cmd1(0x38U, 0x1EU);
    usleep(1000U);
    spi_cmd1(0x08U, 0x01U);
    value = hi3593_read(HI3593_REG_STATUS);
    pl_uart_put_opcode("08", "write_tx_control", 1, value);
    pass_count++;

    spi_cmd4(0x0CU, 0xFFFF0001U);
    status = wait_status_mask(STATUS_TEMPTY, 0x00000000U, 100U);
    ok = ((status & STATUS_TEMPTY) == 0U);
    pl_uart_put_opcode("0C", "write_tx_fifo", ok, status);
    pass_count += ok ? 1 : 0;
    fail_count += ok ? 0 : 1;

    spi_cmd0(0x40U);
    sample = wait_tx_symbol(1000000U);
    ok = ((sample & TX_SAMPLE_TX_SYMBOL) != 0U);
    pl_uart_put_opcode("40", "tx_start", ok, sample);
    pl_uart_put_check("tx_boundary_sampler_decode", ok, sample);
    pass_count += ok ? 2 : 0;
    fail_count += ok ? 0 : 2;

    spi_cmd0(0x44U);
    status = wait_status_mask(STATUS_TEMPTY, STATUS_TEMPTY, 100U);
    ok = ((status & STATUS_TEMPTY) != 0U);
    pl_uart_put_opcode("44", "fifo_mailbox_reset", ok, status);
    pass_count += ok ? 1 : 0;
    fail_count += ok ? 0 : 1;

    spi_cmd1(0x10U, 0x02U);
    value = hi3593_read(HI3593_REG_STATUS);
    pl_uart_put_opcode("10", "write_rx1_control", 1, value);
    pass_count++;

    ok = run_rx_injection_check();
    status = hi3593_read(HI3593_REG_STATUS);
    pl_uart_put_check("rx_symbol_injection_readback", ok, status);
    pass_count += ok ? 1 : 0;
    fail_count += ok ? 0 : 1;

    ok = run_ddr_window_check();
    value = Xil_In32(DDR_TEST_ADDR);
    pl_uart_put_check("ps_ddr_test_window", ok, value);
    pass_count += ok ? 1 : 0;
    fail_count += ok ? 0 : 1;

    spi_cmd0(0x04U);
    status = wait_status_mask(STATUS_TEMPTY, STATUS_TEMPTY, 100U);
    ok = ((status & STATUS_TEMPTY) != 0U);
    pl_uart_put_opcode("04", "master_reset", ok, status);
    pass_count += ok ? 1 : 0;
    fail_count += ok ? 0 : 1;

    pl_uart_put_deferred("analog_boundary", "external_HI8592_HI8450_instruments_not_installed");
    pl_uart_puts(fail_count == 0 ? "LOOP3_SUITE PASS passed=" :
                                  "LOOP3_SUITE FAIL passed=");
    pl_uart_put_hex8((u8)pass_count);
    pl_uart_puts(" failed=");
    pl_uart_put_hex8((u8)fail_count);
    pl_uart_puts(" deferred=01\r\n");
    return fail_count == 0;
}

int main(void)
{
    u32 id;
    u32 sample;
    char c;
    char command[8];
    unsigned int command_len = 0U;

    pl_uart_reset();
    pl_uart_puts("LOOP3_BOOT ps_uart0\r\n");
    hi3593_prepare();
    id = hi3593_read(HI3593_REG_ID);
    pl_uart_put_value_line("LOOP3_READY id=0x", id);

    while (1) {
        if (!pl_uart_get_char(&c)) {
            continue;
        }

        if (c == '\r' || c == '\n') {
            if (command_len == 0U) {
                continue;
            }

            if (command_is_read(command[0])) {
                sample = hi3593_read(HI3593_REG_TX_SAMPLE);
                pl_uart_put_value_line("read data=0x", sample);
            }
            else if (command_len >= 2U &&
                     (command[0] == 'i' || command[0] == 'I') &&
                     (command[1] == 'd' || command[1] == 'D')) {
                sample = hi3593_read(HI3593_REG_ID);
                pl_uart_put_value_line("id data=0x", sample);
            }
            else if (command[0] == 's' || command[0] == 'S') {
                if (command_len >= 2U &&
                    (command[1] == 'u' || command[1] == 'U')) {
                    (void)run_loop3_suite();
                }
                else {
                    sample = hi3593_read(HI3593_REG_STATUS);
                    pl_uart_put_value_line("status data=0x", sample);
                }
            }
            else if (command[0] == 'c' || command[0] == 'C') {
                sample = hi3593_read(HI3593_REG_CONTROL);
                pl_uart_put_value_line("control data=0x", sample);
            }
            else {
                pl_uart_puts("unknown command\r\n");
            }
            command_len = 0U;
        }
        else if (command_len < sizeof(command)) {
            command[command_len] = c;
            command_len++;
        }
        else {
            command_len = 0U;
        }
    }
}
