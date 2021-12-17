/**
 * File: strike-set.h
 * ------------------
 * Defines a class that helps identify hosts
 * that should be blocked out by our proxy.
 */

#pragma once
#include <vector>
#include <string>
#include <regex>
#include "proxy-exception.h"

class StrikeSet {

 public:

   StrikeSet();

/**
 * Method: addFrom
 * ---------------
 * Add the list of of blocked domain patterns within the specified
 * file to the blocked set.  The file contents should be
 * a list of regular expressions--one per line--describing
 * a class of server strings that should be blocked.
 *
 * The file might, for instance, look like this:
 * 
 *   (.*)\.berkeley.edu
 *   (.*)\.bing.com
 *   (.*)\.microsoft.com
 *   (.*)\.org
 *
 * If there's any drama (e.g. the file doesn't exist), then an
 * HTTPProxyException is thrown.
 */
  void addFrom(const std::string& filename);

/**
 * Method: contains
 * ----------------
 * Returns true if the specified server (e.g. `web.stanford.edu`) is blocked,
 * or false if access to that server should be permitted.
 */
  bool contains(const std::string& server) const;

 private:
  std::vector<std::regex> blocked;
};
