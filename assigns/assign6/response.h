/**
 * File: response.h
 * ----------------
 * Presents the interface for an HTTPResponse class, which
 * helps to manage everything associated with the response of
 * an HTTP request.
 */

#ifndef _http_response_
#define _http_response_

#include <istream>
#include <ostream>
#include <string>
#include <vector>
#include <map>

#include "header.h"
#include "payload.h"

enum class HTTPStatus {
  Continue = 100,
  SwitchingProtocols = 101,
  OK = 200,
  Created = 201,
  Accepted = 202,
  NonAuthoritativeInformation = 203,
  NoContent = 204,
  ResetContent = 205,
  PartialContent = 206,
  MultipleChoices = 300,
  PermanentlyMoved = 301,
  Found = 302,
  SeeOther = 303,
  NotModified = 304,
  UseProxy = 305,
  TemporaryRedirect = 307,
  BadRequest = 400,
  Unauthorized = 401,
  PaymentRequired = 402,
  Forbidden = 403,
  NotFound = 404,
  MethodNotAllowed = 405,
  NotAcceptable = 406,
  ProxyAuthenticationRequired = 407,
  RequestTimeout = 408,
  Conflict = 409,
  Gone = 410,
  InternalServerError = 500,
  NotImplemented = 501,
  BadGateway = 502,
  GatewayTimeout = 504,
  HTTPVersionNotSupported = 505,
  GeneralProxyFailure = 510,
  UnknownStatus,
};

class HTTPResponse {

/**
 * Publishes the entire HTTPResponse to the specified
 * ostream, and returns a reference to the ostream so that
 * operator<< can be daisy-chained as it can be with all other types.
 */

  friend std::ostream& operator<<(std::ostream& os, const HTTPResponse& hr);
  
 public:

  /**
   * Ingests everything up through and including the first
   * blank line of the server's response to an HTTP request.
   */

  void ingestResponseHeader(std::istream& instream);

  /**
   * Ingests the payload portion of the server's response
   * to an HTTP request.
   */

  void ingestPayload(std::istream& instream);

  /**
   * Sets the protocol to be the one specified.  The
   * protocol should be "HTTP/1.0" or "HTTP/1.1".
   */

  void setProtocol(const std::string& protocol);

  /**
   * Returns the current protocol associated 
   * with the response.
   */

  const std::string& getProtocol() const { return protocol; }

  /**
   * Installs the provided response code into the receiving
   * HTTPResponse object.
   */

  void setResponseCode(int code);
  void setResponseCode(HTTPStatus code);

  /**
   * Retrieves the response code associated with the
   * HTTPResponse.
   */

  HTTPStatus getResponseCode() const;

  /**
   * Adds the specified key-value pair to the response
   * header.
   */
  void addHeader(const std::string& name, const std::string& value);

  /**
   * Manually updates the payload to be the provided
   * string (and updates the response header to be
   * clear about the content length as well).
   */

  void setPayload(const std::string& payload);

  /**
   * Returns true if and only if the HTTPResponse is
   * cachable and can be returned as is when the same
   * exact request comes through later on.
   */

  bool permitsCaching() const;

  /**
   * Returns the time-to-live, which is the number
   * of remaining seconds for which a cacheable object 
   * is still valid.
   */

  int getTTL() const;
  
 private:
  int code;
  std::string protocol;
  HTTPHeader responseHeader;
  HTTPPayload payload;
  
  static const std::map<HTTPStatus, std::string> kStatusMessages;
  std::string getStatusMessage() const;
};

#endif
