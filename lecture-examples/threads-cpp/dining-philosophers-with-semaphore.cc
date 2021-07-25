/**
 * File: dining-philosophers-with-semaphore.cc
 * -------------------------------------------
 * This program implements the classic dining philosophers
 * simulation using the sempahore class.  We'll call this the
 * final product, since it uses the semaphore, which all
 * prior examples wanted to do. :)
 */

#include <thread>
#include <mutex>
#include <condition_variable>
#include <iostream>
#include "ostreamlock.h"
#include "random-generator.h"
#include "thread-utils.h"
#include "semaphore.h"
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

static void think(size_t id) {
  cout << oslock << id << " starts thinking." << endl << osunlock;
  sleep_for(getThinkTime());
  cout << oslock << id << " all done thinking. " << endl << osunlock;
}

static void eat(size_t id, mutex& left, mutex& right, semaphore& permits) {
  permits.wait();
  left.lock();
  right.lock();
  cout << oslock << id << " starts eating om nom nom nom." << endl << osunlock;
  sleep_for(getEatTime());
  cout << oslock << id << " all done eating." << endl << osunlock;
  permits.signal();
  left.unlock();
  right.unlock();
}

static void philosopher(size_t id, mutex& left, mutex& right, semaphore& permits) {
  for (size_t i = 0; i < kNumMeals; i++) {
    think(id);
    eat(id, left, right, permits);
  }
}

int main(int argc, const char *argv[]) {
  semaphore permits(kNumForks - 1);
  mutex forks[kNumForks];
  thread philosophers[kNumPhilosophers];
  for (size_t i = 0; i < kNumPhilosophers; i++) 
    philosophers[i] = thread(philosopher, i, ref(forks[i]), ref(forks[(i + 1) % kNumForks]), ref(permits));
  for (thread& p: philosophers) p.join();
  return 0;
}
