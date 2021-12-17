// Learnt:
// -  use one semaphore per worker. Otherwise, using a condition_variable.notify_one() could introduce race condition/deadlock
// if a worker other than getAvailableWorker's catches the notify_one() call
// - pass article by copy rather than reference, and don't worry about the order of feedPool.wait() and articlePool.wait()
// - common mistake: when they try to add to the map, they lock for checking if the value is in the map, and unlock immediately after 
// should only unlock after adding the new vector token to the map. doing otherwise introduces race conditions if the map changed in-between.

// vim indentation trick: gg=G
// Question; difference between ref(mutex) and &mutex
// TODO: set VS tab to 2 spaces

mutex thunkQueueLock; // use this to read/pop from the queue
mutex thunkLock; // use this to share the current thunk 
mutex availableWorkerLock; // use this to get the available worker id
condition_variable_any nonEmptyQueue; //use this to notify workers that there is work to do
semaphore workers(numThreads); // to manage thread permits
vector<semaphore> workerSemaphore[numThreads];
condition_variable_any waitCv;
mutex waitMutex;
int waitCounter;
int destruct;

private:
    vector<thread> wts[numThreads];
    thread dt;
    vector<int> availableWorker[numThreads];
    queue<std::function<void(void)>> thunkQueue;
    std::function<void(void)> currentThunk;

ThreadPool(size_t numThreads): waitCounter(0), destruct(0) {
    // declare every worker as available
    availableWorkerLock.lock();
    for (auto & a: availableWorker) a = 1;
    availableWorkerLock.unlock();

    // launch dispatcher
    dt = thread(&ThreadPool::dispatcher, this);

    // launch workers
    for (size_t workerID = 0; workerID < numThreads; workerID++) {
      wts[workerID] = thread(&ThreadPool::worker, this, workerID);
    }
}

size_t getAvailableWorker(){
    lock_guard lg(availableWorkerLock);
    for (size_t workerID = 0; workerID < numThreads ; workerID++){
        if (availableWorker[workerID]) {
            availableWorker[availableWorkerID] = 0;
            return workerID;
        }
    }
    return -1;
}

schedule(std::function<void(void)>& thunk) {
    lock_guard lg(thunkQueueLock);
    thunkQueue.push_back(thunk);
    nonEmptyQueue.notify_one();

    lock_guard lg(waitMutex);
    waitCounter++;
}

dispatcher() {
    while (true){
        queueLock.lock();
        nonEmptyQueue.wait();
        currentThunk = thunkQueue.dequeue();
        queueLock.unlock();

        workers.wait();
        if (destruct) break;

        size_t availableWorkerID = getAvailableWorker();
        assert (availableWorkerID >= 0);

        thunkLock.lock();
        thunk = currentThunk;
        thunkLock.unlock();

        // use semaphore to signal specific worker
        workerSemaphore[availableWorkerID].signal();
    }
}

worker(size_t workerID) {
    while(true) {
        workerSemaphore[workerID].wait();
        if (destruct) break;

        thunkLock.lock();
        currentThunk();
        thunkLock.unlock();

        availableWorkerLock.lock();
        availableWorker[workerID] = 1;
        availableWorkerLock.unlock();

        workers.signal();

        lock_guard lg(waitMutex);
        waitCounter--;
    }
}

wait() {
    lock_guard lg(waitMutex);
    cv.wait(waitMutex, [&waitCounter] {return waitCounter == 0});
}

~ThreadPool() {
    ThreadPool::wait();

    destruct = 1;
    
    // inform workers and dispatcher to exit
    for (auto & s : workerSemaphore) s.signal();
    workers.signal();

    // join all threads
    dt.join();
    for (auto& w : wts){
        w.join();
    }
}
