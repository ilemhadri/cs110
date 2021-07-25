/**
 * File: request-handler.cc
 * ------------------------
 * Provides the implementation for the HTTPRequestHandler class.
 */

#include "request-handler.h"
#include "response.h"
#include <socket++/sockstream.h> // for sockbuf, iosockstream
using namespace std;

HTTPRequestHandler::HTTPRequestHandler() {
  handlers["GET"] = &HTTPRequestHandler::handleGETRequest;
  // add handlers for POST and HEAD as well
}

void HTTPRequestHandler::serviceRequest(const pair<int, string>& connection) throw() {
  sockbuf sb(connection.first);
  iosockstream ss(&sb);
  try {
    HTTPRequest request;
    request.ingestRequestLine(ss);
    request.ingestHeader(ss, connection.second);
    request.ingestPayload(ss);
    auto found = handlers.find(request.getMethod());
    if (found == handlers.cend()) throw UnsupportedMethodExeption(request.getMethod());
    (this->*(found->second))(request, ss);
  } catch (const HTTPBadRequestException &bre) {
    handleBadRequestError(ss, bre.what());
  } catch (const UnsupportedMethodExeption& ume) {
    handleUnsupportedMethodError(ss, ume.what());
  } catch (...) {}
}

static const string kDefaultProtocol = "HTTP/1.0";
void HTTPRequestHandler::handleGETRequest(const HTTPRequest& request, class iosockstream& ss) {
  HTTPResponse response;
  response.setResponseCode(200);
  response.setProtocol(kDefaultProtocol);
  response.setPayload("You're writing a proxy!");
  ss << response;
  ss.flush();
}

/**
 * Responds to the client with code 400 and the supplied message.
 */
void HTTPRequestHandler::handleBadRequestError(iosockstream& ss, const string& message) const {
  handleError(ss, kDefaultProtocol, 400, message);
}

/**
 * Responds to the client with code 405 and the provided message.
 */
void HTTPRequestHandler::handleUnsupportedMethodError(iosockstream& ss, const string& message) const {
  handleError(ss, kDefaultProtocol, 405, message);
}

/**
 * Generic error handler used when our proxy server
 * needs to invent a response because of some error.
 */
void HTTPRequestHandler::handleError(iosockstream& ss, const string& protocol,
				     int responseCode, const string& message) const {
  HTTPResponse response;
  response.setProtocol(protocol);
  response.setResponseCode(responseCode);
  response.setPayload(message);
  ss << response << flush;
}

// the following two methods needs to be completed 
// once you incorporate your HTTPCache into your HTTPRequestHandler
void HTTPRequestHandler::clearCache() {}
void HTTPRequestHandler::setCacheMaxAge(long maxAge) {}
