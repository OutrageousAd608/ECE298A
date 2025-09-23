# Makefile for cocotb simulation

# Simulator
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source directory
SRC_DIR = $(PWD)/../src

# Your Verilog source file(s)
PROJECT_SOURCES = project.v

# RTL simulation build directory
SIM_BUILD = sim_build/rtl

# Verilog sources (your design)
VERILOG_SOURCES = $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

# Top-level module (must match the module name in project.v)
TOPLEVEL = tt_um_counter

# Python testbench module (test/test_counter.py)
COCOTB_TEST_MODULES = test_counter

# Extra compile args
COMPILE_ARGS += -I$(SRC_DIR)

# Include cocotb's simulation makefile
include $(shell cocotb-config --makefiles)/Makefile.sim
