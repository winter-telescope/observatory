/**
 * @file comm.min.cpp
 * @brief Master Communications Source File
 * @date 2010-07-27
 *
 * @details Implements all of the client and server classes.
 *
 * Copyright (c) 2010 California Institute of Technology
 * @author Alexander Rudy
 * @note This file combines many other header files into one convenient one.
 *
 *
 * <b>Version History:</b>
 *
 */

// Local include files
# include "communications.h"
# include "file_ops.h"

/**
 \file tcpip_protected_queue.cpp
 \brief A thread-safe queue for TCPIP operations (and others.)
 \date 2010-06-15

 \details Will define a threadsafe TCPIP double ended queue to handle threaded operations to read and write from queues.

 Copyright (c) 2010 California Institute of Technology
 \author Alexander Rudy
 \note

 <b>Version History:</b>

 */

//REMOVED include "tcpip_protected_queue.h"

namespace TCPIP
{

  /**

   \details Constructs a protected queue, initalizing it to an unlockable state.

   */
  tcpip_protected_queue::tcpip_protected_queue() {
    locked=false;
  }

  /**

   \details Destroys the queue item and associated locks.

   */
  tcpip_protected_queue::~tcpip_protected_queue() {
  }

  /**

   \details Locks the queue item for use by this thread.

   */
  void tcpip_protected_queue::lock() {
    boost::lock_guard<boost::mutex> lock(mut);
    locked=true;
  }

  /**

   \details Relesases the queue item for use by other threads

   */
  void tcpip_protected_queue::release() {
    boost::lock_guard<boost::mutex> lock(mut);
    locked=false;
    cond.notify_one();
  }

  /**

   \details Waits for other locks to expire so it can unlock the queue item.

   */
  void tcpip_protected_queue::unlock() {
    boost::unique_lock<boost::mutex> lock(mut);
    while(locked) {
      cond.wait(lock);
    }
  }

  /**

   \details Locks the queue to prevent corruption, then tests if the queue is empty.

   */
  bool tcpip_protected_queue::empty() {
    bool retval;
    unlock();
    lock();
    retval=queue.empty();
    release();
    return retval;
  }


  /**

   \details Returns the value off of the front of the queue. Collects the value while the queue is locked.

   */
  std::string tcpip_protected_queue::front() {
    std::string retstr;
    unlock();
    lock();
    retstr=queue.front();
    release();
    return retstr;
  }


  /**

   \details Returns the value off of the back of the queue. Collects the value while the queue is locked.

   */
  std::string tcpip_protected_queue::back() {
    std::string retstr;
    unlock();
    lock();
    retstr=queue.back();
    release();
    return retstr;
  }

  /**

   \details Removes the value off of the front of the queue. Removes the value while the queue is locked.
   @return The string on the front of the queue.

   */
  void tcpip_protected_queue::pop_front() {
    unlock();
    lock();
    queue.pop_front();
    release();
  }

  /**

   \details Removes the value off of the bcak of the queue. Removes the value while the queue is locked.
   @return The string on the back of the queue.

   */
  void tcpip_protected_queue::pop_back() {
    unlock();
    lock();
    queue.pop_back();
    release();
  }

  /**

   \details Adds a value to the front of the queue. Adds the value while the queue is locked.
   @param item String to add to the front of the queue.
   */
  void tcpip_protected_queue::push_front(std::string item) {
    unlock();
    lock();
    queue.push_front(item);
    release();
  }

  /**

   \details Adds a value to the back of the queue. Adds the value while the queue is locked.
   @param item String to add to the back of the queue.
   */
  void tcpip_protected_queue::push_back(std::string item) {
    unlock();
    lock();
    queue.push_back(item);
    release();
  }


} /* TCPIP *//**
              @file tcpip_strings.cpp
              @brief Implementation of the Messaging string handlers
              @date 2010-06-14

              @details Implementation of string manipulation commands for TCPIP services

              Copyright (c) 2010 California Institute of Technology
              @author Alexander Rudy
              @note

              <b>Version History:</b>

              */


//REMOVED include "tcpip_strings.h"

/** @namespace TCPIP */
namespace TCPIP
{
  /**

   @details Constructs the string object (generic).

   */
	tcpip_strings::tcpip_strings() {}

  /**

   @details Destructs the string object (generic).

   */

	tcpip_strings::~tcpip_strings() {}

  /**

   @details Maps a command string to an integer value using a given command map.
   @param input The command to map, as a std::string.
   @param cmap The STL map of command strings to command integers
   @return An integer determining the command input for a switch control.

   */
  int tcpip_strings::get_switch(std::string input,std::map<std::string,int> cmap) {
    std::string function("TCPIP::tcpip_strings::get_switch");
    
    std::map<std::string,int>::iterator it;
    int val_switch;
    dbm(input, function, DBM_INFO);
    it=cmap.begin();
    it=cmap.find(input);
    val_switch = it->second;
    if(it==cmap.end()) val_switch=LARGE;
    return val_switch;
  }

  /**

   @details Checks a string for the presence of another string at the beginning.
   @param message A string to test for the presence of a prefix
   @param prefix A string prefix
   @return A boolean which is true if the message has the prefix.

   */
  bool tcpip_strings::check_prefix(std::string message, std::string prefix) {
    int prefixlength = prefix.length();
    std::string message_prefix=message.substr(0,prefixlength);
    return message_prefix==prefix;
  }


	/**

   @details Strips a given prefix from a message. If the message doesn't have the
   given prefix, then it is returned in its original form. Useful for passing messages between client and server.
   @param message The message from which to remove a given prefix
   @param prefix The prefix to be removed
   @return A string without the specified prefix.

   */
  std::string  tcpip_strings::strip_prefix(std::string message, std::string prefix) {
    int prefixlength = prefix.length();
    int messagelength = message.length()-prefixlength;
    if(check_prefix(message,prefix)){
      return message.substr(prefixlength,messagelength);
    }else{
      return message;
    }
  }

	/**

   @details Adds the specified prefix to a string if it is not already present. Useful for constructing messages to pass between client and server.

   */
  std::string	tcpip_strings::prep_prefix(std::string message, std::string prefix) {
    if(!check_prefix(message,prefix)){
      return prefix+message;
    }else{
      return message;
    }
  }

  /**

   \details Initializes the different command strings map which maps a string as the key to an integer for the switch.

   */
  void tcpip_strings::init_map() {
    std::string function("TCPIP::tcpip_strings::init_map");

    dbm("INFO: Basic Init Map", function, DBM_INFO);
//    premap[EXIT_MESSAGE]=EV_EXIT;
//    premap[SHUTDOWN_MESSAGE]=EV_SHUTDOWN;
//    premap[CONFIRM_MESSAGE]=EV_CONFIRM;
    // MEMORY FIX
    premap.clear();
    premap.insert(std::pair <std::string, int> (EXIT_MESSAGE, EV_EXIT));
    premap.insert(std::pair <std::string, int> (SHUTDOWN_MESSAGE, EV_SHUTDOWN));
    premap.insert(std::pair <std::string, int> (CONFIRM_MESSAGE, EV_CONFIRM));
  }
} /* TCPIP *//**
              \file tcpip_handler.cpp
              \brief Implementation of the TCPIP::tcpip_handler class
              \date 2010-06-15

              \details Implements session handling flags and methods to handle sessions and inbox and outbox.

              Copyright (c) 2010 California Institute of Technology
              \author Alexander Rudy
              \note

              <b>Version History:</b>

              */

#include <cstdlib>
#include <iostream>
#include <deque>
#include <string>

//REMOVED include "tcpip_handler.h"
//REMOVED include "tcpip_globals.h"

namespace TCPIP
{
	/**

   \details The constructor defauls several pointers which can be over-ridden.

   @note Resetting the inbox pointer (TCPIP::tcpip_handler::inbox) will add
   inbound communication to a custom queue.
   @note Resetting the outbox pointer will cause the handler to look elsewhere to
   find outbound messages.
   @note Resetting switch_local will move the local switches into a different handler object, but
   will NOT preserve their current state.
   @note Resetting switch_general will move the general switch into a different
   handler.

   */
  tcpip_handler::tcpip_handler()
  : inbox(&local_inbox),
  outbox(&local_outbox),
  switch_local(this),
  switch_general(this)
  {
		//Initialize all of the switches
    this->switch_exit=false;
    this->switch_shutdown=false;
    this->switch_triggered=false;
    this->switch_confirm=false;
    reset();
		//Initialize the command map
    init_map();
  }

	/**

   \details Destructor (generic)

   */
  tcpip_handler::~tcpip_handler () {
    std::string function("TCPIP::tcpip_handler::~tcpip_handler");
    dbm("DEST: Destroyed tcpip_handler", function, DBM_CONST);
  }


	/**

   \details Reads a command received by the handler and adds it to the inbox if it is not a control command. For control commands, they are not added to inbox, instead the handler flips the appropriate flags.
   @param command the string command to read in to the handling system.

   */
  void tcpip_handler::read(std::string command) {
    std::string function("TCPIP::tcpip_handler::read");
    dbm("START: tcpip_handler::read", function, DBM_START);
    init_map();
    int pre_switch=get_switch(command,premap);
    dbm("INFO: read switch", function, DBM_INFO);
    switch (pre_switch) {
      case EV_EXIT:
        dbm("INFO: exit switch", function, DBM_INFO);
        exit();
        trigger();
        break;
      case EV_SHUTDOWN:
        dbm("INFO: shutdown switch", function, DBM_INFO);
        shutdown();
        trigger();
        break;
      case EV_CONFIRM:
        dbm("INFO: confirm switch", function, DBM_INFO);
        confirm();
        break;
      default:
        dbm("INFO: default switch", function, DBM_INFO);
        inbox->push_back(command);
    }
    return;
  }

	/**

   \details Returns a pointer to the outbox. This will be used by the session send command
   to pass a message into the outbound session queue
   @return A pointer to the tcpip_handler::outbox structure holding strings ready to be sent.
   */
  tcpip_queue* tcpip_handler::get_outbox() {
    return outbox;
  }

	/**


   \details Returns a pointer to the inbox. This will be used by the controller to get inbound commands
   @return A pointer to the tcpip_handler::inbox structure holding strings ready to be sent.
   */
  tcpip_queue* tcpip_handler::get_inbox() {
    return inbox;
  }

	/**

   \details Sets the inbox queue for the handler object
   @param new_inbox A pointer to the new inbox object

   */
  void tcpip_handler::set_inbox(tcpip_queue* new_inbox) {
    inbox=new_inbox;
  }

	/**

   \details Sets the outbox queue for the handler object
   @param new_outbox A pointer to the new inbox object

   */
  void tcpip_handler::set_outbox(tcpip_queue* new_outbox) {
    outbox=new_outbox;
  }

	/**

   \details Uses the exit flag to determine whether the current session has a connection. This may be unsafe if the connection is dropped unexpectedly.
   @return Returns true if the session is not set to close.

   */
  bool tcpip_handler::is_open() {
    std::string function("TCPIP::tcpip_handler::is_open");
    dbm("DANGER: 	dummy is_open function from tcpip_handler.cpp", function, DBM_DANGER);
    return (!is_exit());
  }

	/**

   \details A dummy (must be overwritten) quit function.

   */
  void tcpip_handler::quit() {
    std::string function("TCPIP::tcpip_handler::quit");
    dbm("DANGER: 	dummy quit function from tcpip_handler.cpp", function, DBM_DANGER);
    return;
  }

	/**


   \details The shutdown flag is used to tell all other sessions to quit when called
   since it indicates that the server is shutting down.
   @return True if the handler has been told to shutdown.

   */
  bool tcpip_handler::is_shutdown() {
    return switch_general->switch_shutdown;
  }

	/**

   \details Marks the shutdown flag as true. The shutdown flag is used to tell all other sessions to quit when called since it indicates that the server is shutting down.

   */
  void tcpip_handler::shutdown() {
    std::string function("TCPIP::tcpip_handler::shutdown");
    dbm("NOTICE: Flipped Shutdown", function, DBM_NOTICE);
    switch_general->switch_shutdown=true;
    tcpip_handler::exit();
  }

  /**


   \details The exit flag is used to tell the current session or handler to quit.
   @return True if the exit flag has been set.

   */
  bool tcpip_handler::is_exit() {
    return switch_local->switch_exit;
  }

  /**

   \details Flips the exit flag to true. The exit flag is used to tell the current session or handler to quit.

   */
  void tcpip_handler::exit() {
    std::string function("TCPIP::tcpip_handler::exit");
    dbm("NOTICE: Flipped Exit", function, DBM_NOTICE);
    switch_local->switch_exit=true;
  }

  /**

   \details The triggered flag is used to tell the handler that it does not need to alert other
   sessions to its current command
   @return True if the handler has been triggered

   */
  bool tcpip_handler::is_triggered() {
    return switch_local->switch_triggered;
  }

  /**

   \details Sets the triggered flag to true. The triggered flag is used to tell the handler that it does not need to alert other sessions to its current command

   */
  void tcpip_handler::trigger() {
    std::string function("TCPIP::tcpip_handler::trigger");
    dbm("NOTICE: Flipped Trigger", function, DBM_NOTICE);
    switch_local->switch_triggered=true;
  }


	/**

   \details The confirmed flag is used to tell the handler that the peer has finished its remaining outbox, and the handler can close.
   @return True if the outbox of the peer has been cleared.

   */
  bool tcpip_handler::is_confirmed() {
    return switch_local->switch_confirm;
  }

	/**

   \details Sets the confirmed flag to true. The confirmed flag is used to tell the handler that the peer has finished its remaining outbox, and the handler can close.

   */
  void tcpip_handler::confirm() {
    std::string function("TCPIP::tcpip_handler::confirm");
    dbm("NOTICE: Flipped Confirm", function, DBM_NOTICE);
    switch_local->switch_confirm=true;
  }
  /**

   \details This function resets the switches which cause the handler to execute commands at appropriate times. The reset function switches trigger, shutdown and exit to false.

   */
  void tcpip_handler::reset() {
    std::string function("TCPIP::tcpip_handler::reset");
    dbm("NOTICE: Reset triggers: exit, shutdown, triggered", function, DBM_NOTICE);
    switch_local->switch_exit=false;
    switch_general->switch_shutdown=false;
    switch_local->switch_triggered=false;
    switch_local->switch_confirm=false;
  }

  /**
  *
  * @details The Basic Handler Connection Count will always return one since the handler must always represent a connection.
  *
  */
  int tcpip_handler::connection_count() {
  	return 1;
  }

} /* TCPIP *//**
              \file tcpip_session.cpp
              \brief Implements asynchronous read/write commands for clients and servers through the tcpip_session class
              \date 2010-06-15

              \details The asynchronous actions required to read and write data from other sesions, as well as closing, quitting and killing the socket connection when necessary. The implementation uses the boost::asio library.

              Copyright (c) 2010 California Institute of Technology
              \author Alexander Rudy
              \note

              <b>Version History:</b>

              */

#include <cstdlib>
#include <cstring>
#include <iostream>
#include <deque>
#include <map>


#include <boost/asio.hpp>
#include <boost/bind.hpp>
#include <boost/thread.hpp>

//REMOVED include "tcpip_session.h"
//REMOVED include "tcpip_globals.h"

/** \namespace TCPIP */
namespace TCPIP {

	using boost::asio::ip::tcp;

  /**

   \details Constructs a session and the internal objects required for the session, including the socket, and two deadline timers which handle timeouts for inbound thread operations and outbound thread operations. Also defaults the timeout to be TCPIP::SESSION_TIMEOUT.

   */
	tcpip_session::tcpip_session(boost::asio::io_service& io_service_in)
	: sock(io_service_in),
	io_service_session(io_service_in),
	timer_in(io_service_in),
	timer_out(io_service_in)
  {
    set_timeout(boost::posix_time::seconds(SESSION_TIMEOUT));
    std::string function("TCPIP::tcpip_session::tcpip_session");
    dbm("CONSTRUCTION DONE: tcpip_session", function, DBM_CONST);
    
    this->current_operation = 0;
    this->has_timeout_in = false;
    this->has_timeout_out = false;
    this->in_progress = false;
    this->timer_inbound = 0;
    this->reply_length = false;

  }

  tcpip_session::~tcpip_session() {

  }
  /**

   \details Tells the io_service to quit at the next convinent opportunity. This safely kills any currently operating asynchronous operations and should catch all errors from cutoff transmissions. This action is thread safe and can be called from any thread, as it will always post to the io_service's current thread. It will return immediately.

   When the quit action completes, the socket will show as closed from tcpip_sesion is_open.

   This method will be called automatically at the opportune time when the shutdown or exit flags have been set in the attached handler object.

   \throws Boost system error which tries to describe the last action taken, but which indicates that the session has ended. If a new session or server is needed, a new object must be created from scratch.
   */
  void tcpip_session::quit() {
    std::string function("TCPIP::tcpip_session::quit");
    dbm("BEGIN: tcpip_session::quit", function, DBM_BEGIN);
    //io_service_session.post(boost::bind(&tcpip_session::do_quit,this));
    do_quit();
  }

  /**

   \details Sends the given string in a thread safe manner through this session to its peer. If another send operation is currently running, the messages will be queued in a FILO system, so messages will always send in order. This function returns immediately.

   @param input The string message to send.

   \throws Boost system error which tries to describe the last action taken, but which indicates that the session has ended. If a new session or server is needed, a new object must be created from scratch.
   */
  void tcpip_session::send(std::string input) {
    std::string function("TCPIP::tcpip_session::send");
    dbm("BEGIN: tcpip_session::send", function, DBM_BEGIN);
    dbm("VAR input:"+input, function, DBM_VAR);
    if(is_open()) {
      outbox->push_back(input);
      dbm("VAR front of outbox:"+outbox->front(), function, DBM_VAR);
      if(!in_progress) {
        io_service_session.post(boost::bind(&tcpip_session::do_send,this));
      } else {
        dbm("INFO: Send already in progress, not posted", function, DBM_INFO);
      }
    }
  }

  /**
   
   \details Sends a single message in a threadsafe manner. This method is not safe to use if other outbound operations are in progress, as the order of these operations cannot be guaranteed. It should only be used when the caller has no expectations about the response or continuing behavior of the peer (i.e. control commands.). This function returns immediately.
   
   @param input The string message to send.
   
   \throws Boost system error which tries to describe the last action taken, but which indicates that the session has ended. If a new session or server is needed, a new object must be created from scratch.
   */
  void tcpip_session::single_send(std::string input) {
    std::string function("TCPIP::tcpip_session::single_send");
    dbm("BEGIN: tcpip_session::single_send", function, DBM_BEGIN);
    if(is_open()) {
      io_service_session.post(boost::bind(&tcpip_session::do_single_send,this,input));
    }
  }
  
  /**
   
   \details Sends a single message in a threadsafe manner. This method is not 
   safe to use if other outbound operations are in progress, as the order of 
   these operations cannot be guaranteed. It should only be used when the caller 
   has no expectations about the response or continuing behavior of the peer 
   (i.e. control commands.). This function returns immediately.  Sends the 
   input string without modification.
   
   @param input The string message to send.
   
   \throws Boost system error which tries to describe the last action taken, but 
   which indicates that the session has ended. If a new session or server is 
   needed, a new object must be created from scratch.
   */
  void tcpip_session::simple_send(std::string input) {
    std::string function("TCPIP::tcpip_session::simple_send");
    dbm("BEGIN: tcpip_session::single_send", function, DBM_BEGIN);
    if(is_open()) {
      io_service_session.post(boost::bind(&tcpip_session::do_simple_send,this,input));
    }
  }
  
  /**

   \details This function starts the io_service thread listening for incoming communications. This call returns immediately, but the underlying io_service thread will run until quit() is called or the connection dies. This method should be called as soon as the session is likely to be receiving messages.

   \throws Boost system error which tries to describe the last action taken, but which indicates that the session has ended. If a new session or server is needed, a new object must be created from scratch.

   */
  void tcpip_session::listen()
  {
    std::string function("TCPIP::tcpip_session::listen");
    dbm("BEGIN: tcpip_session::listen", function, DBM_BEGIN);
    if(is_open()) {
      io_service_session.post(boost::bind(&tcpip_session::do_recieve,this));
    }
  }

  /**

   \details Tests the socket for an open connection.
   @return True if the socket has an open connection. This may return true for sockets which have lost communication with the server but have not timed out or recognized an error yet. This is especially true for sessions which have yet to call the listen function. Once the listen function has been called, a dropped connection will close the socket immediately.

   */
  bool tcpip_session::is_open() {
    return (sock.is_open());
  }


  /**

   \details Sets the timeout expiry time. The timeout stays persistent throughout the use of the session object.
   @param t timeout duration using boost::posix_time.

   */
  void tcpip_session::set_timeout(const boost::posix_time::time_duration t) {
    timeout=t;
  }


  /**************************************
   THESE FUNCTIONS ARE PROTECTED
   **************************************/

	/**

   \details Performs the quit actions which end the current session and calls do_close on the socket. It will need to be over-written if the session must notify other objects as it closes (see server_session::do_quit)
   \note This really should be re-implemented so that it never needs to be overwritten by derived classes. The message passing should probably be handled by the quit function publicly. When overwriting, compare source from this function and the server_session::do_quit function.
   */
  void tcpip_session::do_quit()
  {
    std::string function("TCPIP::tcpip_session::do_quit");
    dbm("BEGIN: tcpip_session::do_quit", function, DBM_BEGIN);
    //Check if the action was triggered to see if we need to command the peer sessions etc. to exit/shutdown.
    if(is_triggered()){
      //The action was triggered by something else, no need to do anything.
      dbm("INFO: Was Triggered", function, DBM_INFO);
      send(CONFIRM_MESSAGE);
    }else {
      //The action was not triggered, we should tell peers to exit.
      dbm("INFO: Was not Triggered", function, DBM_INFO);
      if(is_shutdown()){
        //Since it was a shutdown, we need to tell all peers to exit.
        single_send(SHUTDOWN_MESSAGE);
      } else {
        //Since it was not a shutdown, just tell the connected peer to exit.
        single_send(EXIT_MESSAGE);
      }
    }
    //Warnings for good health.
    if(!is_exit()) {
      dbm("WARNING: tcpip_session::do_quit ran, but exit is unflagged...", function);
    }
    do_exit();
    //Tell the socket to close
    dbm("END: tcpip_session::do_quit", function, DBM_END);
  }


  void tcpip_session::do_exit() {

  }


  /**

   \details Starts a deadline timer for either an inbound or outbound function. The deadline timer call will return immediately. The timer will run until it expires or is canceled by stop_timeout(). Once this happens, the io_service will call tcpip_session::handle_timeout. If TCPIP::ENABLE_TIMEOUT is set to false, this call does nothing.
   @param inbound If it is true, the inbound timer will be set, if it is false, the outbound timer will be set.
   \note	The inbound/outbound timer distinction should be automated in a better version, this is kind of manual thread safety, although timer objects are thread safe, this just serves to make sure one thread isn't cancelling/starting the other's timeout action.

   */
  void tcpip_session::do_timeout(bool inbound) {
    std::string function("TCPIP::tcpip_session::do_timeout");
    if(ENABLE_TIMEOUT){
      //Integer for debugging timer cancel calls.
      timer_inbound=0;
      //Switch between the two timers. The nice way to do this would be to have a pointer...
      if(inbound){
        dbm("START: timeout in", function, DBM_START);
        //Alerts the session that a timeout timer has been started
        has_timeout_in=true;
        //Sets the timeout expiration time.
        timer_in.expires_from_now(timeout);
        //Starts the asynchronous timeout.
        timer_in.async_wait(boost::bind(&tcpip_session::handle_timeout,this,boost::asio::placeholders::error));
      } else {
        dbm("START: timeout out", function, DBM_START);
        //Alerts the session that a timeout timer has been started
        has_timeout_out=true;
        //Sets the timeout expiration time.
        timer_out.expires_from_now(timeout);
        //Starts the asynchronous timeout.
        timer_out.async_wait(boost::bind(&tcpip_session::handle_timeout,this,boost::asio::placeholders::error));
      }
    }
  }

  /**

   \details Stops a deadline timer for either an inbound or outbound function. The timer will then call the tcpip_session::handle_timeout function, but this call will return immediately. If TCPIP::ENABLE_TIMEOUT is set to false, this call does nothing.
   @param inbound If it is true, the inbound timer will be canceled, if it is false, the outbound timer will be canceled.
   \note	The inbound/outbound timer distinction should be automated in a better version, this is kind of manual thread safety, although timer objects are thread safe, this just serves to make sure one thread isn't cancelling/starting the other's timeout action.

   */
  void tcpip_session::stop_timeout(bool inbound) {
    std::string function("TCPIP::tcpip_session::stop_timeout");
    if(ENABLE_TIMEOUT){
      if(inbound & has_timeout_in){
        dbm("END: timeout in", function, DBM_START);
        //Timeout debugging integer
        timer_inbound=1;
        //Tells the program this timeout has been cancelled
        has_timeout_in=false;
        //Cancels the timeout, calling the handler
        timer_in.cancel();
      } else if(!inbound & has_timeout_out) {
        dbm("END: timeout out", function, DBM_START);
        //Timeout debugging integer
        timer_inbound=2;
        //Tells the program this timeout has been cancelled
        has_timeout_out=false;
        //Cancels the timeout, calling the handler
        timer_out.cancel();
      } else {
        //Warning for good health.
        //dbm("WARNING: Timeout cancel called but no timeout apparent",DBM_WARNING);
      }
    }
  }

  /**

   \details Sets an integer to represent the current TCP operation for error reporting.
   @param op A constant describing the current operation, from TCPIP.
   \note In the multiple thread implementation, this doesn't make too much sense since current_op is not thread local.
   */
  void tcpip_session::set_current_op(int op) {
    current_operation=op;
  }

  /**

   \details Gets the message value of a given error reported integer.
   @return A string message telling the most recent operation flagged, usually the one that killed the current action.
   \note In the multiple thread implementation, this doesn't make too much sense since current_op is not thread local.

   */
  std::string tcpip_session::get_current_op() {
    std::string function("TCPIP::tcpip_session::get_current_op");
    std::map<int,std::string> TCP_ERROR_CODES;

    TCP_ERROR_CODES[TCP_CONNECT]=TCP_OP_CONNECT;
    TCP_ERROR_CODES[TCP_READ]=TCP_OP_READ;
    TCP_ERROR_CODES[TCP_WRITE]=TCP_OP_WRITE;
    TCP_ERROR_CODES[TCP_FINAL_WRITE]=TCP_OP_FINAL_WRITE;

    std::map<int,std::string>::iterator it;

    it=TCP_ERROR_CODES.begin();
    it=TCP_ERROR_CODES.find(current_operation);
    dbm(("VAR: tcpip_session::get_current_op "+it->second), function, DBM_VAR);
    return it->second;
  }

  /**

   \details Determines whether the current operation is considered inbound or outbound. Used only for error reporting.
   \note In the multiple thread implementation, this doesn't make too much sense since current_op is not thread local.

   */
  bool tcpip_session::is_inbound() {
    return (current_operation!=TCP_WRITE);
  }

  /**

   \details Sends requests from the outbox to the peer so long as the outbox is not empty. This call returns immediately. When the write request has finished, it calls handle_write().

   */
	void tcpip_session::do_send()
  {
    std::string function("TCPIP::tcpip_session::do_send");
    //Check to see if there is anything in the outbox
    if(!outbox->empty() && is_open()) {
      std::string request; //String used to hold the outbound message

      dbm("START: tcpip_session::do_send", function, DBM_START);
      set_current_op(TCP_WRITE);
      in_progress=true; //Tell the program that a write is in progress, so it won't start another one.

      //Get the next message off of the outbox.
      request=outbox->front();
      dbm(("VAR: request: "+request), function, DBM_VAR);
      dbm(("VAR: outbox front: "+outbox->front()), function, DBM_VAR);
      outbox->pop_front();
      dbm(("VAR: request: "+request),DBM_VAR);

      //Get the length of the message to be sent.
      int request_length = std::strlen(request.c_str());
      char header[HEADER_LENGTH+1]="";
      std::sprintf(header,"%04d",request_length);
      std::string header_str = std::string(header);
      request = header_str  + request;
      size_t message_length = request_length+HEADER_LENGTH;
//      size_t message_length = request_length;

      //Asynchronously send the message, and prepare to call handle_write
      boost::asio::async_write(sock,boost::asio::buffer(request.c_str(),message_length),
                               boost::bind(&tcpip_session::handle_write, this,
                                           boost::asio::placeholders::error));
      //Start an outbound timeout deadline timer.
      do_timeout(false);
      dbm(("VAR: request: "+request), function, DBM_VAR);
    } else {
      //Information for good health, and tell the program that we are no longer writing.
      dbm("INFO: Outbox is Empty", function, DBM_INFO);
      in_progress=false;
      if(is_triggered()) {
        confirm();
        do_close();
      }
    }
  }

  /**

   \details Sends a single string using the asynchronous write command. If it is successful, the handle will return and do nothing. The asynchronous action is handled by handle_end() This is best used for ending communications and control strings. It will timeout.
   @param request A string message
   
   */
  void tcpip_session::do_single_send(std::string request)
  {
    std::string function("TCPIP::tcpip_session::do_single_send");
    dbm("START: tcpip_session::do_single_send", function, DBM_START);
    set_current_op(TCP_FINAL_WRITE);
    
    //Get the length of the message to be sent.
    int request_length = std::strlen(request.c_str());
    char header[HEADER_LENGTH+1]="";
    std::sprintf(header,"%04d",request_length);
    std::string header_str = std::string(header);
    request = header_str  + request;
    size_t message_length = request_length+HEADER_LENGTH;
    
    //Start the asynchronous write command
    boost::asio::async_write(sock,boost::asio::buffer(request.c_str(),message_length),
                             boost::bind(&tcpip_session::handle_end, this,
                                         boost::asio::placeholders::error));
    //Start an outbound timeout.
    do_timeout(false);
    dbm(("VAR: single request: "+request), function, DBM_VAR);
    
  }
  
  /**
  \details Sends a single string using the asynchronous write command. If it is 
   successful, the handle will return and do nothing. The asynchronous action is 
   handled by handle_end() This is best used for ending communications and 
   control strings. It will timeout.  It sends only the request string, without
   any headers...meant for writing to servers outside ROBO.
    @param request A string message    
    */
    void tcpip_session::do_simple_send(std::string request)
  {
    std::string function("TCPIP::tcpip_session::do_simple_send");
    dbm("START: tcpip_session::do_simple_send", function, DBM_START);
    set_current_op(TCP_FINAL_WRITE);
    
    //Get the length of the message to be sent.
    int request_length = std::strlen(request.c_str());
    //char header[HEADER_LENGTH+1]="";
    //std::sprintf(header,"%04d",request_length);
    //std::string header_str = std::string(header);
    //request = header_str  + request;
    //size_t message_length = request_length+HEADER_LENGTH;
    
    //Start the asynchronous write command
    boost::asio::async_write(sock,boost::asio::buffer(request.c_str(),request_length),
                             boost::bind(&tcpip_session::handle_end, this,
                                         boost::asio::placeholders::error));
    //Start an outbound timeout.
    do_timeout(false);
    dbm(("VAR: single request: "+request), function, DBM_VAR);
    
  }
    
  /**

   \details Starts an asynchronous recieve loop which reads messages from the peer and then handles them using handle_read(). Should only be called within the io_service thread.
   \note Handlers are designed to be used with asynchronous operations ONLY.


   */
  void tcpip_session::do_recieve()
  {
    std::string function("TCPIP::tcpip_session::do_recieve");
    dbm("START: tcpip_session::do_recieve", function, DBM_START);
    set_current_op(TCP_READ);

//    memset(header_,0,HEADER_LENGTH-1);
    memset(header_,'\0',HEADER_LENGTH+1);
//    memset(reply_,0,MAX_LENGTH-1);
    memset(reply_,0,MAX_LENGTH);
//    std::cout << "    do_receive: " << header_ << "|" << std::atoi(header_) << "|" << reply_<< std::endl;
    async_read(sock,boost::asio::buffer(header_,HEADER_LENGTH),
               boost::bind(&tcpip_session::handle_read_header,this,
                           boost::asio::placeholders::error,
                           boost::asio::placeholders::bytes_transferred));
    do_timeout(true);
  }

  /**

   \details Handles timeouts from do_timeout(). If the timeout happened because a timer expired, then it will call do_die() and kill the connection. If not, it will take no action.
   \note Handlers are designed to be used with asynchronous operations ONLY.


   */
  void tcpip_session::handle_timeout(const boost::system::error_code& error) {
    std::string function("TCPIP::tcpip_session::handle_timeout");
    //Debugging messages
    if(timer_inbound==1) {
      dbm("HANDLE: timeout in", function, DBM_HANDLE);
    } else if (timer_inbound==2) {
      dbm("HANDLE: timeout out", function, DBM_HANDLE);
    } else {
      dbm("HANDLE: TIMEOUT", function);
    }

    //Only act if the error is not because the timer was canceled
    if(error && error != boost::asio::error::operation_aborted) {
      //Ensure that the timeout was running on the correct object.
      if((has_timeout_in) || (has_timeout_out)) {
        dbm("WARNING: TIMEOUT", function, DBM_WARNING);
      }
      //Kill the socket.
      do_die(error);
    } else {
      //dbm("INFO: Timeout handled with no error",DBM_INFO);
    }
  }

  /**

   \details Handles write actions from do_send(). Cancels the timeout acting on outbound actions, then, if there was no error, starts another send action. If there was an error, kill the session.
   \note Handlers are designed to be used with asynchronous operations ONLY.

   */
  void tcpip_session::handle_write(const boost::system::error_code& error)
  {
    std::string function("TCPIP::tcpip_session::handle_write");
    dbm("HANDLE: write", function, DBM_HANDLE);
    stop_timeout(false);
    if(!error)  {
      do_send();
    }else{
      dbm("WARNING: write error", function, DBM_WARNING);
      do_die(error);
    }

  }

  void tcpip_session::handle_read_header(const boost::system::error_code& error, size_t bytes_transferred) {
    std::string function("TCPIP::tcpip_session::handle_read_header");
    dbm("HANDLE: read header", function, DBM_HANDLE);
    stop_timeout(true);
    dbm("VAR Bytes:"+bytes_transferred, function, DBM_HANDLE);
    if(!error) {
      reply_length = std::atoi(header_);
      dbm(header_,DBM_INFO);
      async_read(sock,boost::asio::buffer(reply_,reply_length),
                 boost::bind(&tcpip_session::handle_read,this,
                             boost::asio::placeholders::error,
                             boost::asio::placeholders::bytes_transferred));
      do_timeout(true);
    } else {
      dbm("WARNING: handle header error", function, DBM_WARNING);
      do_die(error);
    }
  }

  /**

   \details Handles read actions from do_recieve(). Cancels the outbound timeout. If there was no reply, it reads the reply using the read() command. If the read command flags exit, it will cause the session to quit using do_quit(), otherwise it calls back to receive. IF there was an error, and the session was told to quit, the method catches the error, if not, it kills the session using do_die().
   \note Handlers are designed to be used with asynchronous operations ONLY.
   The do_quit() action called here may not be the primary quit mechanism, but it is safe to multiple calls and will not throw errors.

   */
  void tcpip_session::handle_read(const boost::system::error_code& error, size_t bytes_transferred)
  {
    std::string function("TCPIP::tcpip_session::handle_read");
    dbm("HANDLE: read", function, DBM_HANDLE);
    //Cancel the inbound timeout
    stop_timeout(true);
    //If there is no error, do normal stuff
    if(!error) {
      //Convert the inbound to a string.
      //std::cout << "reply_: " << reply_ << "END" << std::endl;
			dbm(std::string(reply_), function, DBM_INFO);      
      std::string reply = std::string(reply_,reply_length);
      //std::cout << "reply: " << reply << "END" << std::endl;

      dbm(("VAR: std::session::handle_read::reply "+reply), function, DBM_VAR);
      //Read the string into the inbox using the handler to check for commands.
      read(reply);

      //Check to see if a flag told us to exit, if so, quit.
      if(is_confirmed() && !is_triggered()) {
        do_exit();
        do_close();
      } else if(is_triggered()) {
        quit(); //We can call do_quit here b/c we are already in the io_service land...
      } else{
        //If the flag did not say exit, start to read another message.
        do_recieve();
      }
    } else {
      dbm("READ ERROR: "+error.message(), function, DBM_ERROR);
      //If we got a read error, but we are ready to exit, then ignore it.
      if(is_exit() || is_shutdown()) {
        dbm("INFO: read error but exit switched",DBM_INFO);
        //do_quit();
      } else {
        //If we weren't ready to exit but had an error, kill the session.
        dbm("WARNING: read error", function, DBM_WARNING);
        do_die(error);
      }
    }
    dbm("END: handle read", function, DBM_END);
  }

  /**

   \details Handles the do_single_send() write action. Cancels the timeout. If there is an error it kills the session. If not, it returns and does nothing else.
   \note Handlers are designed to be used with asynchronous operations ONLY.

   */
  void tcpip_session::handle_end(const boost::system::error_code& error)
  {
    std::string function("TCPIP::tcpip_session::handle_end");
    dbm("HANDLE: single", function, DBM_HANDLE);
    //Cancel the timer.
    stop_timeout(false);
    //Tell the system there is no longer a write in progress.

    in_progress=false;

    if(error) {
      dbm("WARNING: write (single) error", function, DBM_WARNING);
      //Die if we had an error.
      do_die(error);
    }
  }

  /**

   \details Closes the socket, trying to shutdown if possible. Also cancels any open timeouts. Should not throw errors. To see errors caused during closing, enable DBM_ERROR and VERBOSE. The object is good about usually trying this to make sure that everything is ready to close and leave.

   */
  void tcpip_session::do_close() {
    std::string function("TCPIP::tcpip_session::do_close");
    dbm("BEGIN tcpip_session::do_close", function, DBM_BEGIN);
    //Cancel open timeouts.
    stop_timeout(true);
    stop_timeout(false);
    //Only shutdown if the socket still appears to be open.
    if(sock.is_open()){
      boost::system::error_code ec;
      //Shutdown both read and write commands
      sock.shutdown(boost::asio::ip::tcp::socket::shutdown_both, ec);
      //Catch errors
      if(ec) {
        dbm("ERROR SHUTDOWN: "+ec.message(), function, DBM_ERROR);
      }
      //Close the socket (usually in case shutdown failed)
      sock.close(ec);
      //Catch errors
      if(ec) {
        dbm("ERROR CLOSE: "+ec.message(), function, DBM_ERROR);
      }
    } else {
      dbm("WARNING: on do_close, socket is already closed", function, DBM_WARNING);
    }
    reply="Hi";
  }

  /**

   \details Kills the current session, often violently. Prints the fed error message to standard output for diagnostics, but tries to die with the same system error code always and a descriptive message instead. After this method has completed, the session should be done.
   \throws Boost system error which tries to describe the last action taken, but which indicates that the session has ended. If a new session or server is needed, a new object must be created from scratch.

   */
  void tcpip_session::do_die(const boost::system::error_code& error) {
    std::string function("TCPIP::tcpip_session::do_die");
    if(is_exit() || is_shutdown()) {

    } else {
      dbm("BEGIN tcpip_session::do_die", function, DBM_BEGIN);
      std::string error_message;
      error_message="Died while "+get_current_op();
      if((is_inbound() && has_timeout_in) || (!is_inbound() && has_timeout_out)) {
        error_message += " TIMEOUT";
      }
      dbm("ERROR: "+error.message(), function, DBM_ERROR);
      do_close();
      dbm("WARNING: THROWING from do_die!", function);
			//throw(boost::system::system_error(boost::system::error_code(),error_message));
    }
  }

} /*TCPIP*//**
            \file tcpip_control.cpp
            \brief Implements the TCPIP::tcpip_control class to control tcpip_sessions
            \date 2010-06-14

            \details Implementation relies on the session concept to control sessions from the main objects (TCPIP::tcpip_server and TCPIP::tcpip_client).

            Copyright (c) 2010 California Institute of Technology
            \author Alexander Rudy
            \note

            <b>Version History:</b>

            */

//REMOVED include "tcpip_control.h"
//REMOVED include "tcpip_globals.h"

/** \namespace TCPIP */
namespace TCPIP {

  /**

   \details Constructor (generic)

   */
	tcpip_control::tcpip_control()
  {
		this->session_active = false;
  }

  /**

   \details Destructor (generic)

   */
	tcpip_control::~tcpip_control() {}

  /**

   \details Takes an inbound string and adds it to the controller message stack. The controller message stack is a double-ended queue implemented as a default way for the controller to manage inbound and outbound messages for a simple processing controller, i.e. a controller that takes an inbound string, does some simple manipulation, and sends it back out. This command should be re-implemented in derived classes and be specific to the processing of inbound functions. The reimplementation of this command has no requirements, nor is this necessary for the correct functioning of the controller, as it is not called internally.
   \attention This function should be overloaded by the end user.

   */
  void tcpip_control::process_inbound_command(std::string command) {
    messages.push_back(command);
  }

  /**

   \details Examines the session inbox to determine whether there is a command available for processing. See set_session() for details on the attached session.
   @return true if the inbox has a command.
   \note This method is safe to re-formatting the inbox as a thread-protected queue.

   */
  bool tcpip_control::has_inbound_command() {
    return !session->get_inbox()->empty();
  }

  /**

   \details Gets the top command off of the set inbox. See set_session() for details on the attached session.
   @return A string with the top inbox command
   \attention The inbox must have a command.

   */
  std::string tcpip_control::get_inbound_command() {
    std::string command=session->get_inbox()->front();
    session->get_inbox()->pop_front();
    return command;
  }

  /**

   \details Processes the outbound command for sending. In the default state, it just tells the attached session to send the given command. It may be overwritten to handle command pre-processing, especially for control sequences which may not send a command in the end, but need interpretation. See set_session() for details on the attached session.
   @param command The command string to be processed and possibly sent.

   \note Reimplementation should call session->send(command) from tcpip_session::send() to actually send the command.
   */
  void tcpip_control::process_outbound_command(std::string command) {
    session->send(command);
  }

  /**

   \details Gets the next outbound command to be sent. This gets the command from the default message stack. It may be overwritten to get commands from things like user input or a better message stack, or it can be ignored.

   @return A string message which is the next outbound message to be processed.

   */
  std::string tcpip_control::get_outbound_command() {
    std::string command = messages.front();
    messages.pop_front();
    return command;
  }

  /**

   \details Determines if the controller has another outbound command. Checks the default message stack to see if there are any messages.
   @return True if there are messages to be processed.

   \note Can be reimplemented for loop outbound information.

   */
  bool tcpip_control::has_outbound_command() {
    return !messages.empty();
  }

  /**

   \details Calls the attached session exit command, see tcpip_handler::exit(). To change the attached session, see set_session().

   */
  void tcpip_control::exit() {
    session->exit();
  }

  /**

   \details Calls the attached session shutdown command, see tcpip_handler::shutdown(). To change the attached session, see set_session().
   */
  void tcpip_control::shutdown() {
    session->shutdown();
  }

  /**

   \details Calls the attached session reset command, see tcpip_handler::reset(). To change the attached session, see set_session().
   */
  void tcpip_control::reset() {
    session->reset();
  }

  /**

   \details Calls the attached session trigger command, see tcpip_handler::trigger(). To change the attached session, see set_session().

   */

  void tcpip_control::trigger() {
    session->trigger();
  }

  /**

   \details Sets the attached session to the given handler. The attached session is the session used for flags, inbox, outbox and send commands.
   @param handler A reference to a tcpip_handler object.

   */
  void tcpip_control::set_session(tcpip_handler &handler) {
    session = &handler;
  }

  /**

   \details Returns a pointer to the attached session for use elsewhere.
   @return A pointer to a tcpip_handler object.

   */
  tcpip_handler* tcpip_control::get_session() {
    return session;
  }

} /*TCPIP*/
/**
 \file tcpip_client.cpp
 \brief Implements the tcpip_client class and client_session class
 \date 2010-06-15

 \details Implementation manages client specifics as well as

 Copyright (c) 2010 California Institute of Technology
 \author Alexander Rudy
 \note

 <b>Version History:</b>

 */


//REMOVED include "tcpip_client.h"
//REMOVED include "tcpip_globals.h"

/** \namespace TCPIP */
namespace TCPIP {

  /**

   \details Constructs a client session object which connects to the given address and port. The client object sets the timeout to the default TCPIP::CLIENT_TIMEOUT and starts the connection automatically. The client also starts listening automatically, so there is no need to place a call to tcpip_session::listen(). If it fails, the system will try to reconnect for MAX_CONNECTION_ATTEMPTS.

   @param io_service_in A reference to the client io_service
   @param address The address to connect.
   @param port The port number for the connection

   \throws Boost system error which tries to describe the last action taken, but which indicates that the session has ended. If a new session or server is needed, a new object must be created from scratch.

   */
  client_session::client_session(boost::asio::io_service& io_service_in, char* address, char* port)
  : tcpip_session(io_service_in),
  io_service_client(io_service_in),
  query(boost::asio::ip::tcp::v4(), address, port),
  resolver(io_service_in)
  {
    std::string function("TCPIP::client_session::client_session");
    set_timeout(boost::posix_time::seconds(CLIENT_TIMEOUT));
    connect_count=0;
    do_connect();
    dbm("CONST: client_session", function, DBM_CONST);
  }

  /**

   \details Starts an asynchronous connect operation which relies on the tcp resolver and query items to find a tcp endpoint. Also starts a timeout operation. Calls handle_connect() to handle the result of the asynchronous connection.

   */
  void client_session::do_connect() {
    std::string function("TCPIP::client_session::do_connect");
    dbm("START: client_session::do_connect", function, DBM_START);
    set_current_op(TCP_CONNECT);

    boost::asio::ip::tcp::resolver::iterator iterator = resolver.resolve(query);
    boost::asio::ip::tcp::endpoint endpoint = *iterator;

    dbm("START: async connect", function, DBM_START);
    sock.async_connect(endpoint,boost::bind(&client_session::handle_connect,
                                            this,boost::asio::placeholders::error,++iterator));
    do_timeout(false);
  }


  /**

   \details Handles connect actions from the asynchronous connector. Cancels the timeout operation, and if no error was encountered, starts a receive loop. If an error was encountered, closes the socket and ends the client. If no error was connected, but the ending address cannot be found, it attempts to re-resolve connection for MAX_CONNECTION_ATTEMPTS.

   \throws Boost system error which tries to describe the last action taken, but which indicates that the session has ended. If a new session or server is needed, a new object must be created from scratch.

   */
  void client_session::handle_connect(const boost::system::error_code& error, boost::asio::ip::tcp::resolver::iterator iterator) {
    std::string function("TCPIP::client_session::handle_connect");
    dbm("HANDLE: connect", function, DBM_HANDLE);
    stop_timeout(false);
    if(!error) {
      do_recieve();
    }else if(iterator !=boost::asio::ip::tcp::resolver::iterator() ) {
      sock.close();
      connect_count++;
      if(connect_count<MAX_CONNECT_ATTEMPTS) {
        do_connect();
      } else {
        dbm("Exceeded Maximum Connection Attempts", function);
      }
    } else {
      dbm("WARNING: Error on Connect", function, DBM_WARNING);
      do_die(error);
    }
  }

  /**

   \details Creates a tcpip_client object which establishes a session connection to the given address and port. Automatically constructs the session, as well as registering the session, so there is no need to call set_session. The tcpip_client object constructs its own io_service at this point.

   */
	tcpip_client::tcpip_client(char* addr, char* prt)
	: address(addr), port(prt),io_service(),
	c(io_service,address,port)
  {
    std::string function("TCPIP::tcpip_client::tcpip_client");
    dbm("CONST: client", function, DBM_CONST);
    session = &c;
  }

  /**

   \details Destroys the client object, and stops the read thread as well as the output thread. See tcpip_client::stop()

   */
  tcpip_client::~tcpip_client() {
    stop();
  }

  /**

   \details Starts the io_service thread (tcpip_client::readthread) as well as the output thread (tcpip_client::outputthread). This allows the main thread to ask the user for input, while confining the client activities to the readthread, and the interpretation of inbound commands to the outputthread. The basic implementation just uses the outputthread to print the inbound commands out to the command line.

   */
  void tcpip_client::run() {
    readthread = new boost::thread(boost::bind(&boost::asio::io_service::run, 
                                         &io_service));
  }

  /**

   \details Stops all of the thread actions. This works by first asking the client_session to quit. Since quit returns immediately, there is a crude wait function which allows the io_service thread to finish before stopping the io_service, and then joining the outputthread and readthread to the main thread.

   */
  void tcpip_client::stop() {
    std::string function("TCPIP::tcpip_client::stop");
    //Tell the session to quit, because if we got to this point, the session isn't open any more and we are done.
    if(session->is_open()) {
      session->quit();
     while(session->is_open()) {
        sleep(1);
        dbm("INFO: Client waiting for Quit", function, DBM_INFO);
      }
      io_service.stop();
      dbm("INFO: Joining io_service", function, DBM_INFO);
      readthread->join();
      delete readthread;
      dbm("INFO: Joined io_servie", function, DBM_INFO);
    }
  }


  /**

   \details Creates a brand new session, and restarts the io_service.

  */
  void tcpip_client::reconnect() {
  	stop();
  	io_service.reset();
    // MEMORY FIX
    if (this->session_active == true){
      delete session;
    }
  	session = new client_session(io_service,address,port);
		this->session_active = true;
  	run();
  }


  /**

   \details Ask if the client still has a command to send out. This is done in the default client class by asking the session if it is still operating. If the session is no longer operating, then we don't really want the user to try to give it commands.

   \code
   return !session->is_exit();
   \endcode

   */
  bool tcpip_client::has_outbound_command() {
    std::string function("TCPIP::tcpip_client::has_outbound_command");
    dbm("INFO: Asking about outbound commands", function, DBM_INFO);
    return !session->is_exit();
  }


  /**

   \details The basic process prints the inbound command to cout. Derived classes should re-write the process_inbound_command function to take the appropriate action with each inbound command. Because the inbound commands are held in a queue, this process can take as long or short as necessary without loss of data.


   */
  void tcpip_client::process_inbound_command(std::string command) {
//    std::cout<< "command: " << command << std::endl;
    std::cout<< command << std::endl;
  }

  /**

   \details Get an outbound command to send. This gets the command from the user using cin. There is nothing fancy in the implementation except that it returns the command to be sent to the server.
   @return A string command

   */
  std::string tcpip_client::get_outbound_command() {
    std::string function("TCPIP::tcpip_client::has_outbound_command");
    dbm("INFO: Ready to read in line", function, DBM_INFO);
    return cin_read_message();
  }

  /**

   \details A simple method to take a line in from the user. The command length is set by TCPIP::MAX_LENGTH

   @return A string of user input.

   */
  std::string tcpip_client::cin_read_message() {
    char input_[INPUT_LENGTH];
    std::cin.getline(input_, INPUT_LENGTH);
    std::string tempstring = std::string(input_);
    return tempstring;
  }

  /**

   \details Handles outbound commands from the user. It uses a local map form init_map() to map command strings to switch values. Then it switches through the commands, and sends the appropriate flags if a command is found. If not command is found, it calls on the attached session to send the message.

   @param post_message The message to be processed

   \note Instead of overwriting the control command processor here, it is possible just to write another method to pass command strings to this method.

   */
  void tcpip_client::process_outbound_command(std::string post_message) {
    
//    std::cout << "  outbound message: " << post_message << std::endl;
    init_map();
    int post_switch=get_switch(post_message,postmap);

    switch (post_switch)
    {
      case CV_EXIT:
        exit();
        break;
      case CV_SHUTDOWN:
        shutdown();
        break;
      default:
        session->send(post_message);
    }
  }

  /**

   \details Initialize command map for outbound client command words.

   */
  void tcpip_client::init_map() {
    std::string function("TCPIP::tcpip_client::init_map");
    dbm("INFO: Client init_map", function, DBM_INFO);
    postmap[EXIT_COMMAND]=CV_EXIT;
    postmap[SHUTDOWN_COMMAND]=CV_SHUTDOWN;
  }

} // END TCPIP NAMESPACE
/**
 \file tcpip_server.cpp
 \brief Implementation of Server concepts
 \date 2010-06-14

 \details Implementation of a multiple connection server

 Copyright (c) 2010 California Institute of Technology
 \author Alexander Rudy
 \note

 <b>Version History:</b>

 */

#include <cstdlib>
#include <iostream>
#include <set>
#include <deque>
#include <list>
#include <algorithm>
#include <boost/bind.hpp>
#include <boost/asio.hpp>
#include <boost/shared_ptr.hpp>
#include <boost/enable_shared_from_this.hpp>
#include <boost/thread.hpp>

//REMOVED include "tcpip_server.h"

/** \namespace TCPIP */
namespace TCPIP
{

	using boost::asio::ip::tcp;

	/**

   \details Constructs a broadcast room object and resets all the internal handler flags.

   */
  broadcast_room::broadcast_room() {
    std::string function("TCPIP::broadcast_room::broadcast_room");
    dbm("CONST: Constructed Broadcast Room",DBM_CONST);
    reset();
  }

	/**

   \details Adds a session to the list of managed sessions. The added session must be open, as the broadcast room assumes all managed sessions are open.
   @param session a shared pointer to the managed session, usually from shared_from_this().

   */
  void broadcast_room::join(session_ptr session) {
    std::string function("TCPIP::broadcast_room::join");
    dbm("BEGIN: Join", function, DBM_BEGIN);
    sessions.insert(session);
  }

	/**

   \details Sends a message through all sessions managed by this broadcast room, using each session's tcpip_session::send() command. If there are no managed sessions, will return without taking any action.
   @param dmessage The string message to be sent.
   \throws Boost system error which tries to describe the last action taken, but which indicates that the session has ended. If a new session or server is needed, a new object must be created from scratch.


   */
  void broadcast_room::send(std::string dmessage){
    std::string function("TCPIP::broadcast_room::send");
    dbm("BEGIN: Broadcast: Send", function, DBM_BEGIN);
    if(sessions.empty()) {
      dbm("WARNING: No sessions in room", function, DBM_WARNING);
    } else {
      std::for_each(sessions.begin(),sessions.end(),boost::bind(&tcpip_session::send,_1,dmessage));
    }
  }


  /**

   \details Sends a single message through all sessions managed by this broadcast room, using each session's tcpip_session::single_send() command. If there are no managed sessions, will return without taking any action.
   @param dmessage The string message to be sent.
   \throws Boost system error which tries to describe the last action taken, but which indicates that the session has ended. If a new session or server is needed, a new object must be created from scratch.

   */
  void broadcast_room::simple_send(std::string dmessage){
    std::string function("TCPIP::broadcast_room::simple_send");
    dbm("BEGIN: Broadcast: Simple Send", function, DBM_BEGIN);
    if(sessions.empty()) {
      dbm("WARNING: No sessions in room", function, DBM_WARNING);
    } else {
      std::for_each(sessions.begin(),sessions.end(),boost::bind(&tcpip_session::simple_send,_1,dmessage));
    }
  }

  /**

   \details Sends a single message through all sessions managed by this broadcast room, using each session's tcpip_session::single_send() command. If there are no managed sessions, will return without taking any action.
   @param dmessage The string message to be sent.
   \throws Boost system error which tries to describe the last action taken, but which indicates that the session has ended. If a new session or server is needed, a new object must be created from scratch.

   */
  void broadcast_room::single_send(std::string dmessage){
    std::string function("TCPIP::broadcast_room::single_send");
    dbm("BEGIN: Broadcast: Single Send", function, DBM_BEGIN);
    if(sessions.empty()) {
      dbm("WARNING: No sessions in room", function, DBM_WARNING);
    } else {
      std::for_each(sessions.begin(),sessions.end(),boost::bind(&tcpip_session::single_send,_1,dmessage));
    }
  }

	/**

   \details Tells all sessions managed by this broadcast room to listen for inbound communication, using each session's tcpip_session::listen() command. If there are no managed sessions, will return without taking any action.

   \throws Boost system error which tries to describe the last action taken, but which indicates that the session has ended. If a new session or server is needed, a new object must be created from scratch.


   */
  void broadcast_room::listen(){
    std::string function("TCPIP::broadcast_room::listen");
    dbm("BEGIN: Broadcast: Listen", function, DBM_BEGIN);
    if(sessions.empty()) {
      dbm("WARNING: No sessions in room", function, DBM_WARNING);
    } else {
      std::for_each(sessions.begin(),sessions.end(),boost::bind(&tcpip_session::listen,_1));
    }
  }


  /**

   \details Removes a session from the list of managed sessions.
   @param session a shared pointer to the managed session, usually from shared_from_this().

   */
  void broadcast_room::leave(session_ptr session) {
    std::string function("TCPIP::broadcast_room::leave");
    sessions.erase(session);
    dbm("BEGIN: Leave", function, DBM_BEGIN);
  }

  /**

   \details Uses the shutdown flag to see if there are supposed to be any open sessions.
   @return True if there are allowed to be open sessions. Does not ensure that there actually exist any open sessions.

   */
  bool broadcast_room::is_open() {
    return !(sessions.empty() && is_shutdown());
  }

  /**

   \details Tells all sessions managed by this broadcast room to quit, using each session's tcpip_session::quit() command. If there are no managed sessions, will return without taking any action.
   \throws Boost system error which tries to describe the last action taken, but which indicates that the session has ended. If a new session or server is needed, a new object must be created from scratch.

   */
  void broadcast_room::quit() {
    std::string function("TCPIP::broadcast_room::quit");
    dbm("BEGIN: quit", function, DBM_BEGIN);
    if(sessions.empty()) {
      dbm("WARNING: No sessions in room", function, DBM_WARNING);
    } else {
      std::for_each(sessions.begin(),sessions.end(),boost::bind(&tcpip_session::quit,_1));
    }
  }

  /**
  *
  * @details Uses the set of open connections to determine the number of current connections.
  *
  */

  int broadcast_room::connection_count() {
  	return sessions.size();
  }

  /**

   \details Constructs a server session. Does NOT start the server sessions asynchronous actions. Sets the general switch to refer to the broadcast room so that shutdown is controlled by the room, and sets the local switch to be controlled by this session, so that exit commands only affect this session. Sets both the inbox and outbox to be in the broadcast room instead of in this session, so that messages can be read and written from the broadcast room. Also sets a default timeout value.

   @param io_service_in A reference to the server's single io_serice.
   @param room_ A reference to the server's broadcast room

   */
  server_session::server_session(boost::asio::io_service& io_service_in, broadcast_room& room_)
  : tcpip_session(io_service_in),
  io_service_server(io_service_in),
  room(room_)
  {
    switch_general = &room;
    switch_local = this;
    set_inbox(room.get_inbox());
    std::string function("TCPIP::server_session::server_session");
    dbm("CONST: session", function, DBM_CONST);
    set_timeout(boost::posix_time::seconds(SERVER_TIMEOUT));
    setStartMessage(WELCOME_MESSAGE);
  }


  server_session::~server_session() {
  }
  /**

   \details Returns the socket for this server_session.
   @return A socket

   */
  tcp::socket& server_session::socket()
  {
    return sock;
  }

  /**

   \details Starts the server sessions receive loop, first sending the welcome message to the client so that the client can check that the connection is working. Since the server passively accepts connections and sends all messages to all connected parties, it is not necessary to receive a confirmation message back. It also adds the session to the broadcast room's management. It should only be called by open sessions.

   \note This is a public method which is thread-safe for calls outside the main io_service thread. It may only be called once per session.

   */
  void server_session::start()
  {
    std::string function("TCPIP::server_session::start");
    dbm("BEGIN: server_session:start", function, DBM_BEGIN);
		//Since this is presumably an open session, we can add it to the broadcast room's management list.
    sesptr=shared_from_this();
    room.join(sesptr);
		//Send the client the welcome message so that they know they have connected
    send(mess_start);
		//Listen for inbound messages.
    listen();
    dbm("END: server_session:start", function, DBM_END);
  }


	/**

   \details Set the welcome message that the server sends to new client connections.
   @param input The welcome message.

   \note By default this is set to TCPIP::WELCOME_MESSAGE

   */
  void server_session::setStartMessage(std::string input) {
    mess_start=input;
  }


	/**

   \details Performs the exit actions specific to the server implementation.. Calls for the session to leave the current room, and if it is set to shutdown, calls for all other sessions attached to the broadcast_room to exit.


   */
  void server_session::do_exit() {
    std::string function("TCPIP::server_session::do_exit");
    dbm("BEGIN: server_session:do_exit", function, DBM_BEGIN);
    exit(); //We call exit because we don't want to ungraciously kill any currently acting asynchronous actions.
    room.leave(sesptr);
    dbm("NOTICE: Ready to start shutdown check", function, DBM_NOTICE);
		//Now we can send the message to each item.
    if(is_shutdown()){
      dbm("INFO: Sending room shutdown", function, DBM_INFO);
      room.send(SHUTDOWN_MESSAGE);
    } else {
      dbm("INFO: Not shutdown command", function, DBM_INFO);
    }
  }


	/**

   \details Constructs a tcpip_server object. Also constructs member objects room and acceptor, as well as a reference to the main io_service object. The constructor automatically starts the server's acceptor, and sets the attached session to be the newly created broadcast_room.

   @param io_service_in A reference to the main io_service
   @param port A short port number for the connection.

   */
  tcpip_server::tcpip_server(boost::asio::io_service& io_service_in, short port)
  : room(),
  io_service_server(io_service_in),
  acceptor_(io_service_in, tcp::endpoint(tcp::v4(), port))
  {
    std::string function("TCPIP::tcpip_server::tcpip_server");
    dbm("CONST: tcpip_server", function, DBM_CONST);
    session = &room;
    start_acceptor();
  }

	/**

   \details Destructs the tcpip_server, and calls stop() to close the acceptor, stop the io_service an rejoin threads.

   */
  tcpip_server::~tcpip_server() {
    stop();
  }

	/**

   \details Run the io_service in a separate thread runthread. Branches this thread from the main thread.

   */
  void tcpip_server::run() {
    std::string function("TCPIP::tcpip_server::run");
    dbm("START: io_service.run", function, DBM_START);
//    runthread = new boost::thread(boost::bind(&boost::asio::io_service::run, 
//                                              &io_service_server));
    this->runthread = boost::thread(boost::bind(&boost::asio::io_service::run, 
                                              &io_service_server));
  }

	/**

   \details Stops the acceptor and joins the io_service thread back onto the main thread. Assumes that the io_service has finished (which when the acceptor closes, if all the sessions have been destroyed, is true.)

   */
  void tcpip_server::stop() {
    std::string function("TCPIP::tcpip_server::stop");
    dbm("STOP: io_service", function, DBM_END);
    acceptor_.close();
//    runthread->join();
//    io_service_server.stop();
    runthread.join();
//    delete runthread;
//    std::cout << "d" << std::endl << std::flush;
    dbm("STOPPED: io_service", function, DBM_END);
  }


  /**

   \details Starts a recursive acceptor which asynchronously waits to receive a connection. It creates a server_session before starting the accept, so that the server session socket can be used to accept the connection. When it receives a connection, it calls handle_accpet(). This function DOES NOT timeout.

   */
  void tcpip_server::start_acceptor(){
    std::string function("TCPIP::tcpip_server::start_acceptor");
    dbm("START: start_acceptor", function, DBM_START);
    server_session_ptr new_session(new server_session(io_service_server,room));
    acceptor_.async_accept(new_session->socket(),boost::bind(&tcpip_server::handle_accept,this, new_session,boost::asio::placeholders::error));
  }

  /**

   \details Handles an attempted accept connection by the server. If the attempt was successful, then we tell the new server session to start, and start another acceptor. If it was unsuccessful, the server just ends, presumably because there was something not good.

   */
	void tcpip_server::handle_accept(server_session_ptr new_session,
                                   const boost::system::error_code& error)
  {
    if (!error)
    {
      std::string function("TCPIP::tcpip_server::handle_accept");
      dbm("BEGIN: Session", function, DBM_BEGIN);
      new_session->start();
      start_acceptor();
    }
    else
    {
    }
  }


} /* TCPIP */

/**
 * @file comm.min.cpp
 * @brief Master Communications Source File
 * @date 2010-07-27
 *
 * @details Implements all of the client and server classes.
 *
 * Copyright (c) 2010 California Institute of Technology
 * @author Alexander Rudy
 * @note This file combines many other header files into one convenient one.
 *
 *
 * <b>Version History:</b>
 *
 */
