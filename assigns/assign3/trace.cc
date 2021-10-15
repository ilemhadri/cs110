/**
 * File: trace.cc
 * ----------------
 * Presents the implementation of the trace program, which traces the execution of another
 * program and prints out information about every single system call it makes.  For each system call,
 * trace prints:
 *
 *    + the name of the system call,
 *    + the values of all of its arguments, and
 *    + the system call return value
 */

#include <cassert>
#include <iostream>
#include <map>
#include <unistd.h> // for fork, execvp
#include <string.h> // for memchr, strerror
#include <sys/ptrace.h>
#include <sys/reg.h>
#include <sys/wait.h>
#include "trace-options.h"
#include "trace-error-constants.h"
#include "trace-system-calls.h"
#include "trace-exception.h"
#include "fork-utils.h" // this has to be the last #include statement in this file
using namespace std;

int main(int argc, char *argv[]) {
  bool simple = false, rebuild = false;
  int numFlags = processCommandLineFlags(simple, rebuild, argv);
  if (argc - numFlags == 1) {
    cout << "Nothing to trace... exiting." << endl;
    return 0;
  }

  pid_t pid = fork();
  if (pid == 0) {
    ptrace(PTRACE_TRACEME);
    raise(SIGSTOP);
    execvp(argv[numFlags + 1], argv + numFlags + 1);
    return 0;
  }

  int status;
  waitpid(pid, &status, 0);
  assert(WIFSTOPPED(status));
  ptrace(PTRACE_SETOPTIONS, pid, 0, PTRACE_O_TRACESYSGOOD);

  while (true){
      /* # read sys-call enter */
      ptrace(PTRACE_SYSCALL, pid, 0, 0);
      waitpid(pid, &status, 0);

      if (WIFSTOPPED(status) && (WSTOPSIG(status) == (SIGTRAP | 0x80))) {
	int num = ptrace(PTRACE_PEEKUSER, pid, ORIG_RAX * sizeof(long));
	cout << "syscall(" << num << ") = " << flush;
	ptrace(PTRACE_SYSCALL, pid, 0, 0);
	waitpid(pid, &status, 0);
	if (WIFSTOPPED(status) && (WSTOPSIG(status) == (SIGTRAP | 0x80))) {
	    long ret = ptrace(PTRACE_PEEKUSER, pid, RAX * sizeof(long));
	    cout << ret << endl;
	}
      }

      if (WIFEXITED(status)){
	  cout << "<no return> \nProgram exited normally with status " <<  WEXITSTATUS(status) << endl;
	  return WEXITSTATUS(status);
      }
 }

  cout << "Not supposed to reach here" << endl;
  return -1;
