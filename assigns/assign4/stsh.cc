/**
 * File: stsh.cc
j
 * -------------
 * Defines the entry point of the stsh executable.
 */

#include <cassert>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
#include <array>
#include <algorithm>
#include <fcntl.h>
#include <unistd.h>  // for fork
#include <csignal>  // for kill
#include <sys/wait.h>
#include <sys/types.h> // for open
#include <sys/stat.h> // for open
#include "stsh.h"
#include "stsh-parser/stsh-readline.h"
#include "stsh-parser/stsh-parse-exception.h"
#include "stsh-exception.h"
#include "stsh-parse-utils.h"
#include "stsh-job-list.h"
#include "stsh-job.h"
#include "stsh-process.h"
#include "fork-utils.h" // this needs to be the last #include in the list

using namespace std;

/**
 * Configure signal handling behavior for the shell. You can block or defer any
 * signals here.
 */
void STSHShell::configureSignals() {
  signal(SIGQUIT, [](int sig) { exit(0); });
  signal(SIGTTIN, SIG_IGN);
  signal(SIGTTOU, SIG_IGN);
}

/**
 * Define a mapping of commands as typed by the user to the Builtin enum
 * (defined in stsh.h). Any aliases can be defined here (e.g. "quit" and "exit"
 * are the same)
 */
const map<std::string, STSHShell::Builtin> STSHShell::kBuiltinCommands = {
  {"quit", STSHShell::Builtin::QUIT}, {"exit", STSHShell::Builtin::QUIT},
  {"fg", STSHShell::Builtin::FG},
  {"bg", STSHShell::Builtin::BG},
  {"slay", STSHShell::Builtin::SLAY},
  {"halt", STSHShell::Builtin::HALT},
  {"cont", STSHShell::Builtin::CONT},
  {"jobs", STSHShell::Builtin::JOBS},
};

/**
 * Run the REPL loop: take input from the user, execute commands, and repeat
 */
void STSHShell::run(int argc, char *argv[]) {
  constructMonitoredSet({SIGCHLD, SIGINT, SIGTSTP});

  pid_t stshpid = getpid();
  rlinit(argc, argv);
  signal(SIGINT, SIG_IGN);
  signal(SIGTSTP, SIG_IGN);
  while (true) {
    string line;
    if (!readline(line)) break;
    if (line.empty()) continue;
    try {
      pipeline p(line);
      if (kBuiltinCommands.contains(p.commands[0].command)) {
        Builtin command = kBuiltinCommands.at(p.commands[0].command);
        handleBuiltin(command, p.commands[0].tokens);
      } else {
        createJob(p);
      }
    } catch (const STSHException& e) {
      cerr << e.what() << endl;
      if (getpid() != stshpid) exit(0); // if exception is thrown from child process, kill it
    }
  }
}

/**
 * Handle execution of builtin commands (defined in the STSHShell::Builtin enum)
 */
void STSHShell::handleBuiltin(Builtin command, const char *const arguments[]) {
  if (command == Builtin::QUIT) {
    exit(0);
  } else if (command == Builtin::JOBS) {
    waitOnChildProcesses();
    cout << joblist;
  } else if (command == Builtin::FG) {
    handleFg(arguments);
  } else if (command == Builtin::BG) {
    handleBg(arguments);
  } else if (command == Builtin::SLAY) {
    handleSlay(arguments);
  } else if (command == Builtin::HALT) {
    handleHalt(arguments);
  } else if (command == Builtin::CONT) {
    handleCont(arguments);
  }  else {
    throw STSHException("Internal error: builtin not yet implemented");
  }
}

size_t STSHShell::checkforArguments(std::string command, const char *const arguments[]){
  int num;
  //Set the number of expected arguments for bg, slay, halt, cont
  if ((command == "fg") || (command =="bg")) num = 1;
  else num = 2;
  //Check if the number of arguments is correct for the command
  if ((arguments[num] != NULL) || (arguments[0] == NULL)) throw STSHException("Incorrect number of arguments to the command!"); 

  //Use parseNumber to obtain the arguments
  std::vector<size_t> myParsedArgs;
  size_t argsToReturn;
  for(int i=0; i<num; i++){
    if (arguments[i] == NULL) break;
    myParsedArgs.push_back(parseNumber(arguments[i], "Invalid argument type, argument can only be a number or pid!"));
  }

  //Handle and return the jobNumber incase of fg and bg
  if ((command == "fg") || (command =="bg")){
    if (!joblist.containsJob(myParsedArgs[0])) throw STSHException("Invalid job number!");
    //Return the job number to the fg and bg functions
    argsToReturn = myParsedArgs[0];
  }
  else{
    if(myParsedArgs.size()==1){
      //If there is only one argument it will always be the pid and this should be returned to slay, halt and cont
      if(!joblist.containsProcess(myParsedArgs[0])) throw ("Invalid pid!");
      else argsToReturn = myParsedArgs[0];
    }
    else{
      //If there are two arguments it will always be the jobNum and the index 
      if (!joblist.containsJob(myParsedArgs[0])) throw STSHException("Invalid job number!"); 
      STSHJob& job = joblist.getJob(myParsedArgs[0]);

      //Check if the second argument, the index is valid
      int index = myParsedArgs[1];
      std::vector<STSHProcess>& processes = job.getProcesses();
      if (index >= processes.size()) throw STSHException("Invalid index");
      //Get the process at the index
      STSHProcess& myProcess = processes[index];
      pid_t pid = myProcess.getID();
      argsToReturn = pid;
    }
  } 
 return argsToReturn;
}

void STSHShell::handleFg(const char *const arguments[]){
  int jobNum = checkforArguments("fg", arguments);
  // fetch process group number
  STSHJob& job = joblist.getJob(jobNum);
  pid_t pgid = job.getGroupID();
  job.setState(kForeground);
  // give terminal control to the job before resuming it
  if (tcsetpgrp(STDIN_FILENO, job.getGroupID()) < 0) throw STSHException("tcsetpgrp failed to transfer terminal control to process");
  // restart process
  killpg(pgid, SIGCONT);
  // handle finish and interrupts
  handleInterrupts();
}

void STSHShell::handleBg(const char *const arguments[]){
  int jobNum = checkforArguments("fg", arguments);
  // fetch process group number
  STSHJob& job = joblist.getJob(jobNum);
  pid_t pgid = job.getGroupID();
  job.setState(kBackground);
  killpg(pgid, SIGCONT);
}

void STSHShell::handleSlay(const char *const arguments[]){
  pid_t pid = checkforArguments("slay", arguments);
  assert(joblist.containsProcess(pid));
  kill(pid, SIGKILL);
}

void STSHShell::handleHalt(const char *const arguments[]){
  pid_t pid = checkforArguments("halt", arguments);
  assert(joblist.containsProcess(pid));
  kill(pid, SIGTSTP);
}

void STSHShell::handleCont(const char *const arguments[]){
  pid_t pid = checkforArguments("cont", arguments);
  assert(joblist.containsProcess(pid));
  kill(pid, SIGCONT);
}

void STSHShell::constructMonitoredSet(const std::vector<int>& signals){
  sigemptyset(&monitoredSignals);
  for (int signal: signals){
    sigaddset(&monitoredSignals, signal);
  }
}

void STSHShell::parseArgv(char** argv, command c){
  argv[0] = c.command;
  memcpy(argv + 1, c.tokens, kMaxArguments * sizeof(char*));
  argv[kMaxArguments+1] = NULL;
  /* return argv; */
}

void STSHShell::waitOnChildProcesses(){
    int status;
    while (true) {
        pid_t pid = waitpid(-1, &status, WUNTRACED | WCONTINUED | WNOHANG);
        if (pid <= 0) {
            assert(pid == 0 || errno == ECHILD);
            break;
        }
        // get process from pid
        if (!joblist.containsProcess(pid)) return;
        STSHJob& job = joblist.getJobWithProcess(pid);
        assert(job.containsProcess(pid));
        STSHProcess& process = job.getProcess(pid);

        // update process state
        if (WIFEXITED(status) || WIFSIGNALED(status)) process.setState(kTerminated);
        if (WIFSTOPPED(status)) process.setState(kStopped);
        if (WIFCONTINUED(status)) process.setState(kRunning);

        joblist.synchronize(job);
    }
}

void STSHShell::handleInterrupts(){
  int delivered;
  signal(SIGINT, SIG_IGN);
  signal(SIGTSTP, SIG_IGN);
  signal(SIGINT, SIG_DFL);
  signal(SIGTSTP, SIG_DFL);
  while (joblist.hasForegroundJob()){
    STSHJob& job = joblist.getForegroundJob();
    sigwait(&monitoredSignals, &delivered);
    switch(delivered){
    case SIGINT:
      killpg(job.getGroupID(), SIGINT);
      break;
    case SIGTSTP:
      killpg(job.getGroupID(), SIGTSTP);
      break;
    case SIGCHLD:
      waitOnChildProcesses();
      break;
    }
  }
  // take back control of terminal if necessary
  if (tcsetpgrp(STDIN_FILENO, getpid()) < 0) throw STSHException("terminal failed to take terminal control back");
}

/**
 * Create a new job for the provided pipeline. Spawns child processes with
 * input/output redirected to the appropriate pipes and/or files, and updates
 * the joblist to keep track of these processes.
 */
void STSHShell::createJob(const pipeline& p){
  // Create a new job, to which you'll add any new child processes:
  STSHJob& job= joblist.addJob(kForeground);
  if (p.background) job.setState(kBackground);

  sigprocmask(SIG_BLOCK, &monitoredSignals, NULL);
  char * argv[kMaxArguments + 2];
  pid_t pids[p.commands.size()];
  vector<array<int, 2>> fdsArr;
  for (size_t i = 0; i < p.commands.size(); i++){
      array<int, 2> fds;
      fdsArr.push_back(fds);
      pipe2(fdsArr[i].data(), O_CLOEXEC);

      pids[i] = fork();
      if (pids[i] == 0){
	  if (i == 0){
	    setpgid(pids[0], 0);
	    if (!p.background){
	      // give the first child control of the terminal
	      if (tcsetpgrp(STDIN_FILENO, getpid()) < 0) throw STSHException("failed to transfer terminal control to process");
	    }
	    if (!p.input.empty()){
               int fd_input = open(p.input.c_str(), O_RDONLY | O_CLOEXEC);
	       if (fd_input == -1) throw STSHException("Could not open file for input redirection");
               dup2(fd_input, STDIN_FILENO);
	    }
            close(fdsArr[0][0]);
	  }
	  else setpgid(pids[i], pids[0]);

	  // unblock signals
	  sigprocmask(SIG_UNBLOCK, &monitoredSignals, NULL);
	  signal(SIGINT, SIG_DFL);
	  signal(SIGTSTP, SIG_DFL);

	  // rewire pipes 
	  if (i > 0){
	      dup2(fdsArr[i-1][0], STDIN_FILENO);
	      // close unnecessary fds
	      close(fdsArr[i-1][1]);
	  }

	  if (i < p.commands.size()-1){
            dup2(fdsArr[i][1], STDOUT_FILENO);
          }
          else {
	    if (!p.output.empty()){
              int fd_output = open(p.output.c_str(), O_CREAT | O_WRONLY | O_TRUNC | O_CLOEXEC, 0644);
              if (fd_output == -1) throw STSHException("Could not open file for output redirection");
              dup2(fd_output, STDOUT_FILENO);
            }
          }
	  // close unnecessary fds
	  close(fdsArr[i][0]);

	  // execute command
	  parseArgv(argv, p.commands[i]);
	  if (execvp(argv[0], argv) == -1) throw STSHException("execvp failed!");   
      }
  }

  for (size_t i = 0; i < p.commands.size() ; i++){
      STSHProcess myProcess(pids[i], p.commands[i]);
      job.addProcess(myProcess);
      // close all fds in parent
      close(fdsArr[i][0]);
      close(fdsArr[i][1]);
  }
  if (p.background){
      // print job summary
      const std::vector<STSHProcess>& allProcesses = job.getProcesses();
      cout << "[" << job.getNum() << "] " << flush;
      for (auto& process: allProcesses){
	  cout << process.getID() << " " << flush;
      }
      cout << endl;
  }
  handleInterrupts();
}

/**
 * Define the entry point for a process running stsh.
 */
int main(int argc, char *argv[]) {
  STSHShell shell;
  shell.configureSignals();
  shell.run(argc, argv);
  return 0;
}
