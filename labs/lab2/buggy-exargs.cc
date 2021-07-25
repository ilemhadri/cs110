/**
 * File: buggy-exargs.cc
 * ---------------------
 * Includes a replica of the program in exargs.cc, except
 * that a memory bug has been intentionally introduced.  The
 * program is designed to be examined using valgrind and gdb
 * so we can better learn how to use tools to find memory errors
 * in a multiprocessing scenario.
 */

#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <algorithm>
#include <cstring>
#include "unistd.h"
#include <sys/wait.h>
using namespace std;

static void pullAllTokens(istream& in, vector<string>& tokens) {
  while (true) {
    string line;
    getline(in, line);
    if (in.fail()) break;
    istringstream iss(line);
    while (true) {      
      string token;
      getline(iss, token, ' ');
      if (iss.fail()) break;
      tokens.push_back(token);
    }
  }
}

int main(int argc, char *argv[]) {
  vector<string> tokens;
  pullAllTokens(cin, tokens);
  pid_t pid = fork();
  if (pid == 0) {
    char **exargsv = NULL;
    memcpy(exargsv, argv + 1, (argc - 1) * sizeof(char *));
    transform(tokens.cbegin(), tokens.cend(), exargsv + argc - 1, 
              [](const string& str) { return const_cast<char *>(str.c_str()); });
    exargsv[argc + tokens.size() - 1] = NULL;
    execvp(exargsv[0], exargsv);
    cerr << exargsv[0] << ": command not found" << endl;
    exit(0);
  }
  
  int status;
  waitpid(pid, &status, 0);
  return status == 0 ? 0 : 1; // trivia: if all of status is 0, then child exited normally with code 0
}
