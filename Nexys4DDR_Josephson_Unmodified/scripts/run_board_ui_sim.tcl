set root [file normalize [file join [file dirname [info script]] ..]]
if {[llength [get_projects -quiet]] == 0} {
    set xpr [file join $root build vivado jj_nexys4ddr.xpr]
    if {[file exists $xpr]} {open_project $xpr} else {
        source [file join $root scripts create_project.tcl]
    }
}
set_property top tb_board_ui [get_filesets sim_1]
launch_simulation
run all
