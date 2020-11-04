/**
 \file chiller_interface.h
 \brief Header file for control of Opti Temp Chiller devices.
 \details Contains class and variable definitions for control of Physik
 \ Instrumente Chiller devices.  (Love Controls, PLC controllers.)
 
 Copyright (c) 2009-2011 California Institute of Technology.
 \author John Cromer  cro@astro.caltech.edu
 \author Dr. Reed L. Riddle  riddle@caltech.edu
*/

// Use a preprocessor statement to set a variable that checks if the header has
// already loaded...this avoids loading the header file more than once.
# ifndef CHILLER_INTERFACE_H
# define CHILLER_INTERFACE_H

// Global include files
# include <iostream>

# include <unistd.h>
# include <fcntl.h>
# include <arpa/inet.h>
# include <netdb.h>
# include <sys/types.h>
# include <sys/socket.h>
# include <sys/ioctl.h>
# include <poll.h>

// Local include files
# include "file_ops.h"
# include "common.h"
# include "robo_client.h"
# include "communications.h"
//NPL 10-26-20 commenting out the following line bc of compile error
//# include "sensors.h"


/** \namespace Optitemp
 Namespace for the Opti Temp functions */
namespace Optitemp {
  
  /** \class Chiller_interface
   \brief Class for control of Opti Temp Chiller devices.
   \details   Control software for Chiller devices, does all of the driver
   control functions, communicates with the Chiller to set up parameters, and
   everything else necessary to run the system. */
  class Chiller_interface {
  private:
	  
    /** \var ROBO_client::Information info
     \details The connection information for the server. */
    ROBO_client::Information info;
    
    /** \var bool connection_open
     \details Flag the connection state as open (true) or closed (false) */
    bool connection_open;
    
    /** \var int sockfd
     \details  socket file descriptor for Chiller controls */
    int sockfd;

    const static int READ_REG_CMD=0x03;	//3
    const static int WRITE_REG_CMD=0x10;	//16
    
    void initialize_class();

    int modGet( int fd, unsigned char *buf, int ct);
    
    unsigned short modCRC( unsigned char *pData, int ct);
    
    int modWrite( int fd, unsigned char modaddr, unsigned short Reg, 
                 unsigned char *pData, int ct);

    int modRead( int fd, unsigned char modaddr, unsigned short Reg, 
                unsigned char *pData, int ct);
    

  public:
    
    /** \var Config config
     \details Configuration file class container */
    Config config;
    
    /** \var std::string name
     \details The text name in the config file for the device */
    std::string name;
    
    /** \var ROBO_logfile log
     \details Log file class container */
    ROBO_logfile log;
    
    // Constructors
    Chiller_interface();
    Chiller_interface(std::string logname_in);
    Chiller_interface(ROBO_logfile log_in);
    
    // Destructor
   ~Chiller_interface();
    
    // Read the configuration file
    int get_config();
    
    // Connect to the data logger
    int controllerconnect();
    
    // Disconnect from the data logger
    int disconnect();
    
    int change_temperature_setpoint(std::string setpoint);
    
    int get_state(std::vector<float> & data);
    
  };

}
# endif
