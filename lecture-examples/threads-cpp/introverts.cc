/**
 * File: introverts.cc
 * -------------------
 * Analogous to introverts.c in parallel threads-c directory, except
 * that this uses the C++11 threads package, which I'll be relying on
 * from this point forward.  The C++ thread interfaces are type-safe, cleaner, and
 * in my opinion, easier to understand.
 */

#include <iostream>       // for cout, endl;
#include <thread>         // for C++11 thread support
#include "ostreamlock.h"  // for CS110 iomanipulators (oslock, osunlock) used to lock down streams
using namespace std;

static void recharge() {
  cout << oslock << "I recharge by spending time alone." << endl << osunlock;
}

static const size_t kNumIntroverts = 6;
int main(int argc, char *argv[]) {
  cout << "Let's hear from " << kNumIntroverts << " introverts." << endl;
  thread introverts[kNumIntroverts]; // declare array of empty thread handles
  for (thread& introvert: introverts) 
    introvert = thread(recharge);    // move anonymous threads into empty handles
  for (thread& introvert: introverts)
    introvert.join();  
  cout << "Everyone's recharged!" << endl;
  return 0;
}
