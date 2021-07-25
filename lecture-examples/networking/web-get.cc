/**
 * File: web-get.cc
 * ----------------
 * This file provides a straightforward client application
 * imitating the functionality of the wget built-in, which
 * pulls the remote document whose URL is specified via the
 * program's only argument.
 *
 * This program doesn't do as much aggressive error checking as
 * it could, because I want the example to focus on the use of
 * socket, gethostbyname, htons, and connect to show you
 * the networking code needed to attach a file descriptor to one
 * end of a bidirectional conversation with a service on another
 * machine.
 */

#include <iostream>               // for cout, cerr, cout
#include <string>                 // for string
#include <fstream>                // for ofstream
#include "socket++/sockstream.h"  // for sockbuf, iosockstream
#include "client-socket.h"        // for createClientSocket
#include "string-utils.h"         // for startsWith
using namespace std;

static const int kWrongArgumentCount = 1;

/**
 * With only a modicum of sanity and error checking,
 * the following function accept a string, assumed to be
 * a valid URL (possibly with a leading "http://") and returns
 * the host and path components (e.g. "www.google.com" and
 * "index.html") using a pair<string, string>.
 * If there is no path component (as from "http://www.facebook.com"),
 * then the second half is populated with a default path of "/".
 */

static const string kProtocolPrefix = "http://";
static const string kDefaultPath = "/";
static pair<string, string> parseURL(string url) {
  if (startsWith(url, kProtocolPrefix)) 
    url = url.substr(kProtocolPrefix.size());
  size_t found = url.find('/');
  if (found == string::npos) 
    return make_pair(url, kDefaultPath);
  string host = url.substr(0, found);
  string path = url.substr(found);
  return make_pair(host, path);
}

static void issueRequest(iosockstream& ss, const string& host, const string& path) {
  ss << "GET " << path << " HTTP/1.0\r\n";
  ss << "Host: " << host << "\r\n";
  ss << "\r\n";
  ss.flush();
}

static void skipHeader(iosockstream& ss) {
  string line;
  do {
    getline(ss, line);
  } while (!line.empty() && line != "\r");
}

static string getFileName(const string& path) {
  if (path.empty() || path[path.size() - 1] == '/') return "index.html";
  size_t found = path.rfind('/');
  return path.substr(found + 1);
}

static const size_t kBufferSize = 1024;
static void savePayload(iosockstream& ss, const string& filename) {
  ofstream output(filename, ios::binary); // don't assume it's text
  size_t totalBytes = 0;
  while (!ss.fail()) {
    char buffer[kBufferSize] = {'\0'};
    ss.read(buffer, sizeof(buffer));
    totalBytes += ss.gcount();
    output.write(buffer, ss.gcount());
  }
  cout << "Total number of bytes fetched: " << totalBytes << endl;
}

static const unsigned short kDefaultHTTPPort = 80;
static void pullContent(const pair<string, string>& components) {
  int client = createClientSocket(components.first, kDefaultHTTPPort);
  if (client == kClientSocketError) {
    cerr << "Count not connect to host named \"" 
	 << components.first << "\"." << endl;
    return;
  }

  sockbuf sb(client);
  iosockstream ss(&sb);
  issueRequest(ss, components.first, components.second);
  skipHeader(ss);
  savePayload(ss, getFileName(components.second));
}

int main(int argc, char *argv[]) {
  if (argc != 2) {
    cerr << "Usage: " << argv[0] << " <url>" << endl;
    return kWrongArgumentCount;
  }
  
  pullContent(parseURL(argv[1]));
  return 0;
}
