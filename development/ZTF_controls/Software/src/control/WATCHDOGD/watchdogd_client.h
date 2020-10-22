/**
 \file watchdogd_client.cpp
 \brief Client interface for watchdog daemon interactions.
 \details This is the client software for the interactions with the watchdog
 system.
 
 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
 
 <b>Version History</b>:
 \verbatim
 \endverbatim
 */


# ifndef WATCHDOGD_CLIENT_H
# define WATCHDOGD_CLIENT_H

# include <iostream>
# include <iomanip>

// Local include files
# include "common.h"
# include "communications.h"
# include "robo_client.h"
# include "watchdogd.h"

/** \namespace ROBO_watchdog
 Namespace for the ROBO_watchdog status functions.  */
namespace ROBO_watchdog {
  
  /** \class Client
   \brief Manages the watchdog client interaction
   \details This class holds the information required to manage the client
   connections to the watchdog daemon. */
  class Client {
  private:
    
    /** \var TCPIP::tcpip_client client
     \details The TCP/IP client object used to control the
     communications between server and client. */
    TCPIP::tcpip_client client;
    
    /** \var boost::thread input_thread
     \details Boost thread object used to launch the client thread */
    boost::thread input_thread;
    
    /** \var int number
     \details Tracks the number of this client, multiple clients possible */
    int number;

    /** \var ROBO_logfile log
     \details Log file class container */
    ROBO_logfile log;
    
    
    /**************** ROBO_watchdog::Client::watchdogd_client ****************/
    /**
     This function is the thread that handles client communications with the
     watchdogd server.  Messages are sent directly to the server, and the response
     comes to this thread which handles it appropriately, based on the token at
     the start of the response string.  The thread exits when the client
     connection is terminated; to restart the thread you have to reinitialize the
     connection.
     \note None.
     */
    void watchdogd_client()
    {
      // Log opening the client thread
      std::string function("ROBO_watchdog::Client::watchdogd_client");
      if (this->number != 0){
        function = function + "(" + num_to_string(this->number) + ")";
      }
      this->log.write(function, false, "watchdog client thread started");
      
      boost::mutex::scoped_lock watchdog_lock(this->watchdog_mutex);
      watchdog_lock.unlock();
      
      this->info.connect_attempts = 0;
      this->info.reset_attempts = 0;
      this->info.last_error = NO_ERROR;
      this->info.connected = false;

      // The thread should stay active until the client is shut down
      while(this->info.shutdown_client_thread == false) {
        // Execute the thread once per millisecond, just to save system resources
        timeout(0.001);
//        usleep(1000);
        
        // This loop is executed as long as the client is open
        if (this->client.get_session()->is_open() == true){
          this->info.connected = true;

          // Reset the error code if the daemon connection was dropped but is
          // now back up
          if (this->info.error_code == ROBO_watchdog::WATCHDOGD_ERROR_DAEMON_CONNECTION){
            this->info.error_code = NO_ERROR;
            this->info.error_found = false;
          }
          
          // Check for an inbound message
          if(this->client.has_inbound_command()) {
            std::stringstream log_message;  // Temporary log message stream
            
            // Get the inboound message from the server
            std::string inbound_message(this->client.get_inbound_command());
            // Tokenize the inbound message for reading
            std::vector<std::string> tokens =
            ROBO_client::read_message(inbound_message);
            
//            std::cout << inbound_message << std::endl << std::flush;
            
            if (tokens.size() < 1){
              log.write(function, true,
                        "zero length message received from server!");
              continue;
            }
            
            // This flags that a message was received by the server
            if (tokens[0].compare(0, 8, "RECEIVED") == 0){
              
              int err = ROBO_client::handle_received_message(this->info,
                                  this->log, inbound_message, tokens, function);
              if (err == ERROR){
                this->info.command_error_code =
                		ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR;
              }
              
            }
            else if (tokens[0].compare(0, 8, "COMPLETE") == 0 &&
                     atoi(tokens[1].c_str()) == this->info.command_number){
              
              int err = ROBO_client::handle_complete_message(this->info,
                                  this->log, inbound_message, tokens, function);
              if (err == ERROR){
                this->info.command_error_code =
                		ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR;
              }
              
            }
            else if (tokens[0].compare(0, 5, "ERROR") == 0){
              
              int err = ROBO_client::handle_error_message(this->info,
                                  this->log, inbound_message, tokens, function);
              if (err == ERROR){
                this->info.command_error_code =
                		ROBO_watchdog::WATCHDOGD_ERROR_CONTROL_ERROR;
              }
              
              
            }
            else if (tokens[0].compare(0, 7, "WELCOME") == 0){
              
              int err = ROBO_client::handle_welcome_message(this->info,
                                          this->log, function, this->client,
																					ROBO_watchdog::PROCESS_INFO);
              if (err == ERROR){
                this->info.command_error_code =
                		ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR;
              }
            }
            else if (tokens[0].compare(0, 4, "EXIT") == 0){
              int err = ROBO_client::handle_client_exit_message(this->info,
                                  this->log, inbound_message, tokens, function);
              if (err == ERROR){
                this->info.command_error_code =
                		ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR;
              }
            }
            else if (tokens[0].compare(0, 7, "PROCESS") == 0){
              
              int err = ROBO_client::handle_process_message(this->info,
                                  this->log, inbound_message, tokens, function);
              if (err == ERROR){
                this->info.command_error_code =
                		ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR;
              }
              
            }
            else if (tokens[0].compare(0, 6, "IMGONE") == 0){
              int err = ROBO_client::handle_client_shutdown_message(this->info,
                                  this->log, inbound_message, tokens, function);
              if (err == ERROR){
                this->info.command_error_code =
                		ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR;
              }
            }
            else if (tokens[0].compare(0, 8, "SHUTDOWN") == 0){
              int err = ROBO_client::handle_server_shutdown_message(this->info,
                                  this->log, inbound_message, tokens, function);
              if (err == ERROR){
                this->info.command_error_code =
                		ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR;
              }
            }
            else if (tokens[0].compare(0, 6, "GOHOME") == 0){
              int err = ROBO_client::handle_server_close_message(this->info,
                                  this->log, inbound_message, tokens, function);
              if (err == ERROR){
                this->info.command_error_code =
                		ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR;
              }
            }
            else if (tokens[0].compare(0, 7, "CONFIRM") == 0){
              int err = ROBO_client::handle_confirm_message(this->info,
                                  this->log, inbound_message, tokens, function);
              if (err == ERROR){
                this->info.command_error_code =
                		ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR;
              }
            }
            else if (tokens[0].compare(0, 4, "BUSY") == 0){
              int err = ROBO_client::handle_busy_message(this->info,
                                  this->log, inbound_message, tokens, function);
              if (err == ERROR){
                this->info.command_error_code =
                    ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR;
              }
            }
            else if (tokens[0].compare(0, 6, "STATUS") == 0){
              if (tokens.size() < 5){
                log_message << "bad STATUS message received from server, message: "
                    << inbound_message << " " << tokens.size() << " tokens: ";
                for (unsigned int i = 0; i < tokens.size(); i++){
                  log_message << "|" << tokens[i] << "| ";
                }
                log.write(function, true, log_message.str());
                this->info.command_error_code =
                		ROBO_watchdog::WATCHDOGD_CONTROL_STATUS_ERROR;
              }
              
              this->watchdog_message = inbound_message;
              int err = this->state.load_state(this->watchdog_message);
              if (err != NO_ERROR){
                log_message << "error loading watchdog state, code: "
                            << common_info.erreg.get_code(err);
                this->log.write(function, true, log_message.str());
              }
            }
            else {
              log_message << "unknown message sent by server: "
                          << inbound_message;
              this->log.write(function, true, log_message.str());
              this->info.command_error_code =
                          ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR;
            }
          }
        }
        else {
          this->info.error_code = ROBO_watchdog::WATCHDOGD_ERROR_DAEMON_CONNECTION;
          this->info.error_found = true;
          this->info.connected = false;
          
          ROBO_client::server_reconnect(this->info, this->log, function,
                                          this->client);
        }
      }
      
      this->log.write(function, false, "watchdog client thread exiting");
    }
    /**************** ROBO_watchdog::Client::watchdogd_client ****************/
    
    
  public:
    
    
    ROBO_watchdog::State state;
    
    ROBO_client::Information info;
    
    /** \var std::string watchdog_message
     \details Status message string passed from the watchdog server to be
     interpreted by software on the client side. */
    std::string watchdog_message;
    
    mutable boost::mutex watchdog_mutex;

    /**************** ROBO_watchdog::Client::Client ****************/
    /** Constructor
     Creates the watchdog client object.  This object is used to read
     data from the watchdogd daemon.
     */
    Client(char* host_in, char* port_in, int num = 0):client(host_in, port_in)
    {
      // Run the initialization routine
      this->initialize(host_in, port_in, num);
    }
    /**************** ROBO_watchdog::Client::Client ****************/

    
    /**************** ROBO_watchdog::Client::~Client ****************/
    /**
     
     \note None.
     */
    /** Deconstructor
     Shuts down the watchdog client object.  Can also shut down the
     data server if the proper signal is sent.
     */
    ~Client()
    {
      
      std::string function("ROBO_watchdog::~Client");
      if (this->number != 0){
        function = function + "(" + num_to_string(this->number) + ")";
      }

      this->info.shutdown_client_thread = true;
      
      if (this->info.shutdown_server == true){
        this->log.write(function, false,
                        "shutting down watchdogd server and client");
        this->client.get_session()->shutdown();
      }
      else {
        this->log.write(function, false, "shutting down watchdogd client");
        timeout();
        this->client.stop();
      }
      
      input_thread.join();
    }
    /**************** ROBO_watchdog::Client::~Client ****************/
    
    
    /*********** ROBO_watchdog::Client::set_server_shutdown_flag ***********/
    /**
     
     \note None.
     */
    void set_server_shutdown_flag(bool flag)
    {
      std::string function("ROBO_watchdog::Client::set_server_shutdown_flag");
      if (this->number != 0){
        function = function + "(" + num_to_string(this->number) + ")";
      }
      std::stringstream log_message;
      
      this->info.shutdown_server = flag;
      
      log_message << "setting server shutdown flag to ";
      if (flag == true)
        log_message << "true";
      else
        log_message << "false";
      
      this->log.write(function, false, log_message.str());
    }
    /*********** ROBO_watchdog::Client::set_server_shutdown_flag ***********/
    
    
    /*********** ROBO_watchdog::Client::get_server_shutdown_flag ***********/
    /**
     
     \note None.
     */
    bool get_server_shutdown_flag()
    {
      return (this->info.shutdown_server);
    }
    /*********** ROBO_watchdog::Client::get_server_shutdown_flag ***********/
    
    
    /*********** ROBO_watchdog::Client::set_client_shutdown_flag ***********/
    /**
     
     \note None.
     */
    void set_client_shutdown_flag(bool flag)
    {
      std::string function("ROBO_watchdog::Client::set_client_shutdown_flag");
      if (this->number != 0){
        function = function + "(" + num_to_string(this->number) + ")";
      }
      std::stringstream log_message;
      
      this->info.shutdown_client_thread = flag;
      
      log_message << "setting client shutdown flag to ";
      if (flag == true)
        log_message << "true";
      else
        log_message << "false";
      
      this->log.write(function, false, log_message.str());
    }
    /*********** ROBO_watchdog::Client::set_client_shutdown_flag ***********/
    
    
    /*********** ROBO_watchdog::Client::get_client_shutdown_flag ***********/
    /**
     
     \note None.
     */
    bool get_client_shutdown_flag()
    {
      return (this->info.shutdown_client_thread);
    }
    /*********** ROBO_watchdog::Client::get_client_shutdown_flag ***********/
    
    
    /**************** ROBO_watchdog::Client::send_message ****************/
    /**
     
     \note None.
     */
    int send_message(std::stringstream & message)
    {
      std::string function("ROBO_watchdog::Client::send_message");
      if (this->number != 0){
        function = function + "(" + num_to_string(this->number) + ")";
      }
 
      double end_time = get_clock_time() + 5.0;
      bool sent = true;
      {
        boost::lock_guard<boost::mutex> lock(this->info.info_mutex);
        this->info.command_sent = true;
      }

      this->client.process_outbound_command(message.str());
      
      while (sent == true){
        timeout(0.0001);
        if (get_clock_time() > end_time){
          this->log.write(function, true, "error sending the message!");
          return (ERROR);
        }
        boost::lock_guard<boost::mutex> lock(this->info.info_mutex);
        sent = this->info.command_sent;
      }
      
      return (NO_ERROR);

//      time_t current_time;
//      time_t start_time;
//
//      this->client.process_outbound_command(message.str());
//      this->info.command_sent = true;
//
//      start_time = time(NULL);
//      while (this->info.command_sent == true){
//        timeout(0.00001);
////        usleep(1000);
//        current_time = time(NULL);
//        if (current_time > start_time + 5){
//          this->log.write(function, true, "error sending the message!");
//          return (ERROR);
//        }
//      }
//      return (NO_ERROR);
      
    }
    /**************** ROBO_watchdog::Client::send_message ****************/
    
    
    /**************** ROBO_watchdog::Client::initialize ****************/
    /**
     
     \note None.
     */
    void initialize(char* host_in, char* port_in, int & num)
    {
      std::string function("ROBO_watchdog::Client::initialize");
      // Set the ID number
      this->number = num;
      if (this->number != 0){
        function = function + "(" + num_to_string(this->number) + ")";
      }
      
      
      // Set the log file name to the class log name and open the log
      this->log.filename = common_info.log_dir + common_info.executable_name
                                      + "_client.log";
//      this->log.filename = common_info.log_dir + "watchdogd.log";
      
      this->log.write(function, false, "opening watchdogd client connection");
      
      this->info.timeout = 0;
      this->info.command_number = -1;
      this->info.message_received = false;
      this->info.command_sent = false;
      this->info.shutdown_server = false;
      this->info.shutdown_client_thread = false;
      this->info.port = (ROBO_port) atoi(port_in);
      this->info.hostname = host_in;
      this->info.daemon_executable = "watchdogd";
      this->info.daemon_pid = BAD_VALUE;
      
      ROBO_watchdog::watchdog_registry_codes(this->log);
      
      this->client.run();
      
      this->input_thread = boost::thread(&ROBO_watchdog::Client::watchdogd_client,
                                         this);
      
    }
    /**************** ROBO_watchdog::Client::initialize ****************/
    
    
    /**************** ROBO_watchdog::Client::shutdown ****************/
    /**
     
     \note None.
     */
    void shutdown(bool flag = false)
    {
      std::string function("ROBO_watchdog::Client::shutdown");
      this->log.write(function, false, "closing watchdogd client connection");
      
      //      this->info.shutdown_client_thread = true;
      this->set_server_shutdown_flag(flag);
      this->set_client_shutdown_flag(true);
      timeout(0.01);
      
      //      this->set_server_shutdown_flag(flag);
      //      this->set_client_shutdown_flag(true);
      
      if (this->info.shutdown_server == true){
        this->log.write(function, false,
                        "shutting down watchdogd server and client");
        std::stringstream request;
        request << ROBO_watchdog::SHUTDOWN;
        this->send_message(request);
        this->client.get_session()->shutdown();
      }
      else {
        this->log.write(function, false, "shutting down watchdogd client");
//        timeout();
//        this->client.stop();
      }
      
      timeout();
      this->client.stop();

      input_thread.join();
      
      this->log.write(function, false, "watchdogd client connection closed");
    }
    /**************** ROBO_watchdog::Client::shutdown ****************/
    
    
  };
  
}

# endif
