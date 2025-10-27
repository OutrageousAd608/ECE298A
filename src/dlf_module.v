// File: dlf_module.v
module dlf_module (
    input  wire clk_ref,    // Clock for the filter (usually the reference clock)
    input  wire rst_n,      // Active-low reset
    input  wire up,         // Increment DCO code
    input  wire dn,         // Decrement DCO code
    output reg  [7:0] dco_code // Output DCO control code (8 bits)
);

    parameter INITIAL_CODE = 8'd128; // Center frequency code

    always @(posedge clk_ref or negedge rst_n) begin
        if (!rst_n) begin
            dco_code <= INITIAL_CODE;
        end else begin
            // Accumulate the phase error (UP - DN)
            if (up & ~dn)
                dco_code <= dco_code + 1;
            else if (dn & ~up)
                dco_code <= dco_code - 1;
            // No change if both UP and DN are high (shouldn't happen with PFD above)
            // or if both are low (phase locked or no error)
        end
    end

endmodule
