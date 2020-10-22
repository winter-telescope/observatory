# src/utils/CMakeLists.txt
#
# cmake configuration file for the utils directory

# Set a minimum version for cmake; old versions won't work
cmake_minimum_required (VERSION 2.6) 

# Se the list of source files to include in the library
set(UTIL_SRC
	common
	communications
	file_ops
	operations
	robo_time
#  sensors
	state
)

# Include the necessary header files from the source directories
#include_directories(${PROJECT_INCLUDE_PATH})

# Link to the library directory to get the library object files
add_library(util ${UTIL_SRC})

