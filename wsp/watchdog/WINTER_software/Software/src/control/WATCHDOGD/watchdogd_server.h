/**
 \file watchdogd_server.h
 \brief Header file for watchdog system server control software.
 \details Controls the operation of the watchdog system server.
 
 Copyright (c) 2009-2022 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
*/

// Use a preprocessor statement to set a variable that checks if the header has
// already loaded...this avoids loading the header file more than once.
# ifndef WATCHDOGD_SERVER_H
# define WATCHDOGD_SERVER_H

// Global include files
# include <iostream>
# include <iomanip>

// Local include files
# include "robo_server.h"
# include "watchdogd.h"
# include "watchdogd_client.h"
# include "state.h"

/** \namespace ROBO_watchdog
 Namespace for the ROBO_watchdog watchdog status functions.  */
namespace ROBO_watchdog {
  
  
  /** \class Host
   \brief Watchdog host information container.
   \details This class holds information for a watchdog host computer. */
  class Host
  {
  public:
    
    std::string name;
    
    std::string IP_address;
    
    int chain_ID;
    
  };
  
  /** \class Server
   \brief ROBO_watchdog control server class.
   \details This class sets up the watchdogd server that is used to pass the
   status of the watchdog system to the rest of the software. */
  class Server: public ROBO_server::Server
  {
  private:
    
    /** \var ROBO_watchdog::State state
     \details Tracks the state of the various watchdog system functions */
    ROBO_watchdog::State state;
    
    /** \var Config config
     \details configuration file class container */
    Config config;
    
    /** \var ROBO_status status_info
     \details Status file information container for the status system */
    ROBO_status status_info;
    
    /** \var boost::thread robo_thread
     \details Thread variable that talks to the robotic system */
    boost::thread robo_thread;
    
//    ROBO_state::Daemon_state control_state;

    std::string control_hostname;

    std::vector<ROBO_watchdog::Host> hosts;
    
    std::string my_hostname;
    
    bool connection_open;
    
    bool connected;
    
    bool command_timeout;
    
    bool watchdog_shutdown;

    // Create a thread group for the watchdog connections
    boost::thread_group dogs;
    

    /**************** ROBO_watchdog::Server::initialize_class ****************/
    /**
     This initializes the class functions for the server.  It is created
     separately for each class that inherits from this class.  Each class will
     have individual variables that have to be initialized, but they should also
     start all the threads and initialize the common variables.
     */
    void initialize_class(std::string logname_in);
    /**************** ROBO_watchdog::Server::initialize_class ****************/
    
    /**************** ROBO_watchdog::Server::handle_command ****************/
    /**
     This handles any commands that are sent to the server.  Every server is
     different, so while these functions will all be structured and operate
     similarly, what they handle will be completely different.  This function
     runs in a thread started by the control() function each time a command is
     sent to the server.
     */
    void handle_command();
    /**************** ROBO_watchdog::Server::handle_command ****************/
    
    /**************** ROBO_watchdog::Server::control ****************/
    /**
     Main control function that runs in a separate thread.  This is the function
     that communicates with the clients.  Commands are received, and the
     handle_command() function is started in a separate thread.  Replies are sent
     to clients as appropriate for commands.  Each second, an output status
     message is also sent out.
     */
    void control();
    /**************** ROBO_watchdog::Server::control ****************/
    
    /**************** ROBO_watchdog::Server::status ****************/
    /**
     This function is run in a separate thread.  It is used to monitor the status
     of the daemon subsystems.  Each second, the status is composed and saved in
     a class variable that is then sent to the clients by the control() function.
     The status is completely different for every subsystem, each will have its
     own function to do this.
     */
    void status();
    /**************** ROBO_watchdog::Server::status ****************/
    
    // Prepares to execute a command and launches the handle_command thread
    bool prepare_command(TCPIP::tcpip_server & server, int cmd,
                         time_t command_timeout, std::string cmd_string,
                         bool interrupt);
    
    // Handles the configuration file
    int get_config();
    
    // Thread to handle watching and communicating with the robotic system
    void robo_watch();
    
    // Function that handles watching other watchdogs
    void watch_me(ROBO_watchdog::Host watchdog_host);
    
    int send_command(ROBO_watchdog::Client & client, int watchdog_ID, ROBO_state::Daemon_state & control_state);
    int wait_for_timeout(ROBO_watchdog::Client & client, int watchdog_ID, ROBO_state::Daemon_state & control_state);

  public:
    
    /**************** ROBO_watchdog::Server::Server ****************/
    /**
     The constructor for the server class.
     \param [port_in]  Input port for the server
     */
    Server(ROBO_port port_in, std::string logname_in)
    {
      // The input port for the server
      this->port = port_in;
      
      // Initialize the class settings, and start the control threads
      this->initialize_class(logname_in);
    }
    /**************** ROBO_watchdog::Server::Server ****************/
    
    /**************** ROBO_watchdog::Server::~Server ****************/
    /**
     The destructor for the server class.  Don't put anything in this, unless
     there is something specific to the ROBO_watchdog system.  This will call 
     the base class destructor, which handles shutting down threads and stopping 
     the system.
     \note None.
     */
    ~Server()
    {
    	// Join the thread talking to the robotic system
    	this->robo_thread.join();
      // Join the threads talking to other watchdogs
      this->dogs.join_all();
    }
    /**************** ROBO_watchdog::Server::~Server ****************/
    
    
  };
  
  
}

# endif
