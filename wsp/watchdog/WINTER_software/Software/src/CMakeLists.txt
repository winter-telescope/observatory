# src//CMakeLists.txt
#
# cmake configuration file for the src directory

# Set a minimum version for cmake; old versions won't work
cmake_minimum_required (VERSION 2.6) 


##### Find include files needed by the project

# Find the Boost header file and include that directory
find_path(BOOST_INCLUDE thread.hpp 
    PATHS
    /usr/include
    /usr/local/include
    /usr/include/boost
)
# If the include file is not found, throw an error
IF(${BOOST_INCLUDE} MATCHES "NOTFOUND")
  message ("Error:  \${BOOST_INCLUDE}=" ${BOOST_INCLUDE})
ENDIF(${BOOST_INCLUDE} MATCHES "NOTFOUND")


include_directories (${BOOST_INCLUDE}
                    )


##### Find library files needed by the project

# Find the Boost system library file
find_library(BOOST_SYSTEM boost_system NAMES libboost_system
PATHS
/lib64
/usr/lib64
/usr/lib
/usr/local/lib64
/usr/local/lib
/sw/lib
/opt/local/lib
/lib
)
# If the library file is not found, throw an error
IF(${BOOST_SYSTEM} MATCHES "NOTFOUND")
message ("Error:  \${BOOST_SYSTEM}=" ${BOOST_SYSTEM})
ENDIF(${BOOST_SYSTEM} MATCHES "NOTFOUND")

# Find the Boost system library file
find_library(BOOST_FILESYSTEM boost_filesystem NAMES libboost_filesystem
PATHS
/lib64
/usr/lib64
/usr/lib
/usr/local/lib64
/usr/local/lib
/sw/lib
/opt/local/lib
/lib
)
# If the library file is not found, throw an error
IF(${BOOST_FILESYSTEM} MATCHES "NOTFOUND")
message ("Error:  \${BOOST_FILESYSTEM}=" ${BOOST_FILESYSTEM})
ENDIF(${BOOST_FILESYSTEM} MATCHES "NOTFOUND")

# Find the Boost thread library file
find_library(BOOST_MT_LIB boost_thread NAMES libboost_thread
    PATHS
    /lib64
    /usr/lib64
    /usr/lib
    /usr/local/lib64
    /usr/local/lib
    /sw/lib
    /opt/local/lib
    /lib
)
# If the library file is not found, throw an error
IF(${BOOST_MT_LIB} MATCHES "NOTFOUND")
  message ("Error:  \${BOOST_MT_LIB}=" ${BOOST_MT_LIB})
ENDIF(${BOOST_MT_LIB} MATCHES "NOTFOUND")



# Add the utils directory so it is built
add_subdirectory (${PROJECT_SRC_DIR}/utils)

# Add the control directory so it is built
add_subdirectory (${PROJECT_SRC_DIR}/control)

