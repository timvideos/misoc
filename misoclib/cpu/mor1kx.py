import os

from migen.fhdl.std import *
from migen.bus import wishbone

from migen.genlib.record import Record
from migen.flow.actor import Sink, Source
from migen.genlib.resetsync import AsyncResetSynchronizer

jtag_layout = [
    ("tck", 1),
    ("tdi", 1),
    ("tdo", 1),
    ("rst", 1),
    ("select", 1),
    ("shift", 1),
    ("capture", 1),
    ("update", 1),
]

class BscanSpartan6(Module):
    def __init__(self, chain=1):
        self.jtag = Record(jtag_layout)
        # * BSCAN_SPARTAN6 outputs except TDI are all synchronous
        #   to falling TCK edges
        # * TDO is _synchronized_ to falling edges
        # * TDI must be sampled on rising edges
        # * use rising TCK as clock and keep in mind that there is
        #   always one cycle of latency TDI-to-TDO
        #self.clk = Signal()
        # self.specials += Instance("BUFG", i_I=self.clk, o_O=self.jtag.clk)
        #self.comb += self.jtag.clk.eq(self.clk)
        self.specials += Instance(
            "BSCAN_SPARTAN6",
            p_JTAG_CHAIN=chain,
            o_SEL=self.jtag.select,
            o_RESET=self.jtag.rst,
            o_TDI=self.jtag.tdi,
            #o_DRCK=self.jtag.drck,
            o_CAPTURE=self.jtag.capture,
            o_UPDATE=self.jtag.update,
            o_SHIFT=self.jtag.shift,
            #o_RUNTEST=self.jtag.runtest,
            o_TCK=self.jtag.tck,
            #o_TMS=self.jtag.tms,
            i_TDO=self.jtag.tdo,
        )


class MOR1KX(Module):
    def __init__(self, platform, reset_pc):
        self.ibus = i = wishbone.Interface()
        self.dbus = d = wishbone.Interface()
        self.interrupt = Signal(32)

        ###
        clk = ClockSignal()
        rst = ResetSignal()
        or1k_dbg_rst = Signal()
        cpu_rst = Signal()

        self.comb += [
           cpu_rst.eq(rst | or1k_dbg_rst),
        ]

        i_adr_o = Signal(32)
        d_adr_o = Signal(32)

        or1k_dbg_adr_i = Signal(32)
        or1k_dbg_stb_i = Signal()
        or1k_dbg_dat_i = Signal(32)
        or1k_dbg_we_i = Signal()
        or1k_dbg_dat_o = Signal(32)
        or1k_dbg_ack_o = Signal()
        or1k_dbg_stall_i = Signal()
        or1k_dbg_bp_o = Signal()

        self.specials += Instance("mor1kx",
                                  p_FEATURE_INSTRUCTIONCACHE="ENABLED",
                                  p_OPTION_ICACHE_BLOCK_WIDTH=4,
                                  p_OPTION_ICACHE_SET_WIDTH=8,
                                  p_OPTION_ICACHE_WAYS=1,
                                  p_OPTION_ICACHE_LIMIT_WIDTH=31,
                                  p_FEATURE_DATACACHE="ENABLED",
                                  p_OPTION_DCACHE_BLOCK_WIDTH=4,
                                  p_OPTION_DCACHE_SET_WIDTH=8,
                                  p_OPTION_DCACHE_WAYS=1,
                                  p_OPTION_DCACHE_LIMIT_WIDTH=31,
                                  p_FEATURE_TIMER="NONE",
                                  p_OPTION_PIC_TRIGGER="LEVEL",
                                  p_FEATURE_SYSCALL="NONE",
                                  p_FEATURE_TRAP="NONE",
                                  p_FEATURE_RANGE="NONE",
                                  p_FEATURE_OVERFLOW="NONE",
                                  p_FEATURE_ADDC="ENABLED",
                                  p_FEATURE_CMOV="ENABLED",
                                  p_FEATURE_FFL1="ENABLED",
                                  p_OPTION_CPU0="CAPPUCCINO",
                                  p_OPTION_RESET_PC=reset_pc,
                                  p_IBUS_WB_TYPE="B3_REGISTERED_FEEDBACK",
                                  p_DBUS_WB_TYPE="B3_REGISTERED_FEEDBACK",
                                  p_FEATURE_DEBUGUNIT="ENABLED",
                                  p_OPTION_RF_NUM_SHADOW_GPR=1,

                                  i_clk=clk,
                                  i_rst=cpu_rst,

                                  i_irq_i=self.interrupt,

                                  o_iwbm_adr_o=i_adr_o,
                                  o_iwbm_dat_o=i.dat_w,
                                  o_iwbm_sel_o=i.sel,
                                  o_iwbm_cyc_o=i.cyc,
                                  o_iwbm_stb_o=i.stb,
                                  o_iwbm_we_o=i.we,
                                  o_iwbm_cti_o=i.cti,
                                  o_iwbm_bte_o=i.bte,
                                  i_iwbm_dat_i=i.dat_r,
                                  i_iwbm_ack_i=i.ack,
                                  i_iwbm_err_i=i.err,
                                  i_iwbm_rty_i=0,

                                  o_dwbm_adr_o=d_adr_o,
                                  o_dwbm_dat_o=d.dat_w,
                                  o_dwbm_sel_o=d.sel,
                                  o_dwbm_cyc_o=d.cyc,
                                  o_dwbm_stb_o=d.stb,
                                  o_dwbm_we_o=d.we,
                                  o_dwbm_cti_o=d.cti,
                                  o_dwbm_bte_o=d.bte,
                                  i_dwbm_dat_i=d.dat_r,
                                  i_dwbm_ack_i=d.ack,
                                  i_dwbm_err_i=d.err,
                                  i_dwbm_rty_i=0,

                                  i_du_addr_i=or1k_dbg_adr_i[:16],
                                  i_du_stb_i=or1k_dbg_stb_i,
                                  i_du_dat_i=or1k_dbg_dat_i,
                                  i_du_we_i=or1k_dbg_we_i,
                                  o_du_dat_o=or1k_dbg_dat_o,
                                  o_du_ack_o=or1k_dbg_ack_o,
                                  i_du_stall_i=or1k_dbg_stall_i,
                                  o_du_stall_o=or1k_dbg_bp_o,
                                  )

        jtag_tap_tck = Signal()
        jtag_tap_tdi = Signal()
        jtag_tap_tdo = Signal()
        jtag_tap_rst = Signal()
        jtag_tap_idle = Signal()
        jtag_tap_capture = Signal()
        jtag_tap_shift = Signal()
        jtag_tap_pause = Signal()
        jtag_tap_update = Signal()
        jtag_tap_select = Signal()

        dbg_adr_o = Signal(32)
        self.debug = dbg = wishbone.Interface()

        self.specials += Instance(
            "adbg_top",
            i_cpu0_clk_i=clk,
            o_cpu0_rst_o=or1k_dbg_rst,
            o_cpu0_addr_o=or1k_dbg_adr_i,
            o_cpu0_data_o=or1k_dbg_dat_i,
            o_cpu0_stb_o=or1k_dbg_stb_i,
            o_cpu0_we_o=or1k_dbg_we_i,
            i_cpu0_data_i=or1k_dbg_dat_o,
            i_cpu0_ack_i=or1k_dbg_ack_o,
            o_cpu0_stall_o=or1k_dbg_stall_i,
            i_cpu0_bp_i=or1k_dbg_bp_o,

            # TAP interface
            i_tck_i=jtag_tap_tck,
            i_tdi_i=jtag_tap_tdi,
            o_tdo_o=jtag_tap_tdo,
            i_rst_i=jtag_tap_rst,
            i_capture_dr_i=jtag_tap_capture,
            i_shift_dr_i=jtag_tap_shift,
            i_pause_dr_i=jtag_tap_pause,
            i_update_dr_i=jtag_tap_update,
            i_debug_select_i=jtag_tap_select,

            # Wishbone debug master
            i_wb_clk_i=clk,
            i_wb_dat_i=dbg.dat_r,
            i_wb_ack_i=dbg.ack,
            i_wb_err_i=dbg.err,

            o_wb_adr_o=dbg_adr_o,
            o_wb_dat_o=dbg.dat_w,
            o_wb_sel_o=dbg.sel,
            o_wb_cyc_o=dbg.cyc,
            o_wb_stb_o=dbg.stb,
            o_wb_we_o=dbg.we,
            o_wb_cti_o=dbg.cti,
            o_wb_bte_o=dbg.bte,
        )

        self.specials += Instance(
            "xilinx_internal_jtag",
            o_tck_o=jtag_tap_tck,
            i_debug_tdo_i=jtag_tap_tdo,
            o_tdi_o=jtag_tap_tdi,
            o_test_logic_reset_o=jtag_tap_rst,
            o_run_test_idle_o=jtag_tap_idle,
            o_shift_dr_o=jtag_tap_shift,
            o_capture_dr_o=jtag_tap_capture,
            o_pause_dr_o=jtag_tap_pause,
            o_update_dr_o=jtag_tap_update,
            o_debug_select_o=jtag_tap_select,
        )


        #bscan = self.submodules.bscan = BscanSpartan6()
        #self.comb += [
        #    jtag_tap_tck.eq(bscan.jtag.tck),
        #    jtag_tap_tdi.eq(bscan.jtag.tdi),
        #    jtag_tap_tdo.eq(bscan.jtag.tdo),
        #    jtag_tap_rst.eq(bscan.jtag.rst),
        #    jtag_tap_capture.eq(bscan.jtag.capture),
        #    jtag_tap_shift.eq(bscan.jtag.shift),
        #    jtag_tap_pause.eq(0),
        #    jtag_tap_update.eq(bscan.jtag.update),
        #    jtag_tap_select.eq(bscan.jtag.select),
        #]

        self.comb += [
            self.ibus.adr.eq(i_adr_o[2:]),
            self.dbus.adr.eq(d_adr_o[2:]),
            self.debug.adr.eq(dbg_adr_o[2:]),
        ]

        # add Verilog sources
        platform.add_source_dir(os.path.join("extcores", "mor1kx", "submodule",
                                             "rtl", "verilog"))
        platform.add_source_dir(os.path.join("extcores", "mor1kx", "adv_debug_sys",
                                             "Hardware", "adv_dbg_if",
                                             "rtl", "verilog"))
        platform.add_source_dir(os.path.join("extcores", "mor1kx", "adv_debug_sys",
                                             "Hardware", "xilinx_internal_jtag",
                                             "rtl", "verilog"))
