#include <cassert>
#include <ctime>
#include <cctype>
#include <cstdio>
#include <iostream>
#include <cstdlib>
#include <vector>
#include <sys/wait.h>
#include <unistd.h>
#include <sched.h>
#include "subprocess.h"
#include "fork-utils.h"  // this has to be the last #include'd statement in the file
using namespace std;

static const size_t kNumCPUs = sysconf(_SC_NPROCESSORS_ONLN);

static const char *kWorkerArguments[] = {"./factor.py", "--self-halting", NULL};

static void spawnAllWorkers(vector<subprocess_t>& workers) {
  cout << "There are this many CPUs: " << kNumCPUs << ", numbered 0 through " << kNumCPUs - 1 << "." << endl;
  for (size_t i = 0; i < kNumCPUs; i++) {
    // launch worker
    subprocess_t currProcess = subprocess(kWorkerArguments, true, false);
    workers.push_back(currProcess);

    // link CPU to worker
    cpu_set_t cpuSet;
    CPU_ZERO(&cpuSet);
    CPU_SET(i, &cpuSet);
    sched_setaffinity(currProcess.pid, 1, &cpuSet);

    cout << "Worker " << workers[i].pid << " is set to run on CPU " << i << "." << endl;
  }
}

static const subprocess_t& getAvailableWorker(vector<subprocess_t>& workers) {
  pid_t pid = waitpid(-1, NULL, WUNTRACED);

  static subprocess_t availableWorker = workers[0];
  for (subprocess_t& worker: workers){
    if (worker.pid == pid){
        availableWorker = worker;
        break;
    }
  }
  return availableWorker;
}

static void broadcastNumbersToWorkers(vector<subprocess_t>& workers) {
  while (true) {
    string line;
    getline(cin, line);
    if (cin.fail()) break;
    size_t endpos;
    long long num = stoll(line, &endpos);
    if (endpos != line.size()) break;
    // get available worker
    const subprocess_t currWorker = getAvailableWorker(workers);
    // send num to currWorker
    dprintf(currWorker.supplyfd, "%lld\n", num); 
    // continue the subprocess
    kill(currWorker.pid, SIGCONT);
  }
}

static void waitForAllWorkers(vector<subprocess_t>& workers) {
  for (auto& worker: workers){
    waitpid(worker.pid, NULL, WUNTRACED);
  }
}

static void closeAllWorkers(vector<subprocess_t>& workers) {
  for (auto& worker: workers){
    close(worker.supplyfd);
    kill(worker.pid, SIGCONT);
    waitpid(worker.pid, NULL, 0);
  }
}

int main(int argc, char *argv[]) {
  vector<subprocess_t> workers;
  spawnAllWorkers(workers);
  broadcastNumbersToWorkers(workers);
  waitForAllWorkers(workers);
  closeAllWorkers(workers);
  return 0;
}
