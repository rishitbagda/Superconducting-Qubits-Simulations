`timescale 1ns/1ps
// New adapter checks. Never substitutes for the friend's original testbench.
module tb_board_ui;
    logic clk=0, reset_async=1;
    logic [15:0] sw=0;
    wire [15:0] led; wire [6:0] seg; wire dp; wire [7:0] an;
    logic [31:0] saved_theta, saved_voltage, saved_steps;
    jj_board_ui #(.STEP_DIV(4), .REFRESH_DIV(8)) ui(.*);
    always #50 clk=~clk;
    task automatic cycles(input integer n);
        repeat(n) @(negedge clk);
    endtask
    initial begin
        cycles(5); reset_async=0; cycles(10);
        if(ui.theta !== 0 || ui.voltage !== 0) $fatal(1,"Reset failed");
        sw=16'h0018; cycles(10); // 24/16 = 1.5 Ic, paused
        if(ui.bias_q !== 32'h01800000) $fatal(1,"Bias conversion failed");
        if(ui.steps !== 0) $fatal(1,"Pause failed");
        sw=16'h8018; cycles(200);
        if(ui.voltage === 0 || ui.theta === 0 || ui.steps === 0) $fatal(1,"No computation");
        sw=16'h0018; cycles(10);
        saved_theta=ui.theta; saved_voltage=ui.voltage; saved_steps=ui.steps;
        cycles(50);
        if(ui.theta !== saved_theta || ui.voltage !== saved_voltage || ui.steps !== saved_steps)
            $fatal(1,"State changed while paused");
        sw=16'h403f; cycles(20); // page 2, clamp 63 to 32
        if(ui.bias_q !== 32'h02000000 || ui.snapshot !== 32'h02000000)
            $fatal(1,"Clamp / display selection failed");
        sw=16'h2010; cycles(20);
        if(ui.snapshot !== saved_theta) $fatal(1,"Phase page failed");
        sw=16'h6010; cycles(20);
        if(ui.snapshot !== saved_steps) $fatal(1,"Count page failed");
        cycles(70000);
        if(ui.frame !== saved_steps) $fatal(1,"Frame snapshot failed");
        reset_async=1; cycles(10);
        if(ui.theta !== 0 || ui.voltage !== 0 || ui.steps !== 0) $fatal(1,"Button reset failed");
        $display("PASS: board UI reset, bias, clamp, run, pause, display pages and frame snapshot");
        $finish;
    end
    initial begin #20000000; $fatal(1,"Timeout"); end
endmodule
