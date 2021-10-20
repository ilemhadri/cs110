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

int simpleTrace(char *argv[], int numFlags){
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
        ptrace(PTRACE_SYSCALL, pid, 0, 0);
        waitpid(pid, &status, 0);

        if (WIFSTOPPED(status) && (WSTOPSIG(status) == (SIGTRAP | 0x80))) {

            /* # read sys-call enter */
            int num = ptrace(PTRACE_PEEKUSER, pid, ORIG_RAX * sizeof(long));
            cout << "syscall(" << num << ") = " << flush;
            ptrace(PTRACE_SYSCALL, pid, 0, 0);
            waitpid(pid, &status, 0);

            /* read sys-call exit */
            if (WIFSTOPPED(status) && (WSTOPSIG(status) == (SIGTRAP | 0x80))) {
                long ret = ptrace(PTRACE_PEEKUSER, pid, RAX * sizeof(long));
                cout << ret << endl;
            }
        }

        /* end of sys calls; return child's value */
        if (WIFEXITED(status)){
            cout << "<no return> \nProgram exited normally with status " <<  WEXITSTATUS(status) << endl;
            return WEXITSTATUS(status);
        }
    }
    return -1;
}


static string readString(pid_t pid, unsigned long addr) {
  string str;
  char * char_addr = (char *) addr;
  size_t numLongsRead = 0;
  int done = 0;
  int offset = 0;
  while (!done){
    long ret = ptrace(PTRACE_PEEKDATA, pid, char_addr + (numLongsRead++)*sizeof(long), 0);
    while (!done && offset<sizeof(long)){
      char currChar = ((char *)&ret)[offset];
      done=currChar=='\0';
      if (!done) str += currChar;
      ++offset;
    }
    offset = 0;
  }
  return str;
}


int fullTrace(char *argv[], int numFlags, const std::map<int, std::string> &systemCallNumbers, const std::map<std::string, systemCallSignature> &systemCallSignatures, const std::map<int, std::string> &errorConstants) {
    const int ixToReg[] = {RDI, RSI, RDX, R10, R8, R9};
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
        ptrace(PTRACE_SYSCALL, pid, 0, 0);
        waitpid(pid, &status, 0);

        if (WIFSTOPPED(status) && (WSTOPSIG(status) == (SIGTRAP | 0x80))) {
            /* # read sys-call enter */
            int num = ptrace(PTRACE_PEEKUSER, pid, ORIG_RAX * sizeof(long));

            // read function name
            std::string callName = systemCallNumbers.at(num);
            cout << callName << "(" << flush;

            // read arguments
            if (systemCallSignatures.find(callName) == systemCallSignatures.end()){
            cout << "<signature-information-missing>" << flush;
            }
            else {
                const systemCallSignature& signature = systemCallSignatures.at(callName);
                size_t numArgs = signature.size();
                for (size_t i = 0 ; i < numArgs; i++){
                    long peekValue = ptrace(PTRACE_PEEKUSER,pid, ixToReg[i] * sizeof(long));
                    scParamType arg = signature[i];
                    switch(arg){
                        case SYSCALL_INTEGER:{
                            int myInt = (int) peekValue;
                            cout << myInt << flush;
                            break;
                        }

                        case SYSCALL_POINTER:{
                            if (peekValue == 0) {
                                cout << "NULL" << flush;
                                } else {
                                void * myPtr = (void *) peekValue;
                                cout << myPtr << flush;
                                }
                            break;
                        }

                        case SYSCALL_STRING:{
                            string myStr = readString(pid, peekValue);
                            cout << '"' << myStr << '"' << flush;
                            break;
                        }

                        default:{
                            cout << "<unknown>" << flush;
                        }
                    }
                    
                    if (i < numArgs - 1) {
                    cout << ", " << flush;
                    }
                }
            }
            cout << ") = " << flush;

            /* read sys-call exit */
            ptrace(PTRACE_SYSCALL, pid, 0, 0);
            waitpid(pid, &status, 0);
            if (WIFSTOPPED(status) && (WSTOPSIG(status) == (SIGTRAP | 0x80))) {
                long ret = ptrace(PTRACE_PEEKUSER, pid, RAX * sizeof(long));
                const int retInt = (const int) ret;
                if (ret >= 0) {
                  if ((callName == "brk") || (callName == "mmap")){
                    if (ret == 0){
                      cout << "NULL" << endl;
                    } else {
                        // interpret as 64-bit pointer
                        void * retPtr = (void *) ret;
                        cout << retPtr << endl;
                   }
                 } else {
                    // interpret as int
                    cout << ret << endl;
                  }
                } else {
                  // return error message
                  cout << "-1 " <<  errorConstants.at(-retInt) << " (" << strerror(-retInt) << ")" << endl;
                }
            }
        }

        /* end of sys calls; return child's value */
        if (WIFEXITED(status)){
            cout << "<no return> \nProgram exited normally with status " <<  WEXITSTATUS(status) << endl;
            return WEXITSTATUS(status);
        }
    }
    return -1;
}


int main(int argc, char *argv[]) {
    bool simple = false, rebuild = false;
    int numFlags = processCommandLineFlags(simple, rebuild, argv);
    if (argc - numFlags == 1) {
        cout << "Nothing to trace... exiting." << endl;
        return 0;
    }

    // create system call map if running a full trace or rebuilding the map, or access cache and store info in the maps
    std::map<int, std::string> systemCallNumbers;
    std::map<std::string, systemCallSignature> systemCallSignatures;
    compileSystemCallData(systemCallNumbers, systemCallSignatures, rebuild);

    /* compile error constants */
    std::map<int, std::string> errorConstants;
    compileSystemCallErrorStrings(errorConstants);

    // run full trace instead of simple trace
    if (!simple) {
        return fullTrace(argv, numFlags, systemCallNumbers, systemCallSignatures, errorConstants);
    }

    return simpleTrace(argv, numFlags);
}
