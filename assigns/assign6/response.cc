/**
 * File: response.cc
 * -----------------
 * Presents the implementation of the HTTPResponse class.
 */

#include "response.h"

#include <sstream>
#include <cstring>
#include "proxy-exception.h"
#include "string-utils.h"
using namespace std;

const map<HTTPStatus, std::string> HTTPResponse::kStatusMessages = {
    {HTTPStatus::Continue, "Continue"},
    {HTTPStatus::SwitchingProtocols, "Switching Protocols"},
    {HTTPStatus::OK, "OK"},
    {HTTPStatus::Created, "Created"},
    {HTTPStatus::Accepted, "Accepted"},
    {HTTPStatus::NonAuthoritativeInformation, "Non-Authoritative Information"},
    {HTTPStatus::NoContent, "No Content"},
    {HTTPStatus::ResetContent, "Reset Content"},
    {HTTPStatus::PartialContent, "Partial Content"},
    {HTTPStatus::MultipleChoices, "Multiple Choices"},
    {HTTPStatus::PermanentlyMoved, "Permanently Moved"},
    {HTTPStatus::Found, "Found"},
    {HTTPStatus::SeeOther, "See Other"},
    {HTTPStatus::NotModified, "Not Modified"},
    {HTTPStatus::UseProxy, "Use Proxy"},
    {HTTPStatus::TemporaryRedirect, "Temporary Redirect"},
    {HTTPStatus::BadRequest, "Bad Request"},
    {HTTPStatus::Unauthorized, "Unauthorized"},
    {HTTPStatus::PaymentRequired, "Payment Required"},
    {HTTPStatus::Forbidden, "Forbidden"},
    {HTTPStatus::NotFound, "Not Found"},
    {HTTPStatus::MethodNotAllowed, "Method Not Allowed"},
    {HTTPStatus::NotAcceptable, "Not Acceptable"},
    {HTTPStatus::ProxyAuthenticationRequired, "Proxy Authentication Required"},
    {HTTPStatus::RequestTimeout, "Request Timeout"},
    {HTTPStatus::Conflict, "Conflict"},
    {HTTPStatus::Gone, "Gone"},
    {HTTPStatus::InternalServerError, "Internal Server Error"},
    {HTTPStatus::NotImplemented, "Not Implemented"},
    {HTTPStatus::BadGateway, "Bad Gateway"},
    {HTTPStatus::GatewayTimeout, "Gateway Timeout"},
    {HTTPStatus::HTTPVersionNotSupported, "HTTP Version Not Supported"},
    {HTTPStatus::GeneralProxyFailure, "General Proxy Failure"},
};

void HTTPResponse::ingestResponseHeader(istream& instream) {
  string responseCodeLine;
  getline(instream, responseCodeLine);
  istringstream iss(responseCodeLine);
  string protocol;
  iss >> protocol;
  setProtocol(protocol);
  int code;
  iss >> code;
  setResponseCode(code);
  responseHeader.ingestHeader(instream);
}

void HTTPResponse::ingestPayload(std::istream& instream) {
  payload.ingestPayload(responseHeader, instream);
}

void HTTPResponse::setProtocol(const string& protocol) {
  this->protocol = protocol;
}

void HTTPResponse::setResponseCode(int code) {
  this->code = code;
}

void HTTPResponse::setResponseCode(HTTPStatus code) {
  this->code = static_cast<int>(code);
}

HTTPStatus HTTPResponse::getResponseCode() const {
  if (kStatusMessages.contains(static_cast<HTTPStatus>(code))) {
    return static_cast<HTTPStatus>(code);
  }
  return HTTPStatus::UnknownStatus;
}

void HTTPResponse::addHeader(const std::string& name, const std::string& value) {
  responseHeader.addHeader(name, value);
}

void HTTPResponse::setPayload(const string& payload) {
  this->payload.setPayload(responseHeader, payload);
}

bool HTTPResponse::permitsCaching() const {
  if (!responseHeader.containsName("Cache-Control")) return false;
  const string& cacheControlValue = responseHeader.getValueAsString("Cache-Control");
  if (cacheControlValue.find("private") != string::npos) return false;
  if (cacheControlValue.find("no-cache") != string::npos) return false;
  if (cacheControlValue.find("no-store") != string::npos) return false;
  return getTTL() > 0;
}

int HTTPResponse::getTTL() const {
  if (!responseHeader.containsName("Cache-Control")) return 0;
  const string& cacheControlValue = responseHeader.getValueAsString("Cache-Control");
  size_t pos = cacheControlValue.find("max-age=");
  if (pos == string::npos) return 0;
  string maxAgeValue = cacheControlValue.substr(pos + strlen("max-age="));
  istringstream iss(maxAgeValue);
  int maxAge;
  iss >> maxAge;
  return maxAge;
}

ostream& operator<<(ostream& os, const HTTPResponse& hr) {
  os << hr.protocol << " " << hr.code << " " 
     << hr.getStatusMessage() << "\r\n";
  os << hr.responseHeader;
  os << "\r\n"; // blank line not printed by response header
  os << hr.payload;
  return os;
}

std::string HTTPResponse::getStatusMessage() const {
  if (getResponseCode() == HTTPStatus::UnknownStatus) {
    return "Unknown Code";
  }
  return kStatusMessages.at(getResponseCode());
}
