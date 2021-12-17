/**
 * File: request-handler.h
 * -----------------------
 * Defines the HTTPRequestHandler class, which fully proxies and
 * services a single client request.  
 */

#ifndef _request_handler_
#define _request_handler_

#include <utility>
#include <string>
#include <map>
#include "request.h"
#include "response.h"
#include "strike-set.h"
#include "cache.h"

class HTTPRequestHandler {
 public:
  HTTPRequestHandler();
  void serviceRequest(const std::pair<int, std::string>& connection) noexcept;
  void clearCache();
  void setCacheMaxAge(long maxAge);

 private:
  typedef void (HTTPRequestHandler::*handlerMethod)(const HTTPRequest& request, class iosockstream& ss);
  std::map<std::string, handlerMethod> handlers;
  StrikeSet mySet;
  HTTPCache myCache;

  void manageClientServerBridge(iosockstream& client, iosockstream& server);
  std::string buildTunnelString(iosockstream& from, iosockstream& to) const;

  void handleBadRequestError(class iosockstream& ss, const std::string& message) const;
  void handleUnsupportedMethodError(class iosockstream& ss, const std::string& message) const;
  void handleError(class iosockstream& ss, const std::string& protocol,
                   HTTPStatus responseCode, const std::string& message) const;

  // added this for Milestone 1
  void handleDefaultRequest(const HTTPRequest& request, class iosockstream& ss);
  // define a separate method for handling POST and HEAD requests, since they don't involve the cache (to avoid read timeouts)
  void handleRequestNoCache(const HTTPRequest& request, class iosockstream& ss);

  // added this for Milestone 4
  void handleSecureRequest(const HTTPRequest& request, class iosockstream& ss);
};

#endif
