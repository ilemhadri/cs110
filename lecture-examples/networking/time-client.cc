/**
 * File: time-client.cc
 * --------------------
 * Implements a trivially small program that assumes a time server is running on myth64.stanford.edu:12345.
 */

#include <iostream>
#include "client-socket.h"
#include "socket++/sockstream.h"
using namespace std;

static const int kTimeServerInaccessible = 1;
int main(int argc, char *argv[]) {
  if (argc < 3) {
      cout << "Usage:\n\t" << argv[0] << " server port" << endl;
      cout << "e.g.,\n\t" << argv[0] << " myth61.stanford.edu 12345" << endl;
          
      return 0;
  }
  //int client = createClientSocket("myth61.stanford.edu", 12345);
  int client = createClientSocket(argv[1], atoi(argv[2]));
  if (client == kClientSocketError) {
    cerr << "Time server could not be reached" << endl;
    cerr << "Aborting" << endl;
    return kTimeServerInaccessible;
  }

  sockbuf sb(client);
  iosockstream ss(&sb);
  string timeline;
  getline(ss, timeline);
  cout << timeline << endl;
  return 0;
}
