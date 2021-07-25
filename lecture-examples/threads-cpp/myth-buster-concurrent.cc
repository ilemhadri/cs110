/**
 * File: myth-buster-concurrent.cc
 * -------------------------------
 * Presents a multi-threaded version of the same exact program presented
 * in myth-buster-sequential.cc
 */

#include <iostream>
#include <fstream>
#include <unordered_set>
#include <map>
#include <vector>
#include <algorithm>
#include <thread>
#include <mutex>
#include "myth-buster-service.h"
#include "ostreamlock.h"
#include "semaphore.h"
#include "string-utils.h"
using namespace std;

static const int kFileInaccessible = 1;
static void readStudentFile(unordered_set<string>& sunetIDs, const string& filename) {
  ifstream infile(filename.c_str());
  if (infile.fail()) {
    cerr << "CS110 Student SUNet ID list not found." << endl;
    exit(kFileInaccessible);
  }
  
  while (true) {
    string sunetID;
    getline(infile, sunetID);
    if (infile.fail()) return;
    sunetID = trim(sunetID);
    sunetIDs.insert(sunetID);
  }
}

static void countCS110Processes(int num, const unordered_set<string>& sunetIDs,
                                map<int, int>& processCountMap, mutex& processCountMapLock,
                                semaphore& permits) {
    permits.signal(on_thread_exit);
    int numProcesses = getNumProcesses(num, sunetIDs);
    if (numProcesses >= 0) {
        processCountMapLock.lock();
        processCountMap[num] = numProcesses;
        processCountMapLock.unlock();
        cout << "myth" << num << " has this many CS110-student processes: " << numProcesses << endl;
    }
}

static const int kMinMythMachine = 51;
static const int kMaxMythMachine = 66;
static const int kMaxNumThreads = 8; // really maximum number of threads doing meaningful work
static void compileCS110ProcessCountMap(const unordered_set<string> sunetIDs,
                                        map<int, int>& processCountMap) {  
  vector<thread> threads;
  mutex processCountMapLock;
  semaphore permits(kMaxNumThreads);
  for (int num = kMinMythMachine; num <= kMaxMythMachine; num++) {
    permits.wait();
    threads.push_back(thread(countCS110Processes, num, ref(sunetIDs),
                             ref(processCountMap), ref(processCountMapLock),
                             ref(permits)));
  }
  
  for (thread& t: threads) t.join();
}

static bool isLessLoaded(const pair<int, int>& one,
			 const pair<int, int>& two) {
  return one.second < two.second || (one.second == two.second && one.first > two.first);
}

static void publishLeastLoadedMachineInfo(const map<int, int>& processCountMap) {
  auto leastLoaded = min_element(processCountMap.cbegin(), processCountMap.cend(), isLessLoaded);
  cout << "Machine least loaded by CS110 students: myth" << leastLoaded->first << endl;
  cout << "Number of CS110 processes on least loaded machine: " << leastLoaded->second << endl;
}

static const char *kCS110StudentIDsFile = "studentsunets.txt";
int main(int argc, char *argv[]) {
  unordered_set<string> sunetIDs;
  readStudentFile(sunetIDs, argv[1] != NULL ? argv[1] : kCS110StudentIDsFile);
  map<int, int> processCountMap;
  compileCS110ProcessCountMap(sunetIDs, processCountMap);
  publishLeastLoadedMachineInfo(processCountMap);
  return 0;
}
