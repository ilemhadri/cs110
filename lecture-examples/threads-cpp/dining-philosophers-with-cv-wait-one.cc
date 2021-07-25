/**
 * File: dining-philosophers-with-cv-wait-one.cc
 * ---------------------------------------------
 * This program implements the classic dining philosophers
 * simulation.  This is the first version that actually
 * does the right thing. :)
 */

#include <thread>
#include <mutex>
#include <condition_variable>
#include <iostream>
#include "ostreamlock.h"
#include "random-generator.h"
#include "thread-utils.h"
using namespace std;

/**
 * Defines a collection of timing constants used for 
 * the dining philosopher simulation.
 */

static const unsigned int kLowThinkTime = 100;
static const unsigned int kHighThinkTime = 2000;
static const unsigned int kLowSleepTime = 25;
static const unsigned int kHighSleepTime = 50;

/**
 * Defines the single RandomGenerator class used to generate
 * random timing amounts to allow for variety in the dining 
 * philosopher simulation.
 */

static mutex rgenLock;
static RandomGenerator rgen;

static unsigned int getThinkTime() {
  lock_guard<mutex> lg(rgenLock);
  return rgen.getNextInt(kLowThinkTime, kHighThinkTime);
}

static unsigned int getEatTime() {
  lock_guard<mutex> lg(rgenLock);
  return rgen.getNextInt(kLowSleepTime, kHighSleepTime);
}

/**
 * Defines the collection of constants (not related at all to timing)
 * needed for the dining philosophers simulation.
 */

static const size_t kNumPhilosophers = 5;
static const size_t kNumForks = kNumPhilosophers;
static const size_t kNumMeals = 3;

static void waitForPermission(size_t& permits, condition_variable_any& cv, mutex& m) {
  lock_guard<mutex> lg(m);
  while (permits == 0) cv.wait(m);
  permits--;
}

static void grantPermission(size_t& permits, condition_variable_any& cv, mutex& m) {
  lock_guard<mutex> lg(m);
  permits++;
  if (permits == 1) cv.notify_all();
}

static void think(size_t id) {
  cout << oslock << id << " starts thinking." << endl << osunlock;
  sleep_for(getThinkTime());
  cout << oslock << id << " all done thinking. " << endl << osunlock;
}

static void eat(size_t id, mutex& left, mutex& right, size_t& permits, condition_variable_any& cv, mutex& m) {
  waitForPermission(permits, cv, m);
  left.lock();
  right.lock();
  cout << oslock << id << " starts eating om nom nom nom." << endl << osunlock;
  sleep_for(getEatTime());
  cout << oslock << id << " all done eating." << endl << osunlock;
  grantPermission(permits, cv, m);
  left.unlock();
  right.unlock();
}

static void philosopher(size_t id, mutex& left, mutex& right, size_t& permits, condition_variable_any& cv, mutex& m) {
  for (size_t i = 0; i < kNumMeals; i++) {
    think(id);
    eat(id, left, right, permits, cv, m);
  }
}

int main(int argc, const char *argv[]) {
  size_t permits = kNumForks - 1;
  mutex forks[kNumForks], m;
  condition_variable_any cv;
  thread philosophers[kNumPhilosophers];
  for (size_t i = 0; i < kNumPhilosophers; i++) {
    mutex& left = forks[i],
         & right = forks[(i + 1) % kNumForks];
    philosophers[i] = thread(philosopher, i, ref(left), ref(right), ref(permits), ref(cv), ref(m));
  }
  for (thread& p: philosophers) p.join();
  return 0;
}
