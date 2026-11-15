# From a Vivado command prompt: vivado -mode batch -source scripts/build_bitstream.tcl
set root [file normalize [file join [file dirname [info script]] ..]]
set xpr [file join $root build vivado jj_nexys4ddr.xpr]
if {[llength [get_projects -quiet]] == 0} {
    if {[file exists $xpr]} {open_project $xpr} else {
        source [file join $root scripts create_project.tcl]
    }
} elseif {[file normalize [get_property DIRECTORY [current_project]]] ne [file dirname $xpr]} {
    error "A different project is open. Close it first."
}
launch_runs synth_1 -jobs 4
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
    error "Synthesis failed. Inspect synth_1/runme.log. Original RTL was not changed."
}
launch_runs impl_1 -to_step route_design -jobs 4
wait_on_run impl_1
if {![string match "*route_design Complete*" [get_property STATUS [get_runs impl_1]]]} {
    error "Implementation failed. Inspect impl_1/runme.log."
}
open_run impl_1
set reports [file join $root build reports]
file mkdir $reports
report_timing_summary -file [file join $reports timing_summary.rpt]
report_utilization -file [file join $reports utilization.rpt]
report_drc -file [file join $reports drc.rpt]
report_clocks -file [file join $reports clocks.rpt]
set worst_setup [get_timing_paths -delay_type max -max_paths 1]
set worst_hold [get_timing_paths -delay_type min -max_paths 1]
if {[llength $worst_setup] == 0 || [llength $worst_hold] == 0} {
    error "No timing paths returned; inspect clock constraints."
}
if {[get_property SLACK $worst_setup] < 0 || [get_property SLACK $worst_hold] < 0} {
    error "Timing failed; bitstream not written. See build/reports/timing_summary.rpt."
}
write_bitstream -force [file join $root build nexys4ddr_jj.bit]
puts "Bitstream: [file join $root build nexys4ddr_jj.bit]"
