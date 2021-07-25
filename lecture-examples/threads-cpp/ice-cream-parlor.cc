/** 
 * File: ice-cream-parlor.cc
 * -------------------------
 * An larger example used to show a combination of synchronization techniques 
 * (binary locks, generalized counters, rendezvous semaphores) in a more complicated 
 * arrangement.
 *
 * This is the "ice cream store" simulation.  There are customers who want
 * to buy ice cream cones, clerks who make the cones, the manager who
 * checks a clerk's work, and the cashier who takes a customer's
 * money.  There are a many different interactions that need to be modeled:
 * the customers dispatching several clerks (one for each cone they are buying),
 * the clerks who need the manager to approve their work, the cashier
 * who rings up each customer in a first-in-first-out, and so on.
 */

#include <thread>
#include <mutex>
#include <vector>
#include <iostream>
#include <atomic>
#include "semaphore.h"
#include "ostreamlock.h"
#include "random-generator.h"
#include "thread-utils.h"
using namespace std;

static const unsigned int kNumCustomers = 15;
static const unsigned int kMinConeOrder = 1;
static const unsigned int kMaxConeOrder = 4;
static const unsigned int kMinBrowseTime = 100;
static const unsigned int kMaxBrowseTime = 300;
static const unsigned int kMinPrepTime = 50;
static const unsigned int kMaxPrepTime = 300;
static const unsigned int kMinInspectionTime = 20;
static const unsigned int kMaxInspectionTime = 100;
static const double kConeApprovalProbability = 0.1;

/**
 * Everything from here down to the next comment is used to
 * generate random sleep times and model the variations in
 * execution that come with a real, concurrent, mostly unpredictable system.
 */

static mutex rgenLock;
static RandomGenerator rgen;

static unsigned int getNumCones() {
  lock_guard<mutex> lg(rgenLock);
  return rgen.getNextInt(kMinConeOrder, kMaxConeOrder);
}

static unsigned int getBrowseTime() {
  lock_guard<mutex> lg(rgenLock);
  return rgen.getNextInt(kMinBrowseTime, kMaxBrowseTime);
}

static unsigned int getPrepTime() {
  lock_guard<mutex> lg(rgenLock);
  return rgen.getNextInt(kMinPrepTime, kMaxPrepTime);
}

static unsigned int getInspectionTime() {
  lock_guard<mutex> lg(rgenLock);
  return rgen.getNextInt(kMinInspectionTime, kMaxInspectionTime);
}

static bool getInspectionOutcome() {
  lock_guard<mutex> lg(rgenLock);
  return rgen.getNextBool(kConeApprovalProbability);
}

/**
 * The inspection record is a single, global record used to
 * coordinate interaction between a single clerk and the manager.
 * The available mutex is used by a clerk to transactionally 
 * acquire the one manager's undivided attention.  The requested
 * and finished semaphores are used to coordinate bidirectional
 * rendezvous between the clerk and the manager.  The passed
 * bool stores the approval status of the ice cream cone made by
 * the clerk holding the manager's attention.
 */

struct {
  mutex available;
  semaphore requested;
  semaphore finished;
  bool passed;
} inspection;

/**
 * The checkout record is a single, global record used to
 * coordinate interactions between all of the customers and
 * the cashier.  We introduce the atomic<unsigned int> as means
 * for providing an exposed nonnegative integer that supports
 * ++ and -- in such a way that it's guaranteed to be atomic
 * on all platforms.  The waitingCustomers semaphore is used to
 * inform the cashier that one or more people are waiting in
 * line, and the array-based queue of semaphores are used to foster
 * cashier-to-customer rendezvous so each customer knows that
 * his/her payment has been accepted.
 */

struct checkout {
  checkout(): nextPlaceInLine(0) {}
  atomic<unsigned int> nextPlaceInLine;
  semaphore customers[kNumCustomers];
  semaphore waitingCustomers;
} checkout;

/**
 * Utility functions: browse and makeCone
 * --------------------------------------
 * browse and makeCone are called by customers and
 * clerks to stall and/or emulate the time it might take
 * to do something in a real situation.
 */

static void browse() {
  cout << oslock << "Customer starts to kill time." << endl << osunlock;
  unsigned int browseTime = getBrowseTime();
  sleep_for(browseTime);
  cout << oslock << "Customer just killed " << double(browseTime)/1000
       << " seconds." << endl << osunlock;
}

static void makeCone(unsigned int coneID, unsigned int customerID) {
  cout << oslock << "    Clerk starts to make ice cream cone #" << coneID 
       << " for customer #" << customerID << "." << endl << osunlock;
  unsigned int prepTime = getPrepTime();
  sleep_for(prepTime);
  cout << oslock << "    Clerk just spent " << double(prepTime)/1000 
       << " seconds making ice cream cone#" << coneID 
       << " for customer #" << customerID << "." << endl << osunlock;
}

/**
 * Utility function: inspectCone
 * -----------------------------
 * Called by the manager to simulate the ice-cream-cone inspection
 * process and generate a random bool, where true means the ice cream
 * cone made by the clerk holding his/her attention is good to go, and 
 * false means it needs to be remade.
 */

static void inspectCone() {
  cout << oslock << "  Manager is presented with an ice cream cone." 
       << endl << osunlock;
  unsigned int inspectionTime = getInspectionTime();
  sleep_for(inspectionTime);
  inspection.passed = getInspectionOutcome();
  const char *verb = inspection.passed ? "APPROVED" : "REJECTED";
  cout << oslock << "  Manager spent " << double(inspectionTime)/1000
       << " seconds analyzing presented ice cream cone and " << verb << " it." 
       << endl << osunlock;
}

/**
 * Thread routines: clerk, cashier, manager, and customer
 * ------------------------------------------------------
 * Each of these four functions provide the script that all of the
 * different players follow.
 */

static void clerk(unsigned int coneID, unsigned int customerID) {
  bool success = false;
  while (!success) {
    makeCone(coneID, customerID);
    inspection.available.lock();
    inspection.requested.signal();
    inspection.finished.wait();
    success = inspection.passed;
    inspection.available.unlock();
  }
}

static void cashier() {
  cout << oslock << "      Cashier is ready to take customer money." 
       << endl << osunlock;
  for (unsigned int i = 0; i < kNumCustomers; i++) {
    checkout.waitingCustomers.wait();
    cout << oslock << "      Cashier rings up customer " << i << "." 
         << endl << osunlock;
    checkout.customers[i].signal();
  }
  cout << oslock << "      Cashier is all done and can go home." << endl;
}

static void manager(unsigned int numConesNeeded) {
  unsigned int numConesAttempted = 0; // local variables secret to the manager,
  unsigned int numConesApproved = 0;  // so no locks are needed
  while (numConesApproved < numConesNeeded) {
    inspection.requested.wait();
    inspectCone();
    inspection.finished.signal();
    numConesAttempted++;
    if (inspection.passed) numConesApproved++;
  }
  
  cout << oslock << "  Manager inspected a total of " << numConesAttempted 
       << " ice cream cones before approving a total of " << numConesNeeded 
       << "." << endl;
  cout << "  Manager leaves the ice cream store." << endl << osunlock;
}

static void customer(unsigned int id, unsigned int numConesWanted) {
  // order phase
  vector<thread> clerks;
  for (unsigned int i = 0; i < numConesWanted; i++) 
    clerks.push_back(thread(clerk, i, id));
  browse();
  for (thread& t: clerks) t.join();

  // checkout phase
  int place;
  cout << oslock << "Customer " << id << " assumes position #" 
       << (place = checkout.nextPlaceInLine++) << " at the checkout counter." 
       << endl << osunlock;
  checkout.waitingCustomers.signal();
  checkout.customers[place].wait();
  cout << "Customer " << id << " has checked out and leaves the ice cream store." 
       << endl << osunlock;
}

int main(int argc, const char *argv[]) {
  int totalConesOrdered = 0;
  thread customers[kNumCustomers];
  for (unsigned int i = 0; i < kNumCustomers; i++) {
    int numConesWanted = getNumCones();
    customers[i] = thread(customer, i, numConesWanted);
    totalConesOrdered += numConesWanted;
  }
  thread m(manager, totalConesOrdered);  
  thread c(cashier);

  for (thread& customer: customers) customer.join();
  c.join();
  m.join();
  return 0;
}
