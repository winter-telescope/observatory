/**
 \file lgsd.h
 \brief Header file for Laser Guide Star daemon software.
 \details Controls the operation of the LGS facility for ROBO.

 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note

 <b>Version History</b>:
 \verbatim
 \endverbatim
 */

// Use a preprocessor statement to set a variable that checks if the header has
// already loaded...this avoids loading the header file more than once.
# ifndef ROBO_DAEMON_H
# define ROBO_DAEMON_H

# include <iostream>
# include <sys/resource.h>
# include <sys/stat.h>
# include <fcntl.h>
# include <unistd.h>

namespace ROBO {


//! daemonize the currently running programming
//! Note: the calls to strerror are not thread safe, but that should not matter
//! as the application is only just starting up when this function is called
//! \param[in] dir which dir to ch to after becoming a daemon
//! \param[in] stdinfile file to redirect stdin to
//! \param[in] stdoutfile file to redirect stdout from
//! \param[in] stderrfile file to redirect stderr to
void daemonize(const std::string &dir = "/",
               const std::string &stdinfile = "/dev/null",
               const std::string &stdoutfile = "/dev/null",
               const std::string &stderrfile = "/dev/null")
{
  umask(0);
 
  rlimit rl;
  if (getrlimit(RLIMIT_NOFILE, &rl) < 0) 
  {
    //can't get file limit
    throw std::runtime_error(strerror(errno));
  }
 
  pid_t pid;
  if ((pid = fork()) < 0) 
  {
    //Cannot fork!
    throw std::runtime_error(strerror(errno));
  } else if (pid != 0) { //parent
    exit(0);
  }
 
  setsid();
 
  if (!dir.empty() && chdir(dir.c_str()) < 0) 
  {
    // Oops we couldn't chdir to the new directory
    throw std::runtime_error(strerror(errno));
  }
 
  if (rl.rlim_max == RLIM_INFINITY) 
  {
    rl.rlim_max = 1024;
  }
 
  // Close all open file descriptors
  for (unsigned int i = 0; i < rl.rlim_max; i++) 
  {
    close(i);
  }
 
  int fd0 = open(stdinfile.c_str(), O_RDONLY);
  int fd1 = open(stdoutfile.c_str(),
      O_WRONLY|O_CREAT|O_APPEND, S_IRUSR|S_IWUSR);
  int fd2 = open(stderrfile.c_str(),
      O_WRONLY|O_CREAT|O_APPEND, S_IRUSR|S_IWUSR);
 
  if (fd0 != STDIN_FILENO || fd1 != STDOUT_FILENO || fd2 != STDERR_FILENO) 
  {
    //Unexpected file descriptors
    throw std::runtime_error("new standard file descriptors were not opened as expected");
  }
}
















}

# endif
