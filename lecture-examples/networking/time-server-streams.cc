/**
 * File: time-server-streams.cc
 * ----------------------------
 * Provided a sequential version of a server which
 * provides the simplest service possible--reporting
 * the time back to the client.  This first version
 * relies on raw socket descriptors and the write
 * system call to respond to the connecting client.
 */

#include <iostream>                // for cout, cett, endl
#include <ctime>                   // for time, gmtime, strftim
#include <sys/socket.h>            // for socket, bind, accept, listen, etc.
#include <climits>                 // for USHRT_MAX
#include "socket++/sockstream.h"   // for sockbuf, iosockstream
#include "server-socket.h"
using namespace std;

static const short kDefaultPort = 12345;
static const int kWrongArgumentCount = 1;
static const int kServerStartFailure = 2;
static void publishTime(int client) {
  time_t rawtime;
  time(&rawtime);
  struct tm *ptm = gmtime(&rawtime);
  char timestr[128]; // more than big enough
  /* size_t len = */ strftime(timestr, sizeof(timestr), "%c", ptm);
  sockbuf sb(client);
  iosockstream ss(&sb);
  ss << timestr << endl;
} // sockbuf destructor closes client

int main(int argc, char *argv[]) {
  if (argc > 1) {
    cerr << "Usage: " << argv[0] << endl;
    return kWrongArgumentCount;
  }
  
  int server = createServerSocket(kDefaultPort);
  if (server == kServerSocketFailure) {
    cerr << "Error: Could not start server on port " << kDefaultPort << "." << endl;
    cerr << "Aborting... " << endl;
    return kServerStartFailure;
  }
  
  cout << "Server listening on port " << kDefaultPort << "." << endl;
  while (true) {
    int client = accept(server, NULL, NULL);
    publishTime(client);
  }

  return 0;
}
