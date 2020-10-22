/**
 \file robo_client.h
 \brief Header file for client communications.
 \details This file handles the client communications side of the ROBO 
 server-client architecture.
 
 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
 
 <b>Version History</b>:
 \verbatim
 \endverbatim
 */

// Use a preprocessor statement to set a variable that checks if the header has
// already loaded...this avoids loading the header file more than once.
# ifndef ROBO_CLIENT_H
# define ROBO_CLIENT_H

# include <iostream>
# include <iomanip>
# include <vector>

// Local include files
# include "common.h"
# include "file_ops.h"
# include "communications.h"


namespace ROBO_client {

  /**************** ROBO_client::read_message ****************/
  /**
   Takes a string from a message passed to the system and converts it into 
   tokens that are passed back.
   \param [message] The input message string
   \return [tokens] A string vector of tokens from the message string
   \note None.
   */
  inline std::vector<std::string> read_message(std::string message)
  {
    std::vector<std::string> tokens;  // Temporary tokens
    
    // Use the tokenizer to break up the message
    Tokenize(message, tokens, " \t\n\0\r");
    
    // Return the tokens
    return (tokens);
  }
  /**************** ROBO_client::read_message ****************/
  
  

  
  /** \class Information
   \brief Client information container
   \details Contains the information used by the ROBO client communications
   system to determine the state of the communication process.  This includes
   error code passing and control of the server-client connection. */
  class Information {
  public:
    
    /** \var mutable boost::mutex ao_control_mutex
     \details Mutex for blocking AO control variables */
    mutable boost::mutex info_mutex;
    
    /** \var int command_timeout
     \details Time, in seconds, for a command to time out.  Sent for each
     command sent to the server */
    time_t timeout;
    
    /** \var int command_number
     \details The command number, used to track which command was sent to 
     the server */
    int command_number;
    
    /** \var int command_code
     \details The command code sent to the server */
    int command_code;
    
    /** \var bool message_received
     \details Flag if a message was received from the server */
    bool message_received;
    
    /** \var bool command_sent
     \details Flag if a command was sent to the server */
    bool command_sent;
    
    /** \var bool shutdown_server
     \details Flag to shut the server down */
    bool shutdown_server;
    
    /** \var bool shutdown_client_thread
     \details Flag to terminate the client thread, so it will not stay open
     and stop the thread from joining */
    bool shutdown_client_thread;
    
    /** \var ROBO_port port
     \details The connection port for the daemon.  Standard ports used by the
     ROBO system are defined in communications.h. */
    ROBO_port port;
    
    /** \var std::string hostname
     \details The hostname of the telescope interface, or IP addresss */
    std::string hostname;
    
    /** \var std::string daemon_executable
     \details The executable name of the daemon.  This is used when the 
     daemon crashes to restart it */
    std::string daemon_executable;
    
    /** \var std::stringstream daemon_options
     \details Options sent to the daemon when restarting it.  These match the
     command line options used to launch the daemon, make sure they are
     correct of the client can't automatically start the daemon. */
    std::stringstream daemon_options;
    
    /** \var pid_t daemon_pid
     \details Process ID number of the daemon.  This is used to kill the 
     daemon if it hangs up. */
    pid_t daemon_pid;
    
    /** \var time_t time_wait
     \details The time to wait for something to happen */
    time_t time_wait;
    
    /** \var bool waiting
     \details Flag that the subsystem is waiting for something to happen */
    bool waiting;    
    
    /** \var bool error_found
     \details Flag that an error was sent by the server */
    bool error_found;
    
    /** \var int error_code
     \details Value of the error code sent by the server */
    int error_code;
    
    /** \var bool command_error_found
     \details Flag that an error was returned after a command was sent to the 
     server */
    bool command_error_found;

    /** \var bool busy_signal
     \details Flag that an busy signal was returned after a command was sent to 
     the server */
    bool busy_signal;

    /** \var int command_error_code
     \details Value of error code returned from a command sent to the server */
    int command_error_code;

    /** \var int last_error
     \details Last error code sent by the server */
    int last_error;
        
    /** \var int connect_attempts
     \details Number of attempts to connect to the server */
    int connect_attempts;
    
    /** \var int reset_attempts
     \details Number of attempts to restart a server that is not connecting */
    int reset_attempts;
    
    /** \var std::string client_name
     \details Name of the client connection */
    std::string client_name;
    
    /** \var bool telemetry_only
     \details Flag that this is a telemetry channel, this keeps the system from
     using the wrong port to restart a daemon when there are both command and
     telemetry channels available for connection. */
    bool telemetry_only;

    /** \var bool connected
     \details Flag that the client is connected to the server. */
    bool connected;
    
    /** \var std::vector<std::string> params
     \details Parameters in a message from the server. */
    std::vector<std::string> params;
    
    /** \var bool reading_message
     \details Signal flag that the client is reading a message from the server.
     This should be checked before trying to read the client message, just to 
     make sure the message is complete. */
    bool reading_message;


    Information()
    {
      this->initialize();
    };
    

    /**************** ROBO_client::Information::initialize ****************/
    /**
     Initializes the Information class with default variable values.
     \note None.
     */
    void initialize()
    {

      // Set the server communication variables to defaults
      this->timeout = 0;
      this->command_number = -1;
      this->command_code = -1;
      this->message_received = false;
      this->command_sent = false;
      this->shutdown_server = false;
      this->shutdown_client_thread = false;
      this->telemetry_only = false;
      this->reading_message = false;

      // Set the server connection variables to defaults
      this->connect_attempts = 0;
      this->reset_attempts = 0;
      
      // Set the waiting variables to an initial state
      this->waiting = false;
      this->time_wait = 0;
      
      // Set the error check variables to no error state
      this->error_found = false;
      this->command_error_found = false;
      this->error_code = NO_ERROR;
      this->command_error_code = NO_ERROR;
      this->last_error = NO_ERROR;
      this->busy_signal = false;
      this->connected = false;
    }
    /**************** ROBO_client::Information::initialize ****************/

  };
  
  
  /**************** ROBO_client::handle_received_message ****************/
  /**
   Handle server messages returned with the RECEIVED header.  These are 
   messages sent by the ROBO communications system that let the client
   know a message was received properly by the server and a command is being
   processed.
   \param [info] The info class container for the client
   \param [log] The ROBO logfile the client is writing to
   \param [inbound_message] The inbound message from the server
   \param [tokens] The tokens from the inbound message
   \param [function] The name of the function calling this function
   \note The inbound message has to be tokenized before calling this in order
   to know that the RECEIVED header was found.
   */
  inline int handle_received_message(ROBO_client::Information & info,
                                     ROBO_logfile & log,
                                     std::string & inbound_message, 
                                     std::vector<std::string> & tokens,
                                     std::string & function)
  {
    std::stringstream log_message;  // Temporary log message stream

    // A RECEIVED message should have at least four tokens: 
    // RECEIVED <command_number> <time_out> <inbound_message>
    // The message may have more parameters associated with it.  Return an error
    // if the message is less than 4 tokens long.
    if (tokens.size() < 4){
      log_message << "bad  RECEIVED message received from server, message: "
                  << inbound_message;
      log.write(function, true, log_message.str());
      return (ERROR);
    }
    // Otherwise, process the message
    else {
      {
        boost::lock_guard<boost::mutex> lock(info.info_mutex);
        info.command_number = atoi(tokens[1].c_str());
        info.timeout = atoi(tokens[2].c_str());
        info.message_received = true;
        info.command_sent = false;
      }
      log_message << "command received by server, number "
                  << info.command_number << " command " 
                  << common_info.comreg.get_code(atoi(tokens[3].c_str())) 
                  << " with timeout " << info.timeout 
                  << " seconds.  Command string received: \"" 
                  << inbound_message << "\"";
      log.write(function, false, log_message.str());
    }
    
    // Return no error if the message is good
    return (NO_ERROR);
  }
  /**************** ROBO_client::handle_received_message ****************/

  
  /**************** ROBO_client::handle_complete_message ****************/
  /**
   Handle server messages returned with the COMPLETE header.  These are 
   messages sent by the ROBO communications system that let the client
   know a command has completed.  An error code is included that flags if there
   was a problem executing the command.
   \param [info] The info class container for the client
   \param [log] The ROBO logfile the client is writing to
   \param [inbound_message] The inbound message from the server
   \param [tokens] The tokens from the inbound message
   \param [function] The name of the function calling this function
   \note The inbound message has to be tokenized before calling this in order
   to know that the COMPLETE header was found.
   */
  inline int handle_complete_message(ROBO_client::Information & info,
                                     ROBO_logfile & log,
                                     std::string & inbound_message, 
                                     std::vector<std::string> & tokens,
                                     std::string & function)
  {
    std::stringstream log_message;  // Temporary log message stream
  
    // A COMPLETE message should have at least three tokens: 
    // COMPLETE <command_number> <error code>   [<extra_info>]
    // The message may have more parameters associated with it.  Return an error
    // if the message is less than 3 tokens long.
    if (tokens.size() < 3){
      log_message << "bad COMPLETE message received from server, message: "
                  << inbound_message;
      log.write(function, true, log_message.str());
      return (ERROR);
    }
    // Otherwise, process the message
    else {
      log_message << "command " << info.command_number 
                  << " completed by server, message: " << inbound_message;
      {
        boost::lock_guard<boost::mutex> lock(info.info_mutex);
        info.command_number = -1;
        info.timeout = 0;
        info.busy_signal = false;
        info.message_received = false;
        info.command_error_code = atoi(tokens[2].c_str());
        info.reading_message = true;
      }
      if (info.command_error_code != NO_ERROR){
        log_message << " - ERROR found: " 
                    << common_info.erreg.get_code(info.command_error_code);
        info.error_found = true;
      }
      else {
        boost::lock_guard<boost::mutex> lock(info.info_mutex);
        info.error_found = false;
      }
      // If a message has parameters, capture them
      boost::lock_guard<boost::mutex> lock(info.info_mutex);
      info.params.clear();
      if (tokens.size() > 3){
        for (unsigned int i = 3; i < tokens.size(); i++){
          info.params.push_back(tokens[i]);
        }
      }
     log.write(function, false, log_message.str());
    }

    // Return no error if the message is good
    return (NO_ERROR);
  }
  /**************** ROBO_client::handle_complete_message ****************/

  
  /**************** ROBO_client::handle_welcome_message ****************/
  /**
   Handle server messages returned with the WELCOME header.  These are 
   messages sent by the ROBO communications system that let the client
   know a command has completed.  An error code is included that flags if there
   was a problem executing the command.
   \param [info] The info class container for the client
   \param [log] The ROBO logfile the client is writing to
   \param [inbound_message] The inbound message from the server
   \param [tokens] The tokens from the inbound message
   \param [function] The name of the function calling this function
   \note The inbound message has to be tokenized before calling this in order
   to know that the WELCOME header was found.
   */
  inline int handle_welcome_message(ROBO_client::Information & info,
                                    ROBO_logfile & log,
                                    std::string & function,
                                    TCPIP::tcpip_client & client,
                                    int process_code)
  {
    std::stringstream log_message;  // Temporary log message stream
    

    log.write(function, false, "server connection established");
    {
      boost::lock_guard<boost::mutex> lock(info.info_mutex);
      info.connect_attempts = 0;
      info.reset_attempts = 0;
      info.error_code = NO_ERROR;
      info.error_found = false;
    }
    
    std::stringstream request;
    request << process_code;
    client.get_session()->single_send(request.str());

    // Return no error if the message is good
    return (NO_ERROR);
  }
  /**************** ROBO_client::handle_welcome_message ****************/

  
  /**************** ROBO_client::handle_process_message ****************/
  /**
   Handle server messages returned with the PROCESS header.  These are 
   messages sent by the ROBO communications system that let the client
   know a command has completed.  An error code is included that flags if there
   was a problem executing the command.
   \param [info] The info class container for the client
   \param [log] The ROBO logfile the client is writing to
   \param [inbound_message] The inbound message from the server
   \param [tokens] The tokens from the inbound message
   \param [function] The name of the function calling this function
   \note The inbound message has to be tokenized before calling this in order
   to know that the PROCESS header was found.
   */
  inline int handle_process_message(ROBO_client::Information & info,
                                    ROBO_logfile & log,
                                    std::string & inbound_message, 
                                    std::vector<std::string> & tokens,
                                    std::string & function)
  {
    std::stringstream log_message;  // Temporary log message stream
    
    if (tokens.size() < 5){
      log_message << "bad PROCESS message received from server, message: "
              << inbound_message;
      log.write(function, true, log_message.str());
      boost::lock_guard<boost::mutex> lock(info.info_mutex);
      info.error_found = false;
      return (ERROR);
    }
    else {
      {
        boost::lock_guard<boost::mutex> lock(info.info_mutex);
        info.command_number = atoi(tokens[1].c_str());
        info.command_error_code = atoi(tokens[2].c_str());
        info.daemon_executable = tokens[3];
//      info.daemon_pid = atoi(tokens[4].c_str());
      }
      
      std::vector<int> pid;
      int err = is_process_running(info.daemon_executable, pid);
      if (err == NO_ERROR){
        boost::lock_guard<boost::mutex> lock(info.info_mutex);
        info.daemon_pid = pid[0];
      }
      else if (err == ERROR){
        log_message << "command " << info.command_number
                << " complete, more than one executable process \"" 
                << info.daemon_executable << "\" is running!";
        log.write(function, true, log_message.str());
        return (ERROR);
      }

      /*info.command_number = atoi(tokens[1].c_str());
      info.daemon_executable = tokens[2];
      info.daemon_pid = atoi(tokens[3].c_str());*/
      log_message << "command " << info.command_number
              << " complete, executable is \"" << info.daemon_executable
              << "\", PID " << info.daemon_pid;
      log.write(function, false, log_message.str());
      info.initialize();
      
      /*info.command_number = -1;
      info.timeout = 0;
      info.message_received = false;
      info.error_found = false;*/
    }

    // Return no error if the message is good
    return (NO_ERROR);
  }
  /**************** ROBO_client::handle_process_message ****************/

  
  /**************** ROBO_client::handle_client_exit_message ****************/
  /**
   Handle server messages returned with the PROCESS header.  These are 
   messages sent by the ROBO communications system that let the client
   know a command has completed.  An error code is included that flags if there
   was a problem executing the command.
   \param [info] The info class container for the client
   \param [log] The ROBO logfile the client is writing to
   \param [inbound_message] The inbound message from the server
   \param [tokens] The tokens from the inbound message
   \param [function] The name of the function calling this function
   \note The inbound message has to be tokenized before calling this in order
   to know that the PROCESS header was found.
   */
  inline int handle_client_exit_message(ROBO_client::Information & info,
                                    ROBO_logfile & log,
                                    std::string & inbound_message, 
                                    std::vector<std::string> & tokens,
                                    std::string & function)
  {
    std::stringstream log_message;  // Temporary log message stream
    
    log.write(function, false, "client exit command received");

    // Return no error if the message is good
    return (NO_ERROR);
  }
  /**************** ROBO_client::handle_client_exit_message ****************/
  
  
  /************** ROBO_client::handle_client_shutdown_message **************/
  /**
   Handle server messages returned with the PROCESS header.  These are 
   messages sent by the ROBO communications system that let the client
   know a command has completed.  An error code is included that flags if there
   was a problem executing the command.
   \param [info] The info class container for the client
   \param [log] The ROBO logfile the client is writing to
   \param [inbound_message] The inbound message from the server
   \param [tokens] The tokens from the inbound message
   \param [function] The name of the function calling this function
   \note The inbound message has to be tokenized before calling this in order
   to know that the PROCESS header was found.
   */
  inline int handle_client_shutdown_message(ROBO_client::Information & info,
                                    ROBO_logfile & log,
                                    std::string & inbound_message, 
                                    std::vector<std::string> & tokens,
                                    std::string & function)
  {
    std::stringstream log_message;  // Temporary log message stream
    
    log.write(function, false, "client shutdown command received");

    // Return no error if the message is good
    return (NO_ERROR);
  }
  /************** ROBO_client::handle_client_shutdown_message **************/
  
  
  /************** ROBO_client::handle_server_shutdown_message **************/
  /**
   Handle server messages returned with the PROCESS header.  These are 
   messages sent by the ROBO communications system that let the client
   know a command has completed.  An error code is included that flags if there
   was a problem executing the command.
   \param [info] The info class container for the client
   \param [log] The ROBO logfile the client is writing to
   \param [inbound_message] The inbound message from the server
   \param [tokens] The tokens from the inbound message
   \param [function] The name of the function calling this function
   \note The inbound message has to be tokenized before calling this in order
   to know that the PROCESS header was found.
   */
  inline int handle_server_shutdown_message(ROBO_client::Information & info,
                                    ROBO_logfile & log,
                                    std::string & inbound_message, 
                                    std::vector<std::string> & tokens,
                                    std::string & function)
  {
    std::stringstream log_message;  // Temporary log message stream
    
    log.write(function, false, "server shutdown command received");
    boost::lock_guard<boost::mutex> lock(info.info_mutex);
    info.command_number = -1;
    info.timeout = 0;
    info.message_received = false;

    // Return no error if the message is good
    return (NO_ERROR);
  }
  /************** ROBO_client::handle_server_shutdown_message **************/
  
  
  /**************** ROBO_client::handle_server_close_message ****************/
  /**
   Handle server messages returned with the PROCESS header.  These are 
   messages sent by the ROBO communications system that let the client
   know a command has completed.  An error code is included that flags if there
   was a problem executing the command.
   \param [info] The info class container for the client
   \param [log] The ROBO logfile the client is writing to
   \param [inbound_message] The inbound message from the server
   \param [tokens] The tokens from the inbound message
   \param [function] The name of the function calling this function
   \note The inbound message has to be tokenized before calling this in order
   to know that the PROCESS header was found.
   */
  inline int handle_server_close_message(ROBO_client::Information & info,
                                    ROBO_logfile & log,
                                    std::string & inbound_message, 
                                    std::vector<std::string> & tokens,
                                    std::string & function)
  {
    std::stringstream log_message;  // Temporary log message stream
    
    log.write(function, false, "server closing command received");

    // Return no error if the message is good
    return (NO_ERROR);
  }
  /**************** ROBO_client::handle_server_close_message ****************/
  
  
  /**************** ROBO_client::handle_confirm_message ****************/
  /**
   Handle server messages returned with the PROCESS header.  These are 
   messages sent by the ROBO communications system that let the client
   know a command has completed.  An error code is included that flags if there
   was a problem executing the command.
   \param [info] The info class container for the client
   \param [log] The ROBO logfile the client is writing to
   \param [inbound_message] The inbound message from the server
   \param [tokens] The tokens from the inbound message
   \param [function] The name of the function calling this function
   \note The inbound message has to be tokenized before calling this in order
   to know that the PROCESS header was found.
   */
  inline int handle_confirm_message(ROBO_client::Information & info,
                                    ROBO_logfile & log,
                                    std::string & inbound_message, 
                                    std::vector<std::string> & tokens,
                                    std::string & function)
  {
    std::stringstream log_message;  // Temporary log message stream
    
    log.write(function, false, "internal confirmation received");
    
    // Return no error if the message is good
    return (NO_ERROR);
  }
  /**************** ROBO_client::handle_confirm_message ****************/
  
  
  /**************** ROBO_client::handle_busy_message ****************/
  /**
   Handle server messages returned with the BUSY header.  These are
   messages sent by the ROBO communications system that let the client
   know a command is still in progress.  
   \param [info] The info class container for the client
   \param [log] The ROBO logfile the client is writing to
   \param [inbound_message] The inbound message from the server
   \param [tokens] The tokens from the inbound message
   \param [function] The name of the function calling this function
   \note The inbound message has to be tokenized before calling this in order
   to know that the PROCESS header was found.
   */
  inline int handle_busy_message(ROBO_client::Information & info,
                                    ROBO_logfile & log,
                                    std::string & inbound_message,
                                    std::vector<std::string> & tokens,
                                    std::string & function)
  {
    std::stringstream log_message;  // Temporary log message stream
    
    info.busy_signal = true;
    
    log.write(function, false, "busy message received");
    
    // Return error flag, busy messages shouldn't happen if the software is
    // written correctly
    return (ERROR);
  }
  /**************** ROBO_client::handle_busy_message ****************/
  
  
  /**************** ROBO_client::handle_error_message ****************/
  /**
   Handle server messages returned with the PROCESS header.  These are 
   messages sent by the ROBO communications system that let the client
   know a command has completed.  An error code is included that flags if there
   was a problem executing the command.
   \param [info] The info class container for the client
   \param [log] The ROBO logfile the client is writing to
   \param [inbound_message] The inbound message from the server
   \param [tokens] The tokens from the inbound message
   \param [function] The name of the function calling this function
   \note The inbound message has to be tokenized before calling this in order
   to know that the PROCESS header was found.
   */
  inline int handle_error_message(ROBO_client::Information & info,
                                    ROBO_logfile & log,
                                    std::string & inbound_message, 
                                    std::vector<std::string> & tokens,
                                    std::string & function)
  {
    std::stringstream log_message;  // Temporary log message stream
    
    if (tokens.size() != 2){
      log_message << "bad ERROR message received from server, message: "
              << inbound_message << " tokens: ";
      for (unsigned int i = 0; i < tokens.size(); i++){
        log_message << "|" << tokens[0] << "| ";
      }
      log.write(function, true, log_message.str());
      return (ERROR);
    }
    else {
      info.error_code = atoi(tokens[1].c_str());
      if (info.error_code != info.last_error){
        log_message << "error message sent by server, code: " 
                << info.error_code << ", message: " << inbound_message;
        log.write(function, true, log_message.str());
        boost::lock_guard<boost::mutex> lock(info.info_mutex);
        info.error_found = true;
        info.last_error = info.error_code;
      }
    }
    
    // Return no error if the message is good
    return (NO_ERROR);
  }
  /**************** ROBO_client::handle_error_message ****************/
  
  
  /**************** ROBO_client::server_reconnect ****************/
  /**
   Reset the server connection when it is unexpectedly dropped.  This causes
   clients to automatically restart the server process and reconnect.  This
   should not be called when servers are turned off purposefully, for obvious
   reasons.
   \param [info] The info class container for the client
   \param [log] The ROBO logfile the client is writing to
   \param [function] The name of the function calling this function
   \note None.
   */
  inline void server_reconnect(ROBO_client::Information & info, 
                               ROBO_logfile & log, 
                               std::string & function,
                               TCPIP::tcpip_client & client)
  {
    
    // First try to reconnect to the server, up to the maximum attempt value
    if (info.connect_attempts < MAX_ATTEMPTS){
      log.write(function, true, 
                "server connection lost! attempting reconnect...");      
      // Reconnect the client 
      client.reconnect();
      // Time out to give the system extra time to make the connection
      timeout(0.2);
      // Increment the connection attempt counter
      boost::lock_guard<boost::mutex> lock(info.info_mutex);
      info.connect_attempts++;
    }

    // If the maximum attempts are reached and the connection is still broken, 
    // assume the server has crashed in some way.  Kill and restart it, up 
    // until the maximum attempts.
    else if (info.connect_attempts >= MAX_ATTEMPTS && 
             info.reset_attempts < MAX_ATTEMPTS){
      if (info.telemetry_only == true){
        timeout(10);
        // Increment the reset attempts counter, and reset the connection attempt
        // counter to 0, so that connection attempts start at the beginning.
        boost::lock_guard<boost::mutex> lock(info.info_mutex);
        info.reset_attempts++;
        info.connect_attempts = 0;
      }
      else {
      log.write(function, true, 
                      "server connection lost! trying to restart server...");
      
      // Reset the server
      reset_server(info.daemon_executable, info.daemon_pid, 
                   info.port, info.daemon_options.str(), info.hostname);
      // Time out to let the server come back up.
      timeout(0.1);
      // Increment the reset attempts counter, and reset the connection attempt
      // counter to 0, so that connection attempts start at the beginning.
      boost::lock_guard<boost::mutex> lock(info.info_mutex);
      info.reset_attempts++;
      info.connect_attempts = 0;
      }
    }
    
    // If the server won't come back up, log the error and shut the client down
    else {
      log.write(function, true, 
                "cannot connect to or restart server, giving up!");
      boost::lock_guard<boost::mutex> lock(info.info_mutex);
      info.shutdown_client_thread = true;
      info.reset_attempts = 0;
      info.connect_attempts = 0;
    }

  }
  /**************** ROBO_client::server_reconnect ****************/

  
}

# endif
