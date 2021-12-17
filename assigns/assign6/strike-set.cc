/**
 * File: strike-set.cc
 * -------------------
 * Presents the implementation of the StrikeSet class, which
 * manages a collection of regular expressions.  Each regular expressions
 * encodes a host aka server name that out proxy views as off limits.
 */

#include <fstream>
#include <iostream>
#include "strike-set.h"
using namespace std;

StrikeSet::StrikeSet() {
  // libstdc++ has a bug (#77704) that causes a data race in std::regex,
  // which we use in our implementation. The following code, which was
  // adapted from the #77704 bugzilla ticket, pre-initializes some
  // standard library global memory in order to avoid the race.
#if defined(__GLIBCXX__) || defined(__GLIBCPP__)
  const std::ctype<char>& ct = std::use_facet<std::ctype<char>>(std::locale());
  for (size_t i = 0; i < 256; i++) {
      ct.narrow(static_cast<char>(i), '\0');
  }
#endif
}

void StrikeSet::addFrom(const std::string& filename) {
  ifstream infile(filename.c_str());
  if (infile.fail()) {
    ostringstream oss;
    oss << "Filename \"" << filename << "\" of blocked domains could not be found.";
    throw HTTPProxyException(oss.str());
  }

  while (true) {
    string line;
    getline(infile, line);
    if (infile.fail()) break;
    regex re(line);
    blocked.push_back(re);
  }
}

bool StrikeSet::contains(const string& server) const {
  for (const regex& re: blocked) {
    if (regex_match(server, re)) {
      return true;
    }
  }

  return false;
}
