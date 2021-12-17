/**
 * File: mapreduce-server.h
 * ------------------------
 * Models the master node in the entire MapReduce
 * system.
 */

#pragma once
#include <cstdlib>
#include <string>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <set>
#include <vector>
#include <map>
#include "mapreduce-server-exception.h"

class MapReduceServer {
 public:
  MapReduceServer(int argc, char **argv);
  ~MapReduceServer() noexcept;
  void run() noexcept;
  
 private:
  unsigned short computeDefaultPortForUser() const noexcept;
  void parseArgumentList(int argc, char *argv[]) noexcept(false);
  void initializeFromConfigFile(const std::string& configFileName) noexcept(false);
  void confirmRequiredArgumentsArePresent(const std::string& configFilename) const noexcept(false);
  void confirmExecutablesAreExecutable() const noexcept(false);
  void applyToServer(const std::string& key, const std::string& value) noexcept(false);
  void buildIPAddressMap() noexcept;
  std::vector<std::string> listFiles(const std::string& directory) const noexcept;
  void startServer() noexcept(false);
  void logServerConfiguration(std::ostream& os) noexcept;
  void orchestrateWorkers() noexcept;
  void handleRequest(int clientSocket, const std::string& clientIPAddress) noexcept;
  void spawnMappers() noexcept;
  void spawnWorker(const std::string& node, const std::string& command) const noexcept;

  std::string buildMapperCommand(const std::string& remoteHost,
                                 const std::string& executable, 
                                 const std::string& outputPath) noexcept;
                                  
  bool getNextFilePattern(std::string& pattern) noexcept;
  void markFilePatternAsProcessed(const std::string& clientIPAddress, const std::string& pattern) noexcept;
  void rescheduleFilePattern(const std::string& clientIPAddress, const std::string& pattern) noexcept;

  void dumpFileHashes(const std::string& dir) noexcept;
  void dumpFileHash(const std::string& file) noexcept;
  void bringDownServer() noexcept;

  std::string user;
  std::string host;
  std::string cwd;
  
  int serverSocket;
  unsigned short serverPort;
  bool verbose, mapOnly;
  size_t numMappers;
  size_t numReducers;
  std::string mapper;
  std::string reducer;
  std::string inputPath;
  std::string intermediatePath;
  std::string outputPath;
  std::string mapperExecutable;
  std::string reducerExecutable;
  
  std::vector<std::string> nodes;
  std::map<std::string, std::string> ipAddressMap;
  std::atomic<bool> serverIsRunning;
  std::thread serverThread;
  
  std::queue<std::string> unprocessed;
  std::set<std::string> inflight;
  
  MapReduceServer(const MapReduceServer& original) = delete;
  MapReduceServer& operator=(const MapReduceServer& rhs) = delete;
};
