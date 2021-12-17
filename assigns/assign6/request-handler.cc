/**
 * File: request-handler.cc
 * ------------------------
 * Provides the implementation for the HTTPRequestHandler class.
 */

#include "request-handler.h"
#include "response.h"
#include "client-socket.h"
#include <socket++/sockstream.h> // for sockbuf, iosockstream
#include "ostreamlock.h"
#include "watchset.h"
using namespace std;

HTTPRequestHandler::HTTPRequestHandler() {
  mySet.addFrom("blocked-domains.txt");
  handlers["GET"] = &HTTPRequestHandler::handleDefaultRequest;
  handlers["POST"] = &HTTPRequestHandler::handleRequestNoCache;
  handlers["HEAD"] = &HTTPRequestHandler::handleRequestNoCache;
  handlers["CONNECT"] = &HTTPRequestHandler::handleSecureRequest;
}

static const string kDefaultProtocol = "HTTP/1.0";
void HTTPRequestHandler::serviceRequest(const pair<int, string>& connection) noexcept {
  sockbuf sb(connection.first);
  iosockstream ss(&sb);
  try {
    HTTPRequest request;
    request.ingestRequestLine(ss);
    if (mySet.contains(request.getServer())) {
      handleError(ss, kDefaultProtocol, HTTPStatus::Forbidden, "Forbidden Content");
      return;
    }
    request.ingestHeader(ss, connection.second);
    request.ingestPayload(ss);
    auto found = handlers.find(request.getMethod());
    if (found == handlers.cend()) {
      handleUnsupportedMethodError(ss, "Method Not Allowed");
      return;
    }
    (this->*(found->second))(request, ss);
  } catch (const HTTPBadRequestException &bre) {
    handleBadRequestError(ss, bre.what());
  } catch (const UnsupportedMethodExeption& ume) {
    handleUnsupportedMethodError(ss, ume.what());
  } catch (...) {}
}

void HTTPRequestHandler::handleDefaultRequest(const HTTPRequest& request, class iosockstream& ss) {
  HTTPResponse response;
  // lock the relevant mutex
  lock_guard<mutex> lg(myCache.findMutexFromHash(request));
  if (!(myCache.containsCacheEntry(request, response))){ 
    // request not in cache; fetch it 
    // (1) forward request to original server
    int client = createClientSocket(request.getServer(), request.getPort());
    if (client < 0) throw HTTPProxyException("Proxy failed to create client socket.");
    sockbuf sbServer(client);
    iosockstream ssServer(&sbServer);
    ssServer << request;
    ssServer.flush();
    // (2) digest original server's response
    response.ingestResponseHeader(ssServer);
    if (request.getMethod() != "HEAD") response.ingestPayload(ssServer);
    // (3) cache response
    if (myCache.shouldCache(request, response)) myCache.cacheEntry(request, response);
  }
  // forward response to original client
  ss << response;
  ss.flush();
}

void HTTPRequestHandler::handleRequestNoCache(const HTTPRequest& request, class iosockstream& ss) {
  HTTPResponse response;
  // forward request to original server
  int client = createClientSocket(request.getServer(), request.getPort());
  if (client < 0) throw HTTPProxyException("Proxy failed to create client socket.");
  sockbuf sbServer(client);
  iosockstream ssServer(&sbServer);
  ssServer << request;
  ssServer.flush();
  // digest original server's response
  response.ingestResponseHeader(ssServer);
  if (request.getMethod() != "HEAD") response.ingestPayload(ssServer);
  // forward response to original client
  ss << response;
  ss.flush();
}

static const string kNewProtocol = "HTTP/1.1";
void HTTPRequestHandler::handleSecureRequest(const HTTPRequest& request, class iosockstream& ss){
  HTTPResponse response;
  response.setResponseCode(HTTPStatus::OK);
  response.setProtocol(kNewProtocol);
  // response.setPayload("");
  ss << response;
  ss.flush();

  int client = createClientSocket(request.getServer(), request.getPort());
  if (client < 0) throw HTTPProxyException("Proxy failed to create client socket");
  sockbuf sbServer(client);
  iosockstream ssServer(&sbServer);
  manageClientServerBridge(ss, ssServer);
}

const size_t kTimeout = 5;
const size_t kBridgeBufferSize = 1 << 16;
void HTTPRequestHandler::manageClientServerBridge(iosockstream& client, iosockstream& server) {
  // get embedded descriptors leading to client and origin server
  int clientfd = client.rdbuf()->sd();
  int serverfd = server.rdbuf()->sd();

  // monitor both descriptors for any activity
  ProxyWatchset watchset(kTimeout);
  watchset.add(clientfd);
  watchset.add(serverfd);

  // map each descriptor to its surrounding iosockstream and the one
  // surrounding the descriptor on the other side of the bridge we're building
  map<int, pair<iosockstream *, iosockstream *>> streams;
  streams[clientfd] = make_pair(&client, &server);
  streams[serverfd] = make_pair(&server, &client);
  cout << oslock << buildTunnelString(client, server) << "Establishing HTTPS tunnel" << endl << osunlock;

  while (!streams.empty()) {
    int fd = watchset.wait();
    if (fd == -1) break; // return value of -1 means we timed out
    iosockstream& from = *streams[fd].first;
    iosockstream& to = *streams[fd].second;
    char buffer[kBridgeBufferSize];
    from.read(buffer, 1); // attempt to read one byte to see if we have one
    if (from.eof() || from.fail() || from.gcount() == 0) {
       // in here? that's because the watchset detected EOF instead of an unread byte
       watchset.remove(fd);
       streams.erase(fd);
       break;
    }
    to.write(buffer, 1);
    while(true){
      auto readSize = from.readsome(buffer, kBridgeBufferSize);
      if (from.eof() || from.fail()) { 
	 watchset.remove(fd); 
	 streams.erase(fd); 
	 break;
      }
      if (readSize == 0) break;
      to.write(buffer, readSize);
    }
    // source and transport them to the other side of the bridge
    to.flush();
  }
  cout << oslock << buildTunnelString(client, server) << "Tearing down HTTPS tunnel." << endl << osunlock;
}

string HTTPRequestHandler::buildTunnelString(iosockstream& from, iosockstream& to) const {
  return "[" + to_string(from.rdbuf()->sd()) + " --> " + to_string(to.rdbuf()->sd()) + "]: ";
}

/**
 * Responds to the client with code 400 and the supplied message.
 */
void HTTPRequestHandler::handleBadRequestError(iosockstream& ss, const string& message) const {
  handleError(ss, kDefaultProtocol, HTTPStatus::BadRequest, message);
}

/**
 * Responds to the client with code 405 and the provided message.
 */
void HTTPRequestHandler::handleUnsupportedMethodError(iosockstream& ss, const string& message) const {
  handleError(ss, kDefaultProtocol, HTTPStatus::MethodNotAllowed, message);
}

/**
 * Generic error handler used when our proxy server
 * needs to invent a response because of some error.
 */
void HTTPRequestHandler::handleError(iosockstream& ss, const string& protocol,
                                     HTTPStatus responseCode, const string& message) const {
  HTTPResponse response;
  response.setProtocol(protocol);
  response.setResponseCode(responseCode);
  response.setPayload(message);
  ss << response << flush;
}

// the following two methods needs to be completed 
// once you incorporate your HTTPCache into your HTTPRequestHandler
void HTTPRequestHandler::clearCache() {
  myCache.clear();
}

void HTTPRequestHandler::setCacheMaxAge(long maxAge) {
  myCache.setMaxAge(maxAge);
}
