`timescale 1ns/1ps
// 10 MHz board UI, deliberately outside the unchanged junction model.
module jj_board_ui #(
    parameter integer STEP_DIV = 1000,       // 10,000 model steps/second
    parameter integer REFRESH_DIV = 1000000  // display snapshot at 10 Hz
)(
    input wire clk, input wire reset_async, input wire [15:0] sw,
    output wire [15:0] led, output logic [6:0] seg,
    output wire dp, output logic [7:0] an
);
    (* ASYNC_REG = "TRUE" *) logic [1:0] rst_pipe = 2'b11;
    always_ff @(posedge clk or posedge reset_async)
        if (reset_async) rst_pipe <= 2'b11;
        else rst_pipe <= {rst_pipe[0], 1'b0};
    wire rst = rst_pipe[1];

    (* ASYNC_REG = "TRUE" *) logic [15:0] sw_meta = 0, sw_sync = 0;
    always_ff @(posedge clk) begin
        if (rst) begin sw_meta <= 0; sw_sync <= 0; end
        else begin sw_meta <= sw; sw_sync <= sw_meta; end
    end
    // Use pause while changing several switches: synchronization is per bit.
    wire [5:0] bias_code = sw_sync[5:0] > 6'd32 ? 6'd32 : sw_sync[5:0];
    wire signed [31:0] bias_q = $signed({6'b0, bias_code, 20'b0});
    logic [31:0] step_count = 0;
    wire step_en = sw_sync[15] && (step_count == STEP_DIV-1) && !rst;
    always_ff @(posedge clk) begin
        if (rst || !sw_sync[15] || step_count == STEP_DIV-1) step_count <= 0;
        else step_count <= step_count + 1;
    end

    wire [31:0] theta;
    wire signed [31:0] voltage;
    jj_rcsj #(.DT(1.0/64.0), .BETA_C(4.0)) dut(
        .clk(clk), .rst(rst), .en(step_en), .i_bias(bias_q),
        .theta(theta), .v_out(voltage)
    );

    logic [31:0] steps = 0;
    always_ff @(posedge clk) begin
        if (rst) steps <= 0;
        else if (step_en) steps <= steps + 1;
    end
    // Snapshot the whole word, then latch each display frame to avoid torn digits.
    logic [31:0] refresh_count = 0, snapshot = 0, frame = 0;
    logic [15:0] scan_count = 0;
    logic [31:0] selected;
    always_comb begin
        case (sw_sync[14:13])
            2'b00: selected = voltage;
            2'b01: selected = theta;
            2'b10: selected = bias_q;
            default: selected = steps;
        endcase
    end
    always_ff @(posedge clk) begin
        if (rst) begin
            refresh_count <= 0; snapshot <= 0; frame <= 0; scan_count <= 0;
        end else begin
            scan_count <= scan_count + 1'b1;
            if (refresh_count == REFRESH_DIV-1) begin
                refresh_count <= 0;
                snapshot <= selected;
            end else refresh_count <= refresh_count + 1;
            if (scan_count == 0) frame <= snapshot;
        end
    end
    wire [2:0] digit = scan_count[15:13];
    wire [3:0] nibble = (frame >> (digit * 4));
    // seg[0] is A, seg[6] is G. All outputs are active-low.
    always_comb begin
        an = ~(8'b1 << digit);
        // One blank clock at each digit transition limits ghosting.
        if (scan_count[12:0] == 0 || rst) an = 8'hff;
        case (nibble)
            4'h0: seg=7'b1000000; 4'h1: seg=7'b1111001;
            4'h2: seg=7'b0100100; 4'h3: seg=7'b0110000;
            4'h4: seg=7'b0011001; 4'h5: seg=7'b0010010;
            4'h6: seg=7'b0000010; 4'h7: seg=7'b1111000;
            4'h8: seg=7'b0000000; 4'h9: seg=7'b0010000;
            4'ha: seg=7'b0001000; 4'hb: seg=7'b0000011;
            4'hc: seg=7'b1000110; 4'hd: seg=7'b0100001;
            4'he: seg=7'b0000110; default: seg=7'b0001110;
        endcase
    end
    assign dp = 1'b1;
    // LED15=run, LED14:13=page, LED12=not reset, LED11=step heartbeat,
    // LED10:6=0, LED5:0=clamped bias code.
    assign led = {sw_sync[15], sw_sync[14:13], ~rst, steps[12], 5'b0, bias_code};
endmodule
