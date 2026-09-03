#include <stdint.h>

#define BCI_CONTROL_BASE 0x43C00000u
#define BCI_STATUS_OFFSET 0x04u
#define BCI_RESULT_OFFSET 0x08u

static volatile uint32_t *const bci_control =
    (volatile uint32_t *)BCI_CONTROL_BASE;

int main(void)
{
    bci_control[0] = 1u;
    while ((bci_control[BCI_STATUS_OFFSET / 4u] & 1u) == 0u) {
    }
    return (int)(bci_control[BCI_RESULT_OFFSET / 4u] & 0xFFu);
}
