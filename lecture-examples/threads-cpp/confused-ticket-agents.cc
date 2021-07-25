#include <mutex>     // for mutex
#include <thread>    // for thread
#include <iostream>  // for cout, cerr, endl
#include "random-generator.h"
#include "ostreamlock.h"
#include "thread-utils.h"
using namespace std;

static const unsigned int kMinCallTime = 100;
static const unsigned int kMaxCallTime = 500;
static const unsigned int kMinBreakTime = 100;
static const unsigned int kMaxBreakTime = 500;
static const double kChanceBreakTaken = 0.8;

static mutex rgenLock;
static RandomGenerator rgen;

static unsigned int getCallDuration() {
  lock_guard<mutex> lg(rgenLock);
  return rgen.getNextInt(kMinCallTime, kMaxCallTime);
}

static void handleCall() {
  sleep_for(getCallDuration());
}

static bool shouldTakeBreak() {
  lock_guard<mutex> lg(rgenLock);
  return rgen.getNextBool(kChanceBreakTaken);
}

static unsigned int getBreakDuration() {
  lock_guard<mutex> lg(rgenLock);
  return rgen.getNextInt(kMinBreakTime, kMaxBreakTime);
}

static void takeBreak() {
  sleep_for(getBreakDuration());
}

static const unsigned int kBaseIDNumber = 101;
static const unsigned int kNumAgents = 10;
static const unsigned int kNumTickets = 250;

static void ticketAgent(size_t id, unsigned int& remainingTickets) {
  while (remainingTickets > 0) {
    handleCall();
    remainingTickets--;
    cout << oslock << "Agent #" << id << " sold a ticket! (" << remainingTickets 
	 << " more to be sold)." << endl << osunlock;
    if (shouldTakeBreak()) 
      takeBreak();
  }
  cout << oslock << "Agent #" << id << " notices all tickets are sold, and goes home!" 
       << endl << osunlock;
}

int main(int argc, const char *argv[]) {
  unsigned int remainingTickets = kNumTickets;
  thread agents[kNumAgents];
  for (size_t i = 0; i < kNumAgents; i++)
    agents[i] = thread(ticketAgent, kBaseIDNumber + i, ref(remainingTickets));
  for (thread& agent: agents) 
    agent.join();
  cout << "End of Business Day!" << endl;
  return 0;
}
