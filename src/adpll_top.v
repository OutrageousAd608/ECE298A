// File: adpll_top.v
module adpll_top (
    input  wire       clk_ref,     // Reference clock from ui_in[0]
    input  wire       clk_sys,     // System clock for DCO (or clk_ref if fast enough)
    input  wire       rst_n,       // Active-low reset
    input  wire [3:0] div_ratio_in, // Programmable division ratio N
    output wire       locked,      // PLL lock indicator
    output wire       clk_out,     // Synchronized/multiplied clock output (DCO output)
    output wire [7:0] debug_out    // Internal debug signals
);

    // Internal wires
    wire up, dn;             // PFD outputs
    wire clk_div;            // Divided clock from N-Divider
    wire [7:0] dco_code;     // Control code for DCO (Loop Filter output)
    
    // --- 1. PFD Instantiation ---
    pfd_module pfd_inst (
        .clk_ref   (clk_ref),
        .clk_div   (clk_div),
        .up        (up),
        .dn        (dn)
    );

    // --- 2. Digital Loop Filter (Accumulator) Instantiation ---
    // CRITICAL FIX: Swap UP/DN ports to correct PLL feedback polarity
    dlf_module dlf_inst (
        .clk_ref   (clk_ref),
        .rst_n     (rst_n),
        .up        (dn), // <-- SWAPPED: DLF UP is now PFD DN
        .dn        (up), // <-- SWAPPED: DLF DN is now PFD UP
        .dco_code  (dco_code)
    );

    // --- 3. DCO Instantiation ---
    dco_module dco_inst (
        .clk_sys   (clk_sys),   // DCO runs on the fast system clock
        .rst_n     (rst_n),
        .dco_code  (dco_code),
        .clk_out   (clk_out)
    );

    // --- 4. N-Divider Instantiation ---
    n_divider_module n_div_inst (
        .clk_in    (clk_out),
        .rst_n     (rst_n),
        .div_ratio (div_ratio_in),
        .clk_out   (clk_div)
    );

    // --- Output Assignments ---\
    assign locked    = ~up & ~dn; // Simple assumption for lock signal
    assign debug_out = dco_code;

endmodule
