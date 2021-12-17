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
 * Constructor: ThreadPool
 * -----------------------
 * Constructs a ThreadPool configured to spawn up to the specified
 * number of threads.
 */
  ThreadPool(size_t numThreads);

/**
 * Destructor: ~ThreadPool
 * -----------------------
 * Destroys the ThreadPool class.
 */
  ~ThreadPool();

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
  void schedule(const std::function<void(void)>& thunk);

/**
 * Private Method: wait
 * --------------------
 * Blocks and waits until all previously scheduled thunks
 * have been executed in full.
 */
  void wait();

 private:
  ThreadPool(const ThreadPool& original) = delete;
  ThreadPool& operator=(const ThreadPool& rhs) = delete;

  // protects thunkQueue 
  std::mutex queueLock; 
  // protects currentThunks
  std::vector<std::mutex> thunkLock; 
  // protects availableWorker vector to get the available worker id
  std::mutex availableWorkerLock; 
  // protects the waitCounter
  std::mutex waitMutex;

  // use this to notify workers that there is work to do
  std::condition_variable_any nonEmptyQueue; 
  // use this to notify all threads that the thunks have finished executing
  std::condition_variable_any waitCv;

  // keep track of the number of busy workers
  semaphore workerPermits;
  // keep track of the number of scheduled thunks per worker
  std::vector<semaphore> workerSemaphore;

  // dispatcher thread
  std::thread dt;
  // worker threads
  std::vector<std::thread> wts;

  // number of executing thunks
  size_t waitCounter;
  // set to 1 if the destructor is called and 0 otherwise
  int destruct;
  // set to 1 if the worker is available and 0 otherwise
  std::vector<int> availableWorker;

  // keeps track of the scheduled thunks
  std::queue<std::function<void(void)>> thunkQueue;
  // keep track of the current thunk for each worker
  std::vector<std::function<void(void)>> currentThunks;

/**
 * Private Method: getAvailableWorker
 * ----------------------------------
 * Helper method that returns the availble worker.
 */
  size_t getAvailableWorker();

/**
 * Private Method: dispatcher
 * --------------------------
 * Describes the dispatcher's behavior. Dequeues a thunk, waits for an available
 * worker, then assigns the thunk to the available worker, notifying the worker
 * it was work to do.
 */
  void dispatcher();

/**
 * Private Method: worker
 * ----------------------
 * Blocks and waits until the dispatcher thread signals it to execute an assigned
 * function. Once signaled, the worker invokes the function, waits for the function
 * to execute, marks itself as available.
 */
  void worker(size_t workerID);

/**
 * Helper Method: assignTaskToWorker
 * ---------------------------------
 * Helper method that assigns the next thunk in the queue to the appropriate worker.
 */
  void assignTaskToWorker(size_t workerID);

/**
 * Private Helper Method: waitSignal
 * ---------------------------------
 * Notifies all threads when the wait counter reaches 0, i.e. all the functions
 * have completed executing.
 */
  void waitSignal();
};

#endif

}
