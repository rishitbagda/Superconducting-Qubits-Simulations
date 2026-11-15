# Run in the Vivado Tcl Console: source C:/path/to/scripts/create_project.tcl
set root [file normalize [file join [file dirname [info script]] ..]]
set project_dir [file join $root build vivado]
if {[file exists [file join $project_dir jj_nexys4ddr.xpr]]} {
    error "Project already exists. Open build/vivado/jj_nexys4ddr.xpr, or move the build folder before recreating."
}
create_project jj_nexys4ddr $project_dir -part xc7a100tcsg324-1
set_property target_language Verilog [current_project]
set_property simulator_language Mixed [current_project]
add_files -norecurse [list [file join $root original jj_rcsj.sv] \
    [file join $root board jj_board_ui.sv] [file join $root board nexys4ddr_top.sv]]
set_property top nexys4ddr_top [get_filesets sources_1]
add_files -fileset constrs_1 -norecurse [file join $root constraints nexys4ddr.xdc]
add_files -fileset sim_1 -norecurse [list [file join $root original tb_jj.sv] \
    [file join $root verification tb_board_ui.sv]]
set_property top tb_jj [get_filesets sim_1]
set_property xsim.simulate.runtime 0ns [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1
puts "Created Nexys 4 DDR project. Model and original testbench are unchanged."
