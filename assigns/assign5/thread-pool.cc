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

void ThreadPool::assignTaskToWorker(size_t workerID){
    lock_guard<mutex> queueLg(queueLock);
    nonEmptyQueue.wait(queueLock, [this] {return (!thunkQueue.empty() || destruct);});
    if (destruct) return;
    /* lock_guard<mutex> thunkLg(thunkLock); */
    lock_guard<mutex> thunkLg(thunkLock[workerID]);
    currentThunks[workerID] = thunkQueue.front();
    thunkQueue.pop();
    workerSemaphore[workerID].signal();
}

void ThreadPool::schedule(const std::function<void(void)>& thunk){
  lock_guard<mutex> queueLg(queueLock);
  thunkQueue.push(thunk);
  nonEmptyQueue.notify_all();
  lock_guard<mutex> waitMutexLg(waitMutex);
  waitCounter++;
}

void ThreadPool::dispatcher(){
  while (true){
    workerPermits.wait();
    size_t availableWorkerID = getAvailableWorker();
    assert (availableWorkerID >= 0);
    assignTaskToWorker(availableWorkerID);
    if (destruct) break;
  }
}

void ThreadPool::worker(size_t workerID){
  while (true){
    workerSemaphore[workerID].wait();
    if (destruct) break;
    /* execute current thunk */
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

void ThreadPool::waitSignal(){
  lock_guard<mutex> lg(waitMutex);
  if (--waitCounter == 0) waitCv.notify_all();
}

void ThreadPool::wait(){
  lock_guard<mutex> waitMutexLg(waitMutex);
  waitCv.wait(waitMutex, [this] {return waitCounter == 0;});
}

ThreadPool::~ThreadPool(){
  wait();
  // inform workers and dispatcher to exit
  /* destructLock.lock(); */
  queueLock.lock();
  destruct = 1;
  queueLock.unlock();
  /* destructLock.unlock(); */
  nonEmptyQueue.notify_all();
  for (auto& s : workerSemaphore) s.signal();
  // join all threads
  dt.join();
  for (auto& w : wts) w.join();
}
