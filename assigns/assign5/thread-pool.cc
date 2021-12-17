/**
 * File: thread-pool.cc
 * --------------------
 * Presents the implementation of the ThreadPool class.
 */

#include "thread-pool.h"
#include <assert.h>
#include <iostream>
#include <ostreamlock.h>

using namespace std;
using develop::ThreadPool;

/**
 * Constructor: ThreadPool
 * -----------------------
 * Constructs a ThreadPool configured to spawn up to the specified
 * number of threads.
 */
/* Use initialization list: https://edstem.org/us/courses/14446/discussion/820459 */
ThreadPool::ThreadPool(size_t numThreads) : thunkLock(numThreads), workerPermits(numThreads), workerSemaphore(numThreads), wts(numThreads), waitCounter(0), destruct(0), availableWorker(numThreads), currentThunks(numThreads) {
  // declare every worker as available
  availableWorkerLock.lock();
  for (auto& a: availableWorker) a = 1;
  availableWorkerLock.unlock();
  // launch dispatcher
  dt = thread(&ThreadPool::dispatcher, this);
  // launch workers
  for (size_t workerID = 0; workerID < wts.size(); workerID++){
    wts[workerID] = thread(&ThreadPool::worker, this, workerID);
  }
}

/**
 * Private Method: getAvailableWorker
 * ----------------------------------
 * Helper method that returns the availble worker.
 *
 * @return the index of the worker thread that is available.
 *         -1 if there is not an available thread.
 */
size_t ThreadPool::getAvailableWorker(){
  lock_guard<mutex> availableLockLg(availableWorkerLock);
  for (size_t workerID = 0; workerID < wts.size(); workerID++){
    if (availableWorker[workerID]){
      availableWorker[workerID] = 0;
      return workerID;
    }
  }
  return -1;
}

/**
 * Helper Method: assignTaskToWorker
 * ---------------------------------
 * Helper method that assigns the next thunk in the queue to the appropriate worker.
 *
 * @param workerId - the index of the worker in wts to assign the thunk to.
 */
void ThreadPool::assignTaskToWorker(size_t workerID){
    lock_guard<mutex> queueLg(queueLock);
    nonEmptyQueue.wait(queueLock, [this] {return (!thunkQueue.empty() || destruct);});
    if (destruct) return;
    lock_guard<mutex> thunkLg(thunkLock[workerID]);
    currentThunks[workerID] = thunkQueue.front();
    thunkQueue.pop();
    workerSemaphore[workerID].signal();
}

/**
 * Method: schedule
 * ----------------
 * Schedules the provided thunk (which is something that can be invoked as a
 * zero-argument function without a return value) to be executed by one of the
 * ThreadPool's threads as soon as all previously scheduled thunks have been
 * handled.
 *
 * @param thunk - the function to be scheduled.
 */
void ThreadPool::schedule(const std::function<void(void)>& thunk){
  lock_guard<mutex> queueLg(queueLock);
  thunkQueue.push(thunk);
  nonEmptyQueue.notify_all();
  lock_guard<mutex> waitMutexLg(waitMutex);
  waitCounter++;
}

/**
 * Private Method: dispatcher
 * --------------------------
 * Describes the dispatcher's behavior. Dequeues a thunk, waits for an available
 * worker, then assigns the thunk to the available worker, notifying the worker
 * it was work to do.
 */
void ThreadPool::dispatcher(){
  while (true){
    workerPermits.wait();
    size_t availableWorkerID = getAvailableWorker();
    assert (availableWorkerID >= 0);
    assignTaskToWorker(availableWorkerID);
    if (destruct) break;
  }
}

/**
 * Private Method: worker
 * ----------------------
 * Blocks and waits until the dispatcher thread signals it to execute an assigned
 * function. Once signaled, the worker invokes the function, waits for the function
 * to execute, marks itself as available.
 *
 * @param workerId - the index of the worker to execute the thunk
 */
void ThreadPool::worker(size_t workerID){
  while (true){
    workerSemaphore[workerID].wait();
    if (destruct) break;
    /* execute current thunk */
    /* lock_guard thunkLg(thunkLock[workerID]); */
    thunkLock[workerID].lock();
    currentThunks[workerID]();
    thunkLock[workerID].unlock();
    /* mark worker as available */
    availableWorkerLock.lock();
    availableWorker[workerID] = 1;
    availableWorkerLock.unlock();
    /* signal end of work */
    workerPermits.signal();
    waitSignal();
  }
}

/**
 * Private Helper Method: waitSignal
 * ---------------------------------
 * Notifies all threads when the wait counter reaches 0, i.e. all the functions
 * have completed executing.
 */
void ThreadPool::waitSignal(){
  lock_guard<mutex> lg(waitMutex);
  if (--waitCounter == 0) waitCv.notify_all();
}

/**
 * Private Method: wait
 * --------------------
 * Blocks and waits until all previously scheduled thunks
 * have been executed in full.
 */
void ThreadPool::wait(){
  lock_guard<mutex> waitMutexLg(waitMutex);
  waitCv.wait(waitMutex, [this] {return waitCounter == 0;});
}

/**
 * Destructor: ~ThreadPool
 * -----------------------
 * Destroys the ThreadPool class.
 */
ThreadPool::~ThreadPool(){
  wait();
  // inform workers and dispatcher to exit
  queueLock.lock();
  destruct = 1;
  queueLock.unlock();
  nonEmptyQueue.notify_all();
  for (auto& s : workerSemaphore) s.signal();
  // join all threads
  dt.join();
  for (auto& w : wts) w.join();
}
