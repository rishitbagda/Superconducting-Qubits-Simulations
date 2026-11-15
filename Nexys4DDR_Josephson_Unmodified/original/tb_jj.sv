`timescale 1ns/1ps

module tb_jj;
    timeunit 1ns;
    timeprecision 1ps;

    logic clk = 0;
    logic rst = 1;
    logic en  = 1;
    
    logic signed [31:0] i_bias = 0;
    logic        [31:0] theta;
    logic signed [31:0] v_out;

    // SystemVerilog implicit port mapping (.*)
    jj_rcsj #(
        .DT(1.0/64.0), 
        .BETA_C(4.0)
    ) dut (.*);

    always #5 clk = ~clk;

    localparam int SETTLE = 8000;
    localparam int AVG    = 8000;
    
    real vsum;

    // SystemVerilog automatic task encapsulates local memory
    task automatic measure(input real ibias);
        i_bias = $rtoi(ibias * 16777216.0);
        repeat (SETTLE) @(posedge clk);
        
        vsum = 0.0;
        // Local scoped loop variable
        for (int n = 0; n < AVG; n++) begin
            @(posedge clk);
            vsum += $itor(v_out) / 16777216.0;
        end
        $display("%0.3f,%0.5f", ibias, vsum / AVG);
    endtask

    initial begin
        repeat (4) @(posedge clk);
        rst = 0;
        $display("i_bias,<v>");
        
        // Sweep up
        for (real ib = 0.0; ib <= 2.0001; ib += 0.05) begin
            measure(ib);
        end
        
        $display("--- sweeping down ---");
        
        // Sweep down (no reset: state is retained -> hysteresis)
        for (real ib = 2.0; ib >= -0.0001; ib -= 0.05) begin
            measure(ib);
        end
        
        $finish;
    end
endmodule
