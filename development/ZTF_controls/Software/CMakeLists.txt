# CMakeLists.txt
#
# cmake configuration file for the top level directory of the Robo-AO project

# Set a minimum version for cmake; old versions won't work
cmake_minimum_required (VERSION 2.6) 

# Set the project name to ZTF
PROJECT(WINTER)

# Get the hostname
cmake_host_system_information(RESULT HOST QUERY HOSTNAME)
message ("Compiling " ${PROJECT} " on host " ${HOST})

# Set the name of the main control computer for the project. This is used to
# compile only required software on main and other computer systems.
set (CONTROL_HOST "odin")

# Set project base directory for output files
set (PROJECT_BASE_DIR "/home/winter/WINTER_GIT/code/development/ZTF_controls/Software")
set (PROJECT_DATA_DIR "/home/winter/data")

# Set variables that select modules to compile
set (QUEUE_SYSTEM "ZTF")
set (TELESCOPE "Palomar_48")




# Add command line flags for compiling test software, comment this out to
# ignore the testing software
add_definitions(-DTESTING_SOFTWARE)
message ("TESTING_SOFTWARE flag is set!")

# Add command line flags for compiling data test software, comment this out to
# ignore the testing software
#add_definitions(-DDATA_TESTING)
#message ("DATA_TESTING flag is set!")


## Set up the telescope library and source code paths
IF(TELESCOPE)
  IF(TELESCOPE STREQUAL "Palomar_60")
    set(TELESCOPE_LIBRARY "p60")
    set(TELESCOPE_DIR "Palomar_60")
    set(WEATHER_LIBRARY "weather")
    set(WEATHER_HARDWARE "")
  ELSEIF(TELESCOPE STREQUAL "Palomar_48")
    set(TELESCOPE_LIBRARY "telescope")
    set(TELESCOPE_DIR "Palomar_48")
    set(WEATHER_LIBRARY "weather")
    set(WEATHER_HARDWARE "")
  ELSEIF(TELESCOPE STREQUAL "SIMULATOR")
    set(TELESCOPE_LIBRARY "telescope")
    set(TELESCOPE_DIR "Simulator")
    set(WEATHER_LIBRARY "weather")
    set(WEATHER_HARDWARE "")
  ELSE()
    message ("ERROR: No telescope found to compile: \${TELESCOPE}=" ${TELESCOPE})
  ENDIF()
ELSE()
  message ("ERROR: TELESCOPE variable not set")
ENDIF(TELESCOPE)
message ("TELESCOPE_LIBRARY variable set: \${TELESCOPE_LIBRARY}=" ${TELESCOPE_LIBRARY})
message ("WEATHER_LIBRARY variable set: \${WEATHER_LIBRARY}=" ${WEATHER_LIBRARY})
message ("TELESCOPE_DIR variable set: \${TELESCOPE_DIR}=" ${TELESCOPE_DIR})


################################################################################
# DON'T CHANGE ANYTHING UNDER THIS LINE!

# Set compiler options
set (COMPILER_OPTIONS "-Wall -g -O0 -march=native -DREENTRANT -Wuninitialized")
set (GOOGLE_PERFORMANCE "-ltcmalloc -lprofiler")
#set (COMPILER_OPTIONS "-Wall -g -O2 -DREENTRANT")
#set (GOOGLE_PERFORMANCE "")

# Set paths so libraries and executables end up in the lib and bin directories
set (EXECUTABLE_OUTPUT_PATH ${PROJECT_BASE_DIR}/bin)
set (LIBRARY_OUTPUT_PATH ${PROJECT_BASE_DIR}/lib)

# Make some directories necessary for the project
file (MAKE_DIRECTORY 
	${PROJECT_BASE_DIR}/bin 
	${PROJECT_BASE_DIR}/lib 
	${PROJECT_BASE_DIR}/Logs 
	${PROJECT_BASE_DIR}/Status 
)

# Set some convenient path variables for the file structure
set (PROJECT_BIN_DIR ${PROJECT_BASE_DIR}/bin)
set (PROJECT_LIB_DIR ${PROJECT_BASE_DIR}/lib)
set (PROJECT_SRC_DIR ${PROJECT_BASE_DIR}/src)

# Define the configuration file for the software common class
# We need to do this here so it finds the common.cfg, which then defines
# all of the rest of the configuration parameters.
set (COMMON_CONFIG_FILE "\"${PROJECT_BASE_DIR}/Config/common.cfg\"")
configure_file (
	"${PROJECT_SRC_DIR}/utils/common.h.in"
	"${PROJECT_SRC_DIR}/utils/common.h"
)

# Define the base directory in the common.cfg configuration file in the
# same way, so that both point to the same place.
configure_file (
	"${PROJECT_BASE_DIR}/Config/common.cfg.in"
	"${PROJECT_BASE_DIR}/Config/common.cfg"
)

# Add the src directory so it is built
add_subdirectory (${PROJECT_SRC_DIR})


