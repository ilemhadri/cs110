/**
 * File: html-document.h
 * ---------------------
 * Encapsulates the information needed to represent
 * a single HTML document.  While it could be simpilified
 * quite a bit, it's optimized to pull and parse the content
 * of an HTML document's body tag.
 */

#pragma once
#include <string>
#include <vector>
#include "html-document-exception.h"

class HTMLDocument {
 public:

/**
 * Constructor: HTMLDocument
 * Usage: HTMLDocument profile("http://www.facebook.com/jerry");
 *        HTMLDocument signin("https://login.stanford.edu");
 * -------------------------
 * Constructs an HTMLDocument instance around the specified URL.
 */
  HTMLDocument(const std::string& url) : url(url), urlNormalized(normalize(url)) {}

/**
 * Method: parse
 * Usage: htmlDoc.parse();
 * -----------------------
 * Connects to the relevant server housing the document at the encapsulated
 * URL, pulls the document content, and tokenizes it so that getTokens() works
 * as expected.
 *
 * If any problems are encountered, an HTMLDocumentException is thrown.
 */
  void parse();

/**
 * Method: getURL
 * cout << htmlDoc.getURL() << endl;
 * ---------------------------------
 * Returns a const reference to the encapsulated URL (expressed as a C++ string).
 */
  const std::string& getURL() const { return url; }

/**
 * Method: getTokens
 * const vector<string>& tokens = htmlDoc.getTokens();
 * ---------------------------------------------------
 * Returns a const reference to the encapsulated vector of tokens making
 * up the content of the document.
 */
  const std::vector<std::string>& getTokens() const { return tokens; }
  
 private:
  std::string url;
  std::string urlNormalized;
  std::vector<std::string> tokens;

  std::string download(size_t numRedirectsAllowed = 10);
  void parse(const std::string& contents);
  void extractTokens(struct myhtml_tree *tree);
  void removeNodes(struct myhtml_tree *tree, const std::string& tagName);
  static std::string normalize(const std::string& url);
  
/**
 * The following two lines delete the default implementations you'd
 * otherwise get for the copy constructor and operator=.  Because the implementation
 * of parse() involves networking code, it's not clear what the semantics of a
 * deep copy really should be.  By deleting these two items, we force all clients
 * of the HTMLDocument class to pass instances around by reference or by address.
 */
  HTMLDocument(const HTMLDocument& other) = delete;
  void operator=(const HTMLDocument& rhs) = delete;
};
