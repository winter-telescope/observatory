# src/control/CMakeLists.txt
#
# cmake configuration file for the resources directory

# Set a minimum version for cmake; old versions won't work
cmake_minimum_required (VERSION 2.6) 

# Add the watchdog control software directory so it is built
add_subdirectory (${PROJECT_SRC_DIR}/control/WATCHDOGD)

