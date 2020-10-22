# src/resources/Optitemp/CMakeLists.txt
#
# cmake configuration file for Optitemp resource

# Set a minimum version for cmake; old versions won't work
cmake_minimum_required (VERSION 2.6) 

# Include the necessary header files from the source directories
include_directories (${PROJECT_BASE_DIR}/src/utils
)

# Link to the library directory to get the library object files
link_directories (${PROJECT_BASE_DIR}/lib)


# Build the Skeleton library
add_definitions (-Wall -O3 -g -DREENTRANT)
add_library(optitemp STATIC chiller.cpp chiller_interface.cpp)

#### Compile the WFS stand alone control programs
# Add command line flags for compiling
add_definitions (-Wswitch -Wall -O3 -g -DREENTRANT)

# Compile the executables
ADD_EXECUTABLE(chiller_test chiller_test.cpp)

# Link the executable to the required library files
TARGET_LINK_LIBRARIES(chiller_test optitemp util -lpthread ${BOOST_SYSTEM}
                      ${BOOST_MT_LIB})
#                      -lpthread -ldl -lrt
