/**
 * File: myth-buster-sequential.cc
 * -------------------------------
 * Presents a sequential (and very slow) program that serializes
 * an array of network calls to find out how many CS110 student processes
 * are running on each of the myth machines so that the "least loaded"
 * one can be identified.
 */

#include <unistd.h>
#include <cstring>
#include <iostream>
#include <sstream>
#include <fstream>
#include <unordered_set>
#include <map>
#include <vector>
#include <algorithm>
#include "myth-buster-service.h"
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

static const int kMinMythMachine = 51;
static const int kMaxMythMachine = 66;
static void compileCS110ProcessCountMap(const unordered_set<string>& sunetIDs,
					map<int, int>& processCountMap) {
  for (int num = kMinMythMachine; num <= kMaxMythMachine; num++) {
    int numProcesses = getNumProcesses(num, sunetIDs);
    if (numProcesses >= 0) {
      processCountMap[num] = numProcesses;
      cout << "myth" << num << " has this many CS110-student processes: " << numProcesses << endl;
    }
  }
}

static void publishLeastLoadedMachineInfo(const map<int, int>& processCountMap) {
  auto compfn = [](const pair<int, int>& one,
		   const pair<int, int>& two) -> bool {
    return one.second < two.second || (one.second == two.second && one.first > two.first);
  };

  auto leastLoaded = min_element(processCountMap.cbegin(), processCountMap.cend(), compfn);
  cout << "Machine least loaded by CS110 students: myth" << leastLoaded->first << endl;
  cout << "Number of CS110 processes on least loaded machine: " << leastLoaded->second << endl;
}

static const char *kCS110StudentIDsFile = "studentsunets.txt";
int main(int argc, char *argv[]) {
  unordered_set<string> cs110Students;
  readStudentFile(cs110Students, argv[1] != NULL ? argv[1] : kCS110StudentIDsFile);
  map<int, int> processCountMap;
  compileCS110ProcessCountMap(cs110Students, processCountMap);
  publishLeastLoadedMachineInfo(processCountMap);
  return 0;
}
