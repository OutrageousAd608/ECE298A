// File: tt_um_user_module.v
module tt_um_user_module (
    input  wire [7:0] ui_in,    // Dedicated user input pins
    output wire [7:0] uo_out,   // Dedicated user output pins
    input  wire [7:0] uio_in,   // Bidirectional pins input
    output wire [7:0] uio_out,  // Bidirectional pins output
    output wire [7:0] uio_oe,   // Bidirectional pins output enable
    input  wire       ena,      // Design enable (high when active)
    input  wire       clk,      // System clock (fastest available)
    input  wire       rst_n     // Active-low reset
);

    // --- Signal Mapping ---
    wire ref_clk;
    wire [3:0] div_ratio;
    wire pll_locked;
    wire pll_clk_out;
    wire [7:0] pll_debug;

    // ui_in[0] is the Reference Clock
    assign ref_clk = ui_in[0]; 
    
    // ui_in[4:1] sets the programmable N-Divider ratio
    assign div_ratio = ui_in[4:1];

    // --- ADPLL Core Instantiation ---
    adpll_top pll_inst (
        .clk_ref        (ref_clk),
        .clk_sys        (clk),     // Use the fast system clock for the DCO
        .rst_n          (rst_n),
        .div_ratio_in   (div_ratio),
        .locked         (pll_locked),
        .clk_out        (pll_clk_out),
        .debug_out      (pll_debug)
    );

    // --- Output Assignments ---
    assign uo_out[0] = pll_clk_out;  // uo_out[0] for the generated/synchronized clock
    assign uo_out[1] = pll_locked;   // uo_out[1] for the 'locked' status
    assign uo_out[7:2] = pll_debug[5:0]; // uo_out[7:2] for DCO code and UP/DN debug
    
    // Keep bidirectional pins as high impedance (disabled) for a digital-out-only design
    assign uio_out  = 8'h00;
    assign uio_oe   = 8'h00; 

    wire clk_out_test = uo_out[0];
endmodule
