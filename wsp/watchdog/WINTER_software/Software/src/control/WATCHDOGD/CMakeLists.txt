# src/control/WATCHDOGD/CMakeLists.txt
#
# cmake configuration file for the WATCHDOGD directory

# Set a minimum version for cmake; old versions won't work
cmake_minimum_required (VERSION 2.6) 

# Include the necessary header files from the source directories
include_directories (${PROJECT_BASE_DIR}/src/utils 
         ${PROJECT_BASE_DIR}/src/control/ROBOD
)

# Link to the library directory to get the library object files
link_directories (${PROJECT_BASE_DIR}/lib)


#### Compile the stand alone control programs
# Add command line flags for compiling
add_definitions (-Wall -O -g -DREENTRANT)

# Compile the executables
ADD_EXECUTABLE(watchdogd watchdogd.cpp watchdogd_server.cpp)
ADD_EXECUTABLE(watchdogd_test watchdogd_test.cpp)

# Link the executable to the required library files
TARGET_LINK_LIBRARIES(watchdogd util -lpthread ${BOOST_SYSTEM} ${BOOST_MT_LIB})
TARGET_LINK_LIBRARIES(watchdogd_test util -lpthread ${BOOST_SYSTEM} ${BOOST_MT_LIB})
