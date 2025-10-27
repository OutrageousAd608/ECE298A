// File: n_divider_module.v
module n_divider_module (
    input  wire clk_in,      // Clock to be divided (DCO output)
    input  wire rst_n,       // Active-low reset
    input  wire [3:0] div_ratio, // Programmable division ratio (N from 1 to 15)
    output reg  clk_out      // Divided clock output (clk_div)
);

    // Counter needs to be at least as wide as the division ratio input
    reg [3:0] counter;
    
    // The actual division is by (div_ratio + 1) to allow a ratio of 1
    wire [3:0] target_count = div_ratio; 

    always @(posedge clk_in or negedge rst_n) begin
        if (!rst_n) begin
            counter <= 4'h00;
            clk_out <= 1'b0;
        end else begin
            if (counter == target_count) begin
                // Toggle the output and reset the counter
                clk_out <= ~clk_out;
                counter <= 4'h00;
            end else begin
                counter <= counter + 1;
            end
        end
    end

endmodule
