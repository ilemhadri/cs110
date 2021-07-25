/**
 * File: subprocess.cc
 * -------------------
 * Presents the implementation of the subprocess routine.
 */

#include "subprocess.h"
#include "fork-utils.h" // this has to be the very last #include statement in this .cc file!
using namespace std;

subprocess_t subprocess(char *argv[], bool supplyChildInput, bool ingestChildOutput) throw (SubprocessException) {
  throw SubprocessException("subprocess: not yet implemented.");
}
