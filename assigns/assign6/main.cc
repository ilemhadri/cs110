/**
 * Provides a simple implementation of an http proxy and web cache.  
 * Save for the parsing of the command line, all bucks are passed
 * to an HTTPProxy proxy instance, which repeatedly loops and waits 
 * for proxied requests to come through.
 */

#include <iostream> // for cerr
#include <csignal>  // for sigprocmask, sigwait

#include "proxy.h"
#include "proxy-exception.h"
#include "ostreamlock.h"

using namespace std;

/**
 * Function: alertOfBrokenPipe
 * ---------------------------
 * Simple fault handler that occasionally gets invoked because
 * some pipe is broken.  We actually just print a short message but
 * otherwise allow execution to continue.
 */
static void alertOfBrokenPipe() {
  cerr << oslock << "Client closed socket.... aborting response."
       << endl << osunlock;
}

static sigset_t getSignals() {
  sigset_t signals;
  sigemptyset(&signals);
  sigaddset(&signals, SIGINT);
  sigaddset(&signals, SIGTSTP);
  sigaddset(&signals, SIGPIPE);
  return signals;
}

static void blockSignals() {
  sigset_t signals = getSignals();
  sigprocmask(SIG_BLOCK, &signals, NULL);
}

/**
 * Function: handleSignals
 * -----------------------
 * Configures the entire system to quit on ctrl-c and ctrl-z, and to handle
 * broken pipes
 */
static void handleSignals(function<void()> shutdownServer) {
  thread([=]{
    sigset_t signals = getSignals();
    while (true) {
      int received;
      sigwait(&signals, &received);
      if (received == SIGINT || received == SIGTSTP) {
        shutdownServer();
      } else if (received == SIGPIPE) {
        alertOfBrokenPipe();
      }
    }
  }).detach();
}

/**
 * Function: main
 * --------------
 * Defines the simple entry point to the entire proxy
 * application, which save for the configuration issues
 * passes the buck to an instance of the HTTPProxy class.
 */
static const int kFatalHTTPProxyError = 1;
int main(int argc, char *argv[]) {
  blockSignals();
  HTTPProxy proxy(argc, argv);
  handleSignals([&proxy]{
    proxy.stopServer();
  });
  try {
    cout << "Listening for all incoming traffic on port " << proxy.getPortNumber() << "." << endl;
    if (proxy.isUsingProxy()) {
      cout << "Requests will be directed toward another proxy at " 
           << proxy.getProxyServer() << ":" << proxy.getProxyPortNumber() << "." << endl;
    }
    proxy.runServer();
  } catch (const HTTPProxyException& hpe) {
    cerr << "Fatal Error: " << hpe.what() << endl;
    cerr << "Exiting..... " << endl;
    return kFatalHTTPProxyError;
  }
  
  return 0;
}
