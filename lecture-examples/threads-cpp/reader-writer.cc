/**
 * Implements the classic reader-writer thread example, where
 * one thread writes to a shared buffer and a second thread reads
 * from it.
 */

#include <mutex>
#include <thread>
#include <iostream>
#include "ostreamlock.h"
#include "random-generator.h"
#include "semaphore.h"
#include "thread-utils.h"
using namespace std;

static const unsigned int kLowPrepareTime = 10;
static const unsigned int kHighPrepareTime = 100;
static const unsigned int kLowProcessTime = 20;
static const unsigned int kHighProcessTime = 120;

static mutex rgenLock;
static RandomGenerator rgen;

static unsigned int getSleepDuration(unsigned int low, unsigned int high) {
  lock_guard<mutex> lg(rgenLock);
  return rgen.getNextInt(low, high);
}

static char prepareData() {
  sleep_for(getSleepDuration(kLowPrepareTime, kHighPrepareTime));
  lock_guard<mutex> lg(rgenLock);
  return rgen.getNextInt('A', 'Z');
}

static void processData(char ch) {
  sleep_for(getSleepDuration(kLowProcessTime, kHighProcessTime));
}

static const unsigned int kNumBuffers = 8;
static const unsigned int kNumCycles = 40;

static void writer(char buffer[], semaphore& full, semaphore& empty) {
  cout << oslock << "Writer: ready to write." << endl << osunlock;
  for (size_t i = 0; i < kNumCycles * kNumBuffers; i++) {
    char ch = prepareData();
    empty.wait();   // don't try to write to a slot unless you know it's empty
    buffer[i % kNumBuffers] = ch;
    full.signal();  // signal reader there's more stuff to read
    cout << oslock << "Writer: published data packet with character '" 
	 << ch << "'." << endl << osunlock;
  }
}

static void reader(char buffer[], semaphore& full, semaphore& empty) {
  cout << oslock << "\t\tReader: ready to read." << endl << osunlock;
  for (size_t i = 0; i < kNumCycles * kNumBuffers; i++) {
    full.wait();    // don't try to read from a slot unless you know it's full
    char ch = buffer[i % kNumBuffers];
    empty.signal(); // signal writer there's a slot that can receive data
    processData(ch);
    cout << oslock << "\t\tReader: consumed data packet " 
	 << "with character '" << ch << "'." << endl << osunlock;
  }
}

int main(int argc, const char *argv[]) {
  char buffer[kNumBuffers];
  semaphore fullBuffers, emptyBuffers(kNumBuffers);
  thread w(writer, buffer, ref(fullBuffers), ref(emptyBuffers));
  thread r(reader, buffer, ref(fullBuffers), ref(emptyBuffers));
  w.join();
  r.join();
  return 0;
}
