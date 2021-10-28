#pragma once

#include "stsh-job-list.h"
#include "stsh-parser/stsh-parse.h"

class STSHShell {
public:
  void configureSignals();
  void run(int argc, char *argv[]);

private:
  enum Builtin {QUIT, FG, BG, SLAY, HALT, CONT, JOBS};
  static const std::map<std::string, Builtin> kBuiltinCommands;

  /* declare monitoredSignals */
  sigset_t monitoredSignals;
  void constructMonitoredSet(const std::vector<int>& signals);

  STSHJobList joblist;

  /* added for milestone 4 */
  void waitOnChildProcesses();
  void handleInterrupts();

  /* added for milestone 6 */
  void handleFg(const char *const arguments[]);

  /* added for milestone 8 */ 
  size_t checkforArguments(std::string command, const char *const arguments[]);
  void handleBg(const char *const arguments[]);
  void handleSlay(const char *const arguments[]);
  void handleHalt(const char *const arguments[]);
  void handleCont(const char *const arguments[]);

  /* added for advanced milestone*/
  void manageTerminalControl(const STSHJob& job, const pid_t& pid);
  void parseArgv(char ** argv, command c);

  void createJob(const pipeline& p);
  void handleBuiltin(Builtin command, const char *const arguments[]);
};
