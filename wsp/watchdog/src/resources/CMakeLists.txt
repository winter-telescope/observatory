# src/resources/CMakeLists.txt
#
# cmake configuration file for the resources directory

# Set a minimum version for cmake; old versions won't work
cmake_minimum_required (VERSION 2.6) 

# Add the Optitemp  directory so the chiller interface is built
add_subdirectory (${PROJECT_BASE_DIR}/src/resources/Optitemp)

