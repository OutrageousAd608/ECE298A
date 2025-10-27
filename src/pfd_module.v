// File: pfd_module.v
module pfd_module (
    input  wire clk_ref, // Reference clock (or system clock)
    input  wire clk_div, // Divided feedback clock
    output reg  up,      // Reference leads feedback
    output reg  dn       // Feedback leads reference
);

    // Two DFFs to capture the edges of the input clocks
    reg ref_edge;
    reg div_edge;
    
    // Logic to reset the PFD when both edges have been seen
    wire rst = ref_edge & div_edge;

    // PFD logic, operating on the positive edges of the respective clocks
    always @(posedge clk_ref or posedge rst) begin
        if (rst) 
            ref_edge <= 1'b0;
        else
            ref_edge <= 1'b1;
    end

    always @(posedge clk_div or posedge rst) begin
        if (rst)
            div_edge <= 1'b0;
        else
            div_edge <= 1'b1;
    end
    
    // Generate the UP/DN signals
    // UP is active when ref_edge is high and div_edge is low
    // DN is active when div_edge is high and ref_edge is low
    always @(*) begin
        up = ref_edge & (~div_edge);
        dn = div_edge & (~ref_edge);
    end

endmodule
