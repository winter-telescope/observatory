/**
 \file operations.cpp
 \brief Functions for operations of the ROBO software.
 \details These functions are used for the operation of the system, mainly
 utilities for the interaction between processes.  Lock files and other
 status files are controlled here.  Functions to create daemon states and
 manage them.

 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note

 <b>Version History</b>:
 \verbatim
 2009-11-10:  First complete version
 \endverbatim
 */

// Global include files
# include <csignal>
# include <cstdlib>
# include <dirent.h>

// Local include files
# include "common.h"
# include "file_ops.h"
# include "communications.h"

// Local function definitions
int make_file(std::string executable, int type);
//int check_file(std::string executable, int type);
std::string get_filename(std::string executable, int type);
pid_t spawn(const char *file, const char *argv);



int is_process_running(std::string & name, std::vector<int> & pid)
{
  std::string function("is_process_running");
  std::vector<std::string> pids;
  
  DIR *dp;
  struct dirent *dirp;
  if((dp = opendir("/proc")) == NULL) {
    common_info.log.write(function, true, "unable to open /proc to get process IDs!");
    return(ERROR_SYSTEM_DIRECTORY);
  }
  while ((dirp = readdir(dp)) != NULL) {
    std::string check_string(dirp->d_name);
    if(check_string.find_first_not_of("0123456789") == std::string::npos){
      pids.push_back(check_string);
    }
  }
  closedir(dp);
 
  ROBO_file file;
  int count = 0;
  pid.clear();
  for (unsigned int i = 0; i < pids.size(); i++){
    std::stringstream filename;
    std::string line;     // Temporary string to read file lines into

    filename << "/proc/" << pids[i] << "/comm";
    
    file.open_file_read(filename.str());
    
    getline(file.filestream, line);
        
    file.close_file();
    if (line.compare(name) == 0){
      pid.push_back(atoi(pids[i].c_str()));
      count++;
    }
  }
  
//  if (count != 1 && count != 0){
  if (count != 1){
    return(ERROR);
  }
  
//  if (count == 0){
//  	pid.push_back(BAD_VALUE);
//  }
  
  return(NO_ERROR);
}


int check_process(int argc, char *argv[])
{
  std::string function("check_process");

  // Set the common executable name to the name used to launch this program.
  // This makes sure error messages identify this executable, in case it is
  // compiled with a different name than usual.
	std::vector<std::string> tokens;
	int size = Tokenize(argv[0], tokens, "/");
	if (size == 1){
		common_info.executable_name = argv[0];
	}
	else {
		common_info.executable_name = tokens[size-1];
	}
	

  // Get the process ID of this process
  common_info.pid = getpid();

  srand(time(NULL));

//  float bob = (rand() % 1000 + 1) / 1000.0;
//  std::stringstream mess;
//  mess << "start timeout is " << bob;
//  common_info.log.write(function, true, mess.str());
//  timeout(bob);
//  timeout((rand() % 1000 + 1) / 1000);

  std::vector<int> pid;
  int err = is_process_running(common_info.executable_name, pid);
  if (err == ERROR_SYSTEM_DIRECTORY){
    common_info.using_lock_file = true;
    if (check_lock_file(argc, argv) != NO_ERROR){
      exit(ERROR);
    }
  }
  else if (err == ERROR){
    std::stringstream message;
    message << "program " << common_info.executable_name 
        << " is already running.  Exiting.";
    common_info.log.write(function, true, message.str());
    exit(ERROR);
  }

  common_info.using_lock_file = false;
  return(NO_ERROR);
}


/**************** check_lock_file ****************/
/**
 Checks for presence of a lock file and creates it if one does not exist
 \param [program] Name of the program
 \param [argc] Input parameter count
 \param [argv] Input parameter values
 \exception None.
 \return ERROR: Failure to make lock file
 \return NO_ERROR:	Operation successful
 \note None.
 */
int check_lock_file(int argc, char *argv[])
{
  int i, j;

  // Set the common executable name to the name used to launch this program.
  // This makes sure error messages identify this executable, in case it is
  // compiled with a different name than usual.
  common_info.executable_name = argv[0];

  // Get the process ID of this process
  common_info.pid = getpid();

  // Loop in case of problems checking for the file
  for (i=0; i<15; i++){
  	// Check if the file exists
    if (check_file(common_info.executable_name, LOCK_FILE) == NO_ERROR){
    	// If it does not exist, make it
      make_file(common_info.executable_name, LOCK_FILE);
      return (NO_ERROR);
    }

    // Otherwise, wait 1 second
    else {
      timeout();
      // After 15 seconds, presume lock file already exists and exit
      if (i == 14) {
        // Log the lock file is there, with the launch command
      	ROBO_logfile log;			// Log file class contianer
        // Set the log file name and function
      	log.filename = common_info.log_dir + common_info.executable_name + ".log";
        log.set_function("check_lock_file");
        // Open the log and create the message
//        log.open_file(OPEN_FILE_APPEND);
        log.message << "Lock file present, unable to execute \""
					<< common_info.executable_name;
        for (j=1; j<argc; j++){
        	log.message << " " << argv[j];
        }
      	log.message << "\". Exiting.";
      	// Write the log
        log.write(true);
        // Return an error
        return (ERROR);
      }
    }
  }

  // Never should get here, but it makes the compiler happy
  return (NO_ERROR);
}
/**************** check_lock_file ****************/


/**************** make_file ****************/
/**
 Makes a file for operations
 \param [type] Type of file to make
 \exception None.
 \return ERROR: Failure to make file
 \return NO_ERROR:	Operation successful
 \note None.
 */
int make_file(std::string executable, int type)
{
  ROBO_file file;			// File class container

  // Get the filename
  file.filename = get_filename(executable, type);

	// Set up the log file
  ROBO_logfile log;			// Log file class container
	log.filename = common_info.log_dir + executable + ".log";
  log.set_function("make_file");
//  log.open_file(OPEN_FILE_APPEND);

  // Try to create the file, overwrite what was there
  if (file.open_file(OPEN_FILE_WRITE) == NO_ERROR){
    struct timeval tv;		// System time structure
//    pid_t pid;						// Process ID

    // Get the process ID of this process
//    pid = getpid();
    // Get the current time, which should be the time the process started
    gettimeofday(&tv, NULL);
    // Write this information to the file, so the rest of the system can
    // determine when a process started running
    file.filestream << common_info.pid << " " << tv.tv_sec << std::endl;
    // Log the file creation
    log.message << "process file \"" << file.filename << "\" created with contents \"" << common_info.pid << " "
			<< tv.tv_sec << "\"";
    log.write(false);
    // Return a good message
    return(NO_ERROR);
  }
  // Log that the file could not be created
  else {
    log.message << "Unable to make process file: " << file.filename;
    log.write(true);
    // Return a bad message
    return (ERROR);
  }

  // Never should get here, but it makes the compiler happy
  return(NO_ERROR);
}
/**************** make_file ****************/


/**************** check_file ****************/
/**
 Check if a file exists
 \param [type] Type of file to make
 \exception None.
 \return ERROR: File exists
 \return NO_ERROR:	File does not exist
 \note None.
 */
int check_file(std::string executable, int type)
{
  ROBO_file file;			// File class container

  // Get the filename
  file.filename = get_filename(executable, type);

  // Check if the file can be opened.  If it can, return ERROR.  If not, file
  // does not exist so return NO_ERROR
  if (file.open_file(OPEN_FILE_READ) == NO_ERROR){
    return(ERROR);
  }
  else {
    return(NO_ERROR);
  }

  // Never should get here, but it makes the compiler happy
  return(NO_ERROR);
}
/**************** check_file ****************/


/**************** remove_lock_file ****************/
/**
 Remove a lock file
 \param [executable] Name of the executable to run
 \param [host] The hostname of the computer running the executable
 \excetpion None.
 \return ERROR: Failure to remove file
 \return NO_ERROR:	Operation successful
 \note None.
 */
void remove_lock_file(std::string executable, std::string host)
{
  ROBO_file file;

  file.filename = get_filename(executable, LOCK_FILE);

	// Set up the log file
  ROBO_logfile log;			// Log file class container
	log.filename = common_info.log_dir + common_info.executable_name + ".log";
  log.set_function("remove_lock_file");
//  log.open_file(OPEN_FILE_APPEND);

  // See if the file exists
  if (access(file.filename.c_str(), F_OK) != 0){
    // If the file doesn't exist, log that it doesn't exist and return
//    log.message << "lock file does not exist: " << file.filename << " error: "
//			<< strerror(errno);
//    log.write(true);
    return;
  }

  // Remove the file and log it
  if (remove(file.filename.c_str()) == 0){
    log.message << "removed lock file: " << file.filename;
     log.write(false);
  }
  // Return error message if there is a problem
  else {
    log.message << "unable to remove lock file: " << file.filename << " error: "
			<< strerror(errno);
    log.write(true);
  }
}
/**************** remove_lock_file ****************/


/**************** get_filename ****************/
/**
 Build the filename for the file.
 \param [type] Type of file to make
 \exception None.
 \return Filename as a string
 \note None.
 */
std::string get_filename(std::string executable, int type)
{
  std::stringstream filename("");  // Temporary file name

  // Build the file root, status directory + execurable name
  filename << common_info.status_dir << executable;

// Set the file extension type
  switch (type){
    case LOCK_FILE:
      filename << ".running";
    break;
    case STOP_FILE:
    	filename << ".stop_file";
    break;
    case PAUSE_FILE:
    	filename << ".pause_file";
    break;
    case DAYTIME_FILE:
      filename << ".daytime";
      break;
  }

  // Return the file name
  return (filename.str());
}
/**************** get_filename ****************/


/**************** reset_server ****************/
/**
 Attempt to reset a daemon process that has died.
 \param [executable] Name of the executable to run
 \param [pid] Process ID number
 \param [port] TCP/IP port to open for server
 \param [options] Command options
 \param [host] The hostname of the computer running the executable
 \exception None.
 \note The header file definition for this is in communications.h.
 */
void reset_server(std::string executable, pid_t pid_in, ROBO_port port, 
                  std::string options, std::string host)
{
	// Set up the log file
  ROBO_logfile log;			// Log file class container
	log.filename = common_info.log_dir + common_info.executable_name + ".log";
  std::string function("reset_server");
  std::stringstream log_message;
  
	// Kill daemon processes if they are running
  if (host.compare("localhost") == 0 || host.compare("127.0.0.1") == 0){
    std::vector<int> pid;
    int err = is_process_running(executable, pid);
    if (pid.size() > 0){
      log_message << "process " << executable
                  <<  " found running, killing it";
      log.write(function, true, log_message.str());
      log_message.str("");
      for (unsigned int i = 0; i < pid.size(); i++){
        int ret = kill(pid[i], SIGKILL);
        if (ret != 0){
          log_message << "error killing process " << executable << ", PID "
                      <<  pid[i] << ", error: " << strerror(errno);
          log.write(function, true, log_message.str());
          log_message.str("");
        }
        else {
          log_message << "killed process " << executable << ", PID " <<  pid[i];
          log.write(function, true, log_message.str());
          log_message.str("");
        }
      }
    }
  }
  else {
    log_message << "killing process " << executable << " on host " << host;
    log.write(function, true, log_message.str());
    log_message.str("");
    std::stringstream command;
    command << "ssh " << host << " killall " << executable;
    int ret = system(command.str().c_str());
    if (ret == 0){
      log_message << "command to kill process " << executable << " on host "
                  << host << " was successful";
      log.write(function, false, log_message.str());
    }
    else {
      log_message << "command to kill process " << executable << " on host "
                  << host << " failed";
      log.write(function, true, log_message.str());
    }
    log_message.str("");
  }

  // Remove the lock file if it exists
  if (host.compare("localhost") == 0 || host.compare("127.0.0.1") == 0){
    remove_lock_file(executable);
  }
  
  // Create the command string to relaunch the daemon process
	// Timeout to allow it to die
	timeout(0.1);
//	timeout();

//	std::stringstream temp;			// Temporary stream
//	temp << executable << " -d " << options << " -p " << port << " &";
//	std::string command(temp.str());
  std::stringstream command;
  if (host.compare("localhost") == 0 || host.compare("127.0.0.1") == 0){
    command << executable << " -d " << options << " -p " << port;
  }
  else {
//    command << "ssh " << host << " /home/ztf/Software/bin/" << executable
//            << " -d " << options << " -p " << port;
    command << "ssh " << host << " " << common_info.bin_dir << "/" 
            << executable << " -d " << options << " -p " << port;
  }
//  command << executable << " -d " << options << " -p " << port << " &";

  
	// Relaunch the daemon process
  log_message.str("");
	log_message << "relaunching " << executable << ", command string \""
              << command.str() << "\"";
  log.write(function, false, log_message.str());

  float bob = (rand() % 1000 + 1) / 1000.0;
  timeout(bob);
  
  int ret = system(command.str().c_str());
  log_message.str("");
	if (ret == -1){
    log_message << "error launching command \"" << executable << "\", error: "
        << strerror(errno);
    log.write(function, true, log_message.str());
	}
	else {
    log_message << "successfully launched " << executable;
    log.write(function, false, log_message.str());
	}

//	// Wait 2 seconds to allow the daemon to start up
	timeout(2.1, false);
}
/**************** reset_server ****************/


/**************** kill_server ****************/
/**
 Attempt to kill a daemon process.
 \param [executable] Name of the executable to kill
 \param [pid] Process ID number
 \param [host] The hostname of the computer running the executable
 \exception None.
 \note The header file definition for this is in communications.h.
 */
void kill_server(std::string executable, pid_t pid_in, std::string host)
{
  // Set up the log file
  ROBO_logfile log;			// Log file class container
  log.filename = common_info.log_dir + common_info.executable_name + ".log";
  std::string function("kill_server");
  std::stringstream log_message;
  
  // Kill daemon processes if they are running
  if (host.compare("localhost") == 0 || host.compare("127.0.0.1") == 0){
    std::vector<int> pid;
    int err = is_process_running(executable, pid);
    if (pid.size() > 0){
      log_message << "process " << executable
                  <<  " found running, killing it";
      log.write(function, true, log_message.str());
      log_message.str("");
      for (unsigned int i = 0; i < pid.size(); i++){
        int ret = kill(pid[i], SIGKILL);
        if (ret != 0){
          log_message << "error killing process " << executable << ", PID "
                      <<  pid[i] << ", error: " << strerror(errno);
          log.write(function, true, log_message.str());
          log_message.str("");
        }
        else {
          log_message << "killed process " << executable << ", PID " <<  pid[i];
          log.write(function, true, log_message.str());
          log_message.str("");
        }
      }
    }
  }
  else {
    log_message << "killing process " << executable << " on host " << host;
    log.write(function, true, log_message.str());
    log_message.str("");
    std::stringstream command;
    command << "ssh " << host << " killall " << executable;
    int ret = system(command.str().c_str());
    if (ret == 0){
      log_message << "command to kill process " << executable << " on host "
                  << host << " was successful";
      log.write(function, false, log_message.str());
    }
    else {
      log_message << "command to kill process " << executable << " on host "
                  << host << " failed";
      log.write(function, true, log_message.str());
    }
    log_message.str("");
  }
  
  // Remove the lock file if it exists
  if (host.compare("localhost") == 0 || host.compare("127.0.0.1") == 0){
    remove_lock_file(executable);
  }
  
  // Timeout to allow it to die
  timeout();
}
/**************** kill_server ****************/


