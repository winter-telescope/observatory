/**
 \file watchdogd_server.cpp
 \brief watchdog server control software.
 \details Controls the operation of the watchdog system server.
 
 Copyright (c) 2009-2022 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
 */

// Global include files
# include <cstdlib>
# include <iostream>
# include <fstream>
# include <boost/thread.hpp>
# include <dirent.h>

// Local include files
# include "communications.h"
# include "watchdogd.h"
# include "watchdogd_server.h"
# include "robod_client.h"
//# include "robo.h"

/** \namespace ROBO_watchdog
 Namespace for the ROBO_watchdog functions */
namespace ROBO_watchdog {
  

  /**************** ROBO_watchdog::Server::initialize_class ****************/
  /**
   This initializes the class functions for the server.
   */
  void Server::initialize_class(std::string logname_in)
  {
    this->log.filename = common_info.log_dir + logname_in + ".log";
    
    // Log that the server is being initialized
    std::string function("ROBO_watchdog::Server::initialize_class");
    std::stringstream message;
  
    this->log.write(function, false, "starting the watchdogd server system");

    // Set default values for class variables
    this->command = 0;
    this->command_number = 0;
    this->processing_command = false;
    this->server_name = "ROBO_watchdog::Server::";
    this->max_watchdog_diff = 5;
    this->status_updated = false;
    this->system_initialized = false;
    this->connection_open = true;
    this->connected = false;
    this->command_timeout = false;
    this->watchdog_shutdown = false;

    // Register the watchdog system and error codes into the registry system
    ROBO_watchdog::watchdog_registry_codes(this->log);
    
    // Get the computer hostname
    char hostname[HOST_NAME_MAX];
    int out;
    out = gethostname(hostname, HOST_NAME_MAX-1);
    if (out != 0){
      std::stringstream message;  // A stream for messages to be logged
      message << "bad hostname found: " << hostname << " Using default!";
      common_info.log.write(function, true, message.str());
      message.str("");
      strcpy(hostname, "BADHOST");
    }
    this->my_hostname = hostname;
    
    // Set the configuration file name
    this->config.filename = common_info.config_dir + "watchdog.cfg";
    
    // Get the configuration information
    if (this->get_config() != NO_ERROR){
      this->log.write(function, true, "failed to read configuration file!");
      return;
    }

    
    // Change the operating flag to true so that everything runs
    this->operating = true;
    
    // Start the threads
    this->control_thread = boost::thread(&ROBO_watchdog::Server::control, this);
    this->status_thread = boost::thread(&ROBO_watchdog::Server::status, this);
    this->watchdog_thread = boost::thread(&ROBO_watchdog::Server::watchdog, this);

    // If the hostname matches the control hostname, start the watchdog thread
    // that talks to the robotic system and threads that talk to to each of the
    // other watchdogs
    if (this->control_hostname.compare(this->my_hostname) == 0){
      this->robo_thread = boost::thread(&ROBO_watchdog::Server::robo_watch, this);
      for (unsigned int i = 0; i < this->hosts.size(); i++){
        if (this->control_hostname.compare(this->hosts[i].name) != 0){
          this->dogs.add_thread(new boost::thread(&ROBO_watchdog::Server::watch_me, this, this->hosts[i]));
        }
      }
    }
    // Otherwise, just start the thread to talk to the main watchdog
    else {
      for (unsigned int i = 0; i < this->hosts.size(); i++){
        if (this->control_hostname.compare(this->hosts[i].name) == 0){
          this->dogs.add_thread(new boost::thread(&ROBO_watchdog::Server::watch_me, this, this->hosts[i]));
        }
      }
    }
    
    // Flag as initialized
    this->state.initialized = true;

    // Log that initialization is complete
    this->log.write(function, false, "watchdogd server system now running");
  }
  /**************** ROBO_watchdog::Server::initialize_class ****************/
  
  
  /**************** ROBO_watchdog::Server::handle_command ****************/
  /**
   This handles any commands that are sent to the server.  This function
   runs in a thread started by the control() function each time a command is
   sent to the server.
   */
  void Server::handle_command()
  {
    std::string function("ROBO_watchdog::Server::handle_command");
    
    std::stringstream message("");  // A stream for messages to be logged
    std::stringstream reply;        // Temporary reply string
    std::stringstream output;             // Output string from commands

    // Local copy of the command to run
    int local_command;
    
    // Set up the command to run
    boost::mutex::scoped_lock lock(this->command_mutex);
    this->processing_command = true;
    local_command = this->command;
    message << "executing command number " << this->command_number
            << ", command: " << common_info.comreg.get_code(local_command)
            << " " << this->print_params(this->command_tokens);
    // Make a copy of the input command tokens
    std::vector<std::string> tokens(this->command_tokens);
    lock.unlock();
    // Remove the first token
    tokens.erase(tokens.begin());
    
    // Log that the command thread is starting
    this->log.write(function, false, message.str());
    message.str("");
    
    boost::this_thread::interruption_point();  // Point to interrupt thread
    
    // Execute the input command.  This switch should be populated with all of
    // the possible commands.  An unknown command will send an error back.
    switch (local_command){
        
      case ROBO_watchdog::START_WATCHDOG:
        this->connection_open = true;;
        output << NO_ERROR;
        break;
        
      case ROBO_watchdog::PAUSE_WATCHDOG:
        this->connection_open = false;;
        output << NO_ERROR;
        break;
        
     case ROBO_watchdog::PROCESS_INFO:
      {
        std::stringstream temp;
        temp << NO_ERROR << " " << common_info.executable_name << " "
            << common_info.pid;
        output << temp.str();
        break;
      }
        
      // This shuts the server down completely.  Until this command is received
      // the server should continue to run.
      case ROBO_watchdog::SHUTDOWN:
        this->log.write(function, false,
                        "watchdog daemon termination command received, shutting down");
        lock.lock();
        this->operating = false;
        this->watchdog_shutdown = true;
        lock.unlock();
        output << NO_ERROR;
        break;
      
      case ROBO_watchdog::EMERGENCY_SHUTDOWN:
        this->log.write(function, false,
                        "emergency shutdown command received, shutting down");
        lock.lock();
        this->operating = false;
        this->watchdog_shutdown = true;
        lock.unlock();
        output << NO_ERROR;
        break;
        
        // Catch any other commands, nothing else should do anything
      default:
        message << "Unknown command! Entered command code: " << command;
        this->log.write(function, true, message.str());
        output << ROBO_watchdog::ERROR_UNKNOWN;
    }
    
    message.str("");
    
    boost::this_thread::interruption_point();  // Point to interrupt thread
    
    // Put the right key onto the reply message. This is read by the client to
    // determine what kind of message is being passed back to the system.
    if (local_command == ROBO_watchdog::SHUTDOWN){
      reply << TCPIP::SHUTDOWN_COMMAND;
    }
    else if (local_command == ROBO_watchdog::PROCESS_INFO){
      reply << TCPIP::PROCESS_MESSAGE;
    }
    else {
      reply << TCPIP::COMPLETE_MESSAGE;
    }
    
    boost::this_thread::interruption_point();  // Point to interrupt thread
    
    // Build the reply message for the client.  Replies to the clients have the
    // format "key command_number output_string", where the output string is
    // formatted by the interface software.
    lock.lock();
    reply << " " << this->command_number << " " << output.str();
    // Put the reply in the class variable so the control thread can see it.
    this->command_reply = reply.str();
    message << "command number " << this->command_number
            << " complete, output: " << this->command_reply;
    // This flag signals the control thread that the command is complete.  This
    // makes the control thread send the reply message to the client.
    this->processing_command = false;
    this->command = 0;
    lock.unlock();
    
    // Log that the command is complete
    this->log.write(function, false, message.str());
  }
  /**************** ROBO_watchdog::Server::handle_command ****************/
  

  /**************** ROBO_watchdog::Server::control ****************/
  /**
   Main control function that runs in a separate thread.  This is the function
   that communicates with the clients.  Commands are received, and the
   handle_command() function is started in a separate thread.  Replies are sent
   to clients as appropriate for commands.  Each second, an output status
   message is also sent out.
   */
  void Server::control()
  {
    // Log that the control thread is starting
    std::string function("ROBO_watchdog::Server::control");
    this->log.write(function, false, "starting watchdogd system control thread");
    
    // Start the TCP/IP service so that clients can connect to the server
    boost::asio::io_service io_service;
		TCPIP::tcpip_server server(io_service, this->port);
		server.run();
		
    // Get the time for the server thread.  The last_time variable is used to
    // check when a second has elapsed, at which point a status message is sent.
    boost::mutex::scoped_lock lock(this->command_mutex);
    bool local_operating = this->operating;
    this->server_time = time(NULL);
    lock.unlock();
    
	int command_timeout = 0;          // Time to complete a command
  	bool client_connected = false;    // Flag if clients are connected
    bool command_in_progress = false; // Local variable to flag a command is running
    
    // Continue to do this while the server is operating
		while(server.get_session()->is_open() && local_operating == true){
			
      // The time() function returns UNIX time at an integer second.  If the
      // current time is greater than last_time, then a second has passed.  At
      // that point, a status message is sent to the client (this has to be
      // formatted properly in the status() function), and last_time is reset
      // to the current time.
      lock.lock();
      this->server_time = time(NULL);
      if (this->status_updated == true){
        server.process_inbound_command(this->current_status.str());
        this->status_updated = false;
      }
      lock.unlock();
      
      //  Handle an inbound command sent to the server from a client
      if(server.has_inbound_command()){
        
        std::stringstream reply;    // Temporary reply string
        
        // Read the incoming message from the client into a string
        std::string incoming(server.get_inbound_command());
			  
        // Tokenize the string, and extract the number of tokens and the command
        // code.  This is blocked as the information is shared.
        lock.lock();
        this->command_tokens.clear();
        this->command_tokens = this->read_message(incoming);
        int num_tokens = this->command_tokens.size();
			  int cmd = atoi(this->command_tokens[0].c_str());
        lock.unlock();
        
        // A blank command is ignored.  If blank commands are sent the client is
        // doing something wrong and should be fixed.
        if (num_tokens == 0){
          this->log.write(function, true,
                          "zero length command sent to server, ignoring");
          continue;
        }
			  
        // Command abort template, figure it out later
        // if (cmd == ABORT){
        //   this->command_thread.interrupt;
        //   this->processing_command = false;
        // log
        //   continue;
        // }
        
        // If the server is already handling a command, send a busy message.
        // The server could stack commands in a queue, but to make things simple
        // the system is only going to do one thing at a time.
        if (command_in_progress == true){
          this->log.write(function, true,
                    "messaged already executing command, ignoring new command");
          lock.lock();
          reply << TCPIP::BUSY_MESSAGE << this->command_number;
          server.get_session()->single_send(reply.str());
          lock.unlock();
          continue;
        }
			  
		  switch (cmd){
        case ROBO_watchdog::SHUTDOWN:
		  	default:
		  		command_timeout = 5;
		  }
        
        command_in_progress = this->prepare_command(server, cmd, command_timeout,
                                                    incoming, false);
        
      }
      
      
      
      // When the current command finishes, the processing_command flag is set
      // to false.  At that point, the command is complete, triggering this
      // statement to send the output message of the command back to the client.
      lock.lock();
      if (command_in_progress == true && this->processing_command == false){
        command_in_progress = false;
        server.process_inbound_command(this->command_reply);
      }
      else if (command_in_progress == false && this->processing_command == true){
        command_in_progress = true;
      }
      lock.unlock();
      
      //      // Check for system errors, and pass the error back to the client
      //      lock.lock();
      //      local_error_code = this->viscam.error.code;
      //      lock.unlock();
      //      if (local_error_code != NO_ERROR){
      //        std::stringstream reply;    // Temporary reply string
      //
      //        reply << TCPIP::ERROR_MESSAGE << local_error_code;
      //
      //        server.process_inbound_command(reply.str());
      //      }
      
      // If the server has an outbound message in the queue, send it out.
      if (server.has_outbound_command()){
        std::string outmessage = server.get_outbound_command();
        server.process_outbound_command(outmessage);
      }
      
      // Check the client connection.  If there aren't any connected clients,
      // then log that and take any necessary actions to stop operations.
      if(server.get_session()->connection_count() > 0){
        client_connected = true;
      }
      else if(server.get_session()->connection_count() == 0){
        if (client_connected == true){
          this->log.write(function, false,
                          "all watchdogd daemon clients disconnected");
          client_connected = false;
        }
      }
      
      // Wait for a short amount of time (the delay keeps the process from using
      // too much system resources) and then check the operating flag.
      timeout(0.01);
      //      usleep(1000);
      lock.lock();
      local_operating = this->operating;
      lock.unlock();
    }
    
    // Once the operating flag is changed to false, stop the TCP/IP server and log
    // that the thread is stopping.
    server.stop();
    this->log.write(function, false, "shutting down watchdogd system control thread");
  }
  /**************** ROBO_watchdog::Server::control ****************/
  
  
  /**************** ROBO_watchdog::Server::status ****************/
  /**
   This function is run in a separate thread.  It is used to monitor the status
   of the daemon subsystems.  Each second, the status is composed and saved in
   a class variable that is then sent to the clients by the control() function.
   */
  void Server::status()
  {
    // Log that the thread is starting operation
    std::string function("ROBO_watchdog::Server::status");
    this->log.write(function, false, "starting watchdogd status thread");
    
    // Initialize the status containers that write message to the status files
    // and the telemetry directory.  In this case, one is for the status of the
    // camera system and the other is the last image gathered by the camera.
    this->status_info.initialize("watchdogd", common_info.status_dir,
                                 common_info.telemetry_dir);
    
    // Get the class operating flag value, and set the thread time that is
    // checked by the watchdog to make sure the thread is not locked
    boost::mutex::scoped_lock lock(this->command_mutex);
    bool local_operating = this->operating;
    this->status_time = time(NULL);
    lock.unlock();
    
    // Do this until the class operating flag is switched to false
    std::string now;
    while(local_operating == true){
      
      // Check if the config file has been modified
      if (this->config.modified() == true){
        log.write(function, false, "configuration file has changed, reloading");
        if (this->get_config() != NO_ERROR){
          log.write(function, true, "error reading configuration file!");
        }
      }

      // Set the status string and the thread time.  These are used in other
      // thread so block them while setting.
      lock.lock();
      this->status_time = time(NULL);
      this->state.status_time  = this->status_time;
      now = get_current_time(SECOND_MILLI);
      this->state.update_time.set_time(now, ROBO_time::TIMEFMT_Y_M_D_H_M_S);

      this->status_info.temp_status
        << this->state.status_time << " "
        << this->state.update_time.get_time(ROBO_time::TIMEFMT_Y_M_D_H_M_S)
        << " " << this->state.initialized
        << " " << this->state.error_code
				;
      
      this->status_info.temp_status << std::endl;
      
      // Print the status information out to the system
      this->status_info.print_status(false);
      
      this->current_status.str("");
      this->current_status << TCPIP::STATUS_MESSAGE << " "
        << this->status_info.current_status.str();
      
      this->status_updated = true;
      
      lock.unlock();
      
      // Wait until the end of the second, then get the operating flag value
      timeout();
      lock.lock();
      local_operating = this->operating;
      lock.unlock();
      
//std::cout << "watchdogd server status: " << this->current_status.str() << std::endl;
    }
    
    // Log that the thread is exiting
    this->log.write(function, false, "shutting down watchdogd status thread");
  }
  /**************** ROBO_watchdog::Server::status ****************/
  
  
  /**************** ROBO_watchdog::Server::prepare_command ****************/
  /**
   This function prepares the parameters for a command to be processed, sends a
   response to the client that a command was received, and launches the command
   thread.
   \param [server] The TCPIP information container for the server
   \param [cmd] Command being sent to the laser
   \param [command_timeout] The timeout for the command
   \param [cmd_string] The command string to send to the client
   \param [interrupt] Flag to interrupt a command that is already running
   */
  bool Server::prepare_command(TCPIP::tcpip_server & server, int cmd,
                               time_t command_timeout, std::string cmd_string,
                               bool interrupt)
  {
    std::stringstream reply;
    // Interrupt the command thread
    if (interrupt == true){
      if (this->processing_command == true){
        this->command_thread.interrupt();
      }
    }
    
    // Set the command parameters
    boost::mutex::scoped_lock lock(this->command_mutex);
    this->command = cmd;
    this->command_number++;
    if (this->command_number == 15000){
      this->command_number = 0;
    }

    this->command_tokens.clear();
    this->command_tokens = this->read_message(cmd_string);
    reply << TCPIP::RECEIVED_MESSAGE << this->command_number << " "
          << command_timeout << " " << cmd_string;
    this->processing_command = true;
    lock.unlock();
    
    // Send the reply string.  This tells the client that the command was
    // received and is being executed, and the maximum time that the command
    // execution should take.
    server.get_session()->single_send(reply.str());
    
    // Launch the command thread
    this->command_thread = boost::thread(&ROBO_watchdog::Server::handle_command,
                                         this);
    this->command_thread.detach();

    // Set the local flag to track that a command is running.
    return(true);
  }
  /**************** ROBO_watchdog::Server::prepare_command ****************/
  
  
  /*************** ROBO_watchdog::Server::get_config *******************/
  /**
   * Reads the configuration file into the config class variable. This requires
   * setting the file name variable (config.filename) to the configuration file
   * before calling this routine. The configuration file must be set up with
   * variable=value pairs in the same format as a Bash script:
   * \code
   * # Configuration file directory
   * CONFIG_DIR="/home/bob/Config/"
   * \endcode
   * \return NO_ERROR if the configuration file is read properly, ERROR if not.
   * \note The configuration filename is set in initialize_class, if it changes
   * for some reason that change must be applied before get_config() is called.
   */
  int Server::get_config()
  {
    std::string function("ROBO_watchdog::Server::get_config");
    std::stringstream message;
    
    message << "reading config file " << this->config.filename;
    log.write(function, false, message.str());
    message.str("");
    
    int error_code = NO_ERROR;
    
    if (this->config.filename.empty() == true) {
      log.write(function, true, "no config file specified!");
      return (ERROR);
    }
    
    // After reading, toss any errors back from the file reading system.
    error_code = this->config.read_config(this->config);
    if (error_code != NO_ERROR) {
      message << "file error thrown, error code: "
              << common_info.erreg.get_code(error_code);
      this->log.write(function, true, message.str());
      return (ERROR);
    }
    
    // Set the parameter values, do some checking along the way
    for (int i=0; i<this->config.n_elements; i++) {
      
      if (config.vars[i].compare("CONTROL_HOSTNAME") == 0){
        this->control_hostname = this->config.params[i];
      }
      
      else if (config.vars[i].compare("WATCHDOG_HOST") == 0){
        std::vector<std::string> tokens;
        int err = Tokenize(this->config.params[i], tokens, " \"");
        // There are 3 elements to a host entry
        if (err == 3){
          ROBO_watchdog::Host temp;
          temp.name = tokens[0];
          temp.IP_address = tokens[1];
          temp.chain_ID = atoi(tokens[2].c_str());
          this->hosts.push_back(temp);
        }
        else {
            message << "badly formatted host entry: " << this->config.params[i]
                    << "  Skipping entry!";
            this->log.write(function, true, message.str());
            message.str("");
            continue;
          }
        }
      
      
      // found an unknown variable name, so flag it and return
      else {
        message << "unknown variable found: " << this->config.vars[i];
        this->log.write(function, true, message.str());
        return (ERROR);
      }
    }
    
    // configuration was found successfully
    this->log.write_log_config(this->config.vars, this->config.params,
                               this->config.filename);
    message << "successfully read config file " << this->config.filename;
    this->log.write(function, false, message.str());
    
    return (NO_ERROR);
  }
  /*************** ROBO_watchdog::Server::get_config *******************/
  
  
  /*************** ROBO_watchdog::Server::robo_watch *******************/
  /**
   Who watches the watchers?
   */
  void Server::robo_watch()
  {
    std::string function("ROBO_watchdog::Server::robo_watch");
    std::stringstream message;
    
    this->log.write(function, false, "starting robotic monitoring thread");
    
    // This keeps the thread running as long as the program is operating
    while (this->operating == true){
      
      // Don't do anything if the connection isn't open
      if(this->connection_open == false){
        this->connected = false;
        timeout(0.1);
        continue;
      }
      
      // When the signal is sent, open the connection
      char host[20];
      char port[20];
      sprintf(host, "localhost");
      sprintf(port, "%d", ROBO_PORT_ROBOD);
      message << "opening connection to robotic system at " << host
              << " on port " << port;
      this->log.write(function, false, message.str());
      message.str("");
      
      ROBO_state::Daemon_state control_state;
      ROBO_robotic::Client client(host, port);
      this->connected = false;
      // Wait for the connection to be made
      while(client.info.connected == false){
        timeout();
        this->connected = client.info.connected;
      }
      
      // Loop through waiting for commands and errors
      boost::mutex::scoped_lock lock(control_state.control_mutex);
      lock.unlock();
      while (this->operating == true && this->connection_open == true){
        // Check the connected flag
        this->connected = client.info.connected;
        
        // If the status has updated load the local state information
        if (client.state.updated == true){
          this->state.load_state(client.robo_message);
          boost::lock_guard<boost::mutex> lock(client.state.state_mutex);
          client.state.updated = false;
          
        }
        
        // If there is an error with the connection flag it
        control_state.error = client.info.error_code;
        if (control_state.error == ROBO_robotic::ROBOD_ERROR_DAEMON_CONNECTION){
          this->log.write(function, true, "robotic client connection error!");
          timeout(10.1);
        }
        
        timeout(0.1);
      }
      // Close the client connection when signaled
      if (control_state.daemon_shutdown == true){
        client.set_server_shutdown_flag(true);
        control_state.command = NO_COMMAND;
        control_state.daemon_shutdown = false;
        control_state.waiting = false;
        client.shutdown(true);
        this->log.write(function, false, "closing robotic monitoring system");
      }
      else {
        client.shutdown(false);
        this->log.write(function, false, 
                        "closing connection to robotic system");
      }
    }
    
    this->log.write(function, false, "stopping robotic monitoring thread");
  }
  /*************** ROBO_watchdog::Server::robo_watch *******************/
  
  
  /*************** ROBO_watchdog::Server::watch_me *******************/
  /**
   Who watches the watchers?
   */
  void Server::watch_me(ROBO_watchdog::Host watchdog_host)
  {
    std::string function("ROBO_watchdog::Server::watch_me");
    std::stringstream message;
    if (watchdog_host.chain_ID != 0){
      message << function << "[" << watchdog_host.chain_ID << "]";
      function = message.str();
      message.str("");
    }
    
    message << "starting watchdog interface control thread for watchdog on "
            << watchdog_host.name;
    this->log.write(function, false, message.str());
    message.str("");
    
    // This keeps the thread running as long as the program is operating
    while (this->operating == true){
      
      // Don't do anything if the connection isn't open
      if (this->connection_open == false){
        this->connected = false;
        timeout(0.1);
        continue;
      }
      
      // When the signal is sent, open the connection
      char host[20];
      char port[20];
      sprintf(host, watchdog_host.IP_address.c_str());
      sprintf(port, "%d", ROBO_PORT_WATCHDOGD);
      message << "opening connection to watchdog at " << host << " on port "
              << port;
      this->log.write(function, false, message.str());
      message.str("");
      
      ROBO_state::Daemon_state control_state;
      ROBO_watchdog::Client client(host, port);
      this->connected = false;
      // Wait for the connection to be made
      while(client.info.connected == false){
        timeout();
        this->connected = client.info.connected;
      }
      
      // Loop through waiting for commands and errors
      boost::mutex::scoped_lock lock(control_state.control_mutex);
      lock.unlock();
      while (this->operating == true){
        // Check the connected flag
        this->connected = client.info.connected;
        
        // If the status has updated load the local state information
        if (client.state.updated == true){
          this->state.load_state(client.watchdog_message);
          boost::lock_guard<boost::mutex> lock(client.state.state_mutex);
          client.state.updated = false;
          
        }
        
        // If there is an error with the connection flag it
        if (client.info.error_code ==
                    ROBO_watchdog::WATCHDOGD_ERROR_DAEMON_CONNECTION){
          control_state.error =
                    ROBO_watchdog::WATCHDOGD_ERROR_DAEMON_CONNECTION;
          this->log.write(function, true, "watchdog client connection error!");
          timeout();
        }
        
        timeout(0.1);
     }
      // Close the client connection when signaled
      if (this->control_hostname.compare(this->my_hostname) == 0 &&
          this->watchdog_shutdown == true){
        control_state.command = ROBO_watchdog::SHUTDOWN;
        this->send_command(client, watchdog_host.chain_ID, control_state);
        control_state.command = NO_COMMAND;
        control_state.daemon_shutdown = false;
        control_state.waiting = false;
        client.shutdown(true);
        this->log.write(function, false, "closing watchdog server system");
      }
      else {
        client.shutdown(false);
        this->log.write(function, false, 
                        "closing connection to watchdog system");
      }
    }
    
    message << "stopping watchdog interface control thread for watchdog on "
            << watchdog_host.name;
    this->log.write(function, false, message.str());
    message.str("");
  }
  /*************** ROBO_watchdog::Server::watch_me *******************/
  
  
  /**************** ROBO_watchdog::Server::send_command ****************/
  /**
   Sends a command to the Message daemon.
   \param [client] Message client class object
   \note None.
   */
  int Server::send_command(ROBO_watchdog::Client & client, int watchdog_ID, ROBO_state::Daemon_state & control_state)
  {
    std::string function("ROBO_watchdog::Server::send_command");
    std::stringstream request;
    std::stringstream message;
    if (watchdog_ID != 0){
      message << function << "[" << watchdog_ID << "]";
      function = message.str();
      message.str("");
    }
    
    // Set up parameters based on the command, then build the request string
    // to send to the daemon. You have to get these right, otherwise the
    // commands don't work. In most cases it is assumed that the error checking
    // is done before reaching this spot, and it should definitely be done by
    // the daemon that receives the commands.
    switch (control_state.command) {
        
      case ROBO_watchdog::SHUTDOWN:
        this->log.write(function, false, "shutting down watchdog");
        request << ROBO_watchdog::SHUTDOWN;
        break;
        
      case ROBO_watchdog::EMERGENCY_SHUTDOWN:
        this->log.write(function, false, "emergency shutdown of watchdog");
        request << ROBO_watchdog::EMERGENCY_SHUTDOWN;
        break;
        
      default:
        message << "unknown command: "
        << common_info.comreg.get_code(control_state.command);
        this->log.write(function, true, message.str());
        return(ERROR);
        break;
    }
    
    // Send the command
    bool busy_message = true;
    int n = 0;
    int error;
    this->command_timeout = false;
    while (busy_message == true && n < 10){
      
      error = client.send_message(request);
      
      boost::mutex::scoped_lock lock(control_state.control_mutex);
      control_state.command_error = NO_ERROR;
      lock.unlock();
      
      if (error == NO_ERROR &&
          control_state.command != ROBO_watchdog::SHUTDOWN){
        error = this->wait_for_timeout(client, watchdog_ID, control_state);
      }
      
      else {
        boost::lock_guard<boost::mutex> lock(control_state.control_mutex);
        control_state.command_error = ROBO_robotic::ERROR_WATCHDOG_CONNECTION;
        busy_message = false;
      }
      
      busy_message = client.info.busy_signal;
      if (busy_message == true){
        timeout();
        n++;
      }
    }
    
    // Handle the result of the send
    int retval;
    boost::lock_guard<boost::mutex> lock(control_state.control_mutex);
    control_state.reply.clear();
    control_state.old_command_error = control_state.command_error;
    if (busy_message == true){
      this->log.write(function, true, "client busy, message not sent!");
      retval = ERROR_CLIENT_BUSY;
    }
    else if (error == ERROR_TIMEOUT){
      this->log.write(function, true, "client command timeout!");
      this->command_timeout = true;
      control_state.command_error_found = true;
      control_state.command_error = ROBO_robotic::ERROR_WATCHDOG_TIMEOUT;
      control_state.command_error_time = time(NULL);
      control_state.command_attempts++;
      retval = ROBO_robotic::ERROR_MESSAGE_TIMEOUT;
    }
    else if (error == ROBO_robotic::ERROR_WATCHDOG_CONNECTION){
      this->log.write(function, true, "client connection error!");
      control_state.command_error_found = true;
      control_state.command_error = ROBO_robotic::ERROR_WATCHDOG_CONNECTION;
      control_state.command_error_time = time(NULL);
      control_state.command_attempts++;
      retval = ROBO_robotic::ERROR_MESSAGE_CONNECTION;
    }
    else if (client.info.command_error_code != NO_ERROR){
      message << "command error found: "
      << common_info.erreg.get_code(client.info.command_error_code);
      this->log.write(function, true, message.str());
      this->command_timeout = false;
      control_state.command_error_found = true;
      control_state.command_error = client.info.command_error_code;
      control_state.command_error_time = time(NULL);
      control_state.command_attempts++;
      retval = control_state.command_error;
    }
    else {
      this->command_timeout = false;
      control_state.command_error_found = false;
      control_state.command_error = client.info.command_error_code;
      control_state.command_error_time = 0;
      control_state.command_attempts = 0;
      retval = NO_ERROR;
    }
    
    control_state.error_attempts = 0;
    control_state.last_command = control_state.command;
    control_state.command = NO_COMMAND;
    control_state.reply = client.info.params;
    control_state.waiting = false;
    
    // Update the telemetry in case the command took a long time
    if (client.state.updated == true){
      this->state.load_state(client.watchdog_message);
      boost::lock_guard<boost::mutex> lock(client.state.state_mutex);
      client.state.updated = false;
      
    }
    
    return(retval);
  }
  /**************** ROBO_watchdog::Server::send_command ****************/
  

  /**************** ROBO_watchdog::Server::wait_for_timeout ****************/
  /**
   Waits for a Message command to timeout while being executed by the daemon.
   \param [client] Message client class object
   \note None.
   */
  int Server::wait_for_timeout(ROBO_watchdog::Client & client, int watchdog_ID, ROBO_state::Daemon_state & control_state)
  {
    std::string function("ROBO_watchdog::Server::wait_for_timeout");
    std::stringstream message;
    if (watchdog_ID != 0){
      message << function << "[" << watchdog_ID << "]";
      function = message.str();
      message.str("");
    }

    // Get the timeout value and flag the waiting state
    boost::mutex::scoped_lock lock(control_state.control_mutex);
    control_state.timeout = client.info.timeout;
    control_state.waiting = true;
    lock.unlock();
    
    // Set up the time variables
    time_t current_time;
    time_t end_time;
    end_time = time(NULL) + control_state.timeout;
    
    // Wait for the message_received flag to change to false, when the happens
    // the command processing has finished
    while (client.info.message_received == true){
      timeout(0.001);
      current_time = time(NULL);
      // Flag an error if the time exceeds the timeout
      if (current_time > end_time){
        this->log.write(function, true, "command timeout exceeded!");
        lock.lock();
        control_state.error = ROBO_robotic::ERROR_WATCHDOG_TIMEOUT;
        control_state.waiting = false;
        lock.unlock();
        return (ERROR_TIMEOUT);
      }
    }
    
    return (NO_ERROR);
  }
  /**************** ROBO_watchdog::Server::wait_for_timeout ****************/

  
  

  
  
  
  
  
}
