// File: dco_module.v
module dco_module (
    input  wire clk_sys,    // A faster, stable system clock available on the chip
    input  wire rst_n,      // Active-low reset
    input  wire [7:0] dco_code, // Frequency control code (Period control)
    output reg  clk_out     // Generated clock output
);

    reg [7:0] counter;
    
    always @(posedge clk_sys or negedge rst_n) begin
        if (!rst_n) begin
            counter <= 8'h00;
            clk_out <= 1'b0;
        end else begin
            if (counter == dco_code) begin
                // Toggle the output clock when the counter reaches the DCO code
                clk_out <= ~clk_out;
                counter <= 8'h00;
            end else begin
                counter <= counter + 1;
            end
        end
    end

endmodule
