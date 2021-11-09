/**
 * File: thread-pool.h
 * -------------------
 * Exports a ThreadPool abstraction, which manages a finite pool
 * of worker threads that collaboratively work through a sequence of tasks.
 * As each task is scheduled, the ThreadPool waits for at least
 * one worker thread to be free and then assigns that task to that worker.  
 * Threads are scheduled and served in a FIFO manner, and tasks need to
 * take the form of thunks, which are zero-argument thread routines.
 */

#ifndef _thread_pool_
#define _thread_pool_

#include <cstdlib>
#include <functional>

// place additional #include statements here
#include <vector>
#include <queue>
#include <mutex>
#include <thread>
#include <condition_variable>
#include <semaphore.h>

namespace develop {

class ThreadPool {
 public:

/**
 * Constructs a ThreadPool configured to spawn up to the specified
 * number of threads.
 */
  ThreadPool(size_t numThreads);

/**
 * Destroys the ThreadPool class
 */
  ~ThreadPool();

/**
 * Schedules the provided thunk (which is something that can
 * be invoked as a zero-argument function without a return value)
 * to be executed by one of the ThreadPool's threads as soon as
 * all previously scheduled thunks have been handled.
 */
  void schedule(const std::function<void(void)>& thunk);

/**
 * Blocks and waits until all previously scheduled thunks
 * have been executed in full.
 */
  void wait();

 private:
  ThreadPool(const ThreadPool& original) = delete;
  ThreadPool& operator=(const ThreadPool& rhs) = delete;

  // added this for Milestone 3
  std::mutex queueLock; // protects thunkQueue 
  std::vector<std::mutex> thunkLock; // protects currentThunks
  std::mutex availableWorkerLock; // use this to get the available worker id
  std::mutex waitMutex;

  std::condition_variable_any nonEmptyQueue; //use this to notify workers that there is work to do
  std::condition_variable_any waitCv;

  semaphore workerPermits;
  std::vector<semaphore> workerSemaphore;

  std::thread dt;
  std::vector<std::thread> wts;

  size_t waitCounter;
  int destruct;
  std::vector<int> availableWorker;

  std::queue<std::function<void(void)>> thunkQueue;
  std::vector<std::function<void(void)>> currentThunks;

  size_t getAvailableWorker();
  void dispatcher();
  void worker(size_t workerID);
  void assignTaskToWorker(size_t workerID);
  void waitSignal();
};

#endif

}
