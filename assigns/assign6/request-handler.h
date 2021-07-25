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

class HTTPRequestHandler {
 public:
  HTTPRequestHandler();
  void serviceRequest(const std::pair<int, std::string>& connection) throw();
  void clearCache();
  void setCacheMaxAge(long maxAge);

 private:
  typedef void (HTTPRequestHandler::*handlerMethod)(const HTTPRequest& request, class iosockstream& ss);
  std::map<std::string, handlerMethod> handlers;

  void handleGETRequest(const HTTPRequest& request, class iosockstream& ss);
  
  void handleBadRequestError(class iosockstream& ss, const std::string& message) const;
  void handleUnsupportedMethodError(class iosockstream& ss, const std::string& message) const;
  void handleError(class iosockstream& ss, const std::string& protocol,
                   int responseCode, const std::string& message) const;
};

#endif
