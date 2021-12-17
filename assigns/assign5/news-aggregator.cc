/**
 * File: news-aggregator.cc
 * --------------------------------
 * Presents the implementation of the NewsAggregator class.
 */

#include "news-aggregator.h"
#include <iostream>
#include <iomanip>
#include <memory>
#include <thread>
#include <iostream>
#include <algorithm>
#include <thread>
#include <utility>

#include <getopt.h>
#include <libxml/parser.h>
#include <libxml/catalog.h>
#include "rss-feed.h"
#include "rss-feed-list.h"
#include "html-document.h"
#include "html-document-exception.h"
#include "rss-feed-exception.h"
#include "rss-feed-list-exception.h"
#include "utils.h"
#include "ostreamlock.h"
#include "string-utils.h"
using namespace std;

/**
 * Factory Method: createNewsAggregator
 * ------------------------------------
 * Factory method that spends most of its energy parsing the argument vector
 * to decide what RSS feed list to process and whether to print lots of
 * of logging information as it does so.
 */
static const string kDefaultRSSFeedListURL = "small-feed.xml";
NewsAggregator *NewsAggregator::createNewsAggregator(int argc, char *argv[]) {
  struct option options[] = {
    {"verbose", no_argument, NULL, 'v'},
    {"quiet", no_argument, NULL, 'q'},
    {"url", required_argument, NULL, 'u'},
    {NULL, 0, NULL, 0},
  };

  string rssFeedListURI = kDefaultRSSFeedListURL;
  bool verbose = true;
  while (true) {
    int ch = getopt_long(argc, argv, "vqu:", options, NULL);
    if (ch == -1) break;
    switch (ch) {
      case 'v':
        verbose = true;
        break;
      case 'q':
        verbose = false;
        break;
      case 'u':
        rssFeedListURI = optarg;
        break;
      default:
        NewsAggregatorLog::printUsage("Unrecognized flag.", argv[0]);
    }
  }

  argc -= optind;
  if (argc > 0) NewsAggregatorLog::printUsage("Too many arguments.", argv[0]);
  return new NewsAggregator(rssFeedListURI, verbose);
}

/**
 * Method: buildIndex
 * ------------------
 * Initalize the XML parser, processes all feeds, and then
 * cleans up the parser.  The lion's share of the work is passed
 * on to processAllFeeds, which you will need to implement.
 */
void NewsAggregator::buildIndex() {
  if (built) return;
  built = true; // optimistically assume it'll all work out
  xmlInitParser();
  xmlInitializeCatalog();
  processAllFeeds();
  xmlCatalogCleanup();
  xmlCleanupParser();
}

/**
 * Method: queryIndex
 * ------------------
 * Interacts with the user via a custom command line, allowing
 * the user to surface all of the news articles that contains a particular
 * search term.
 */
void NewsAggregator::queryIndex() const {
  static const size_t kMaxMatchesToShow = 15;
  while (true) {
    cout << "Enter a search term [or just hit <enter> to quit]: ";
    string response;
    getline(cin, response);
    response = trim(response);
    if (response.empty()) break;
    const vector<pair<Article, int> >& matches = index.getMatchingArticles(response);
    if (matches.empty()) {
      cout << "Ah, we didn't find the term \"" << response << "\". Try again." << endl;
    } else {
      cout << "That term appears in " << matches.size() << " article"
        << (matches.size() == 1 ? "" : "s") << ".  ";
      if (matches.size() > kMaxMatchesToShow)
        cout << "Here are the top " << kMaxMatchesToShow << " of them:" << endl;
      else if (matches.size() > 1)
        cout << "Here they are:" << endl;
      else
        cout << "Here it is:" << endl;
      size_t count = 0;
      for (const pair<Article, int>& match: matches) {
        if (count == kMaxMatchesToShow) break;
        count++;
        string title = match.first.title;
        if (shouldTruncate(title)) title = truncate(title);
        string url = match.first.url;
        if (shouldTruncate(url)) url = truncate(url);
        string times = match.second == 1 ? "time" : "times";
        cout << "  " << setw(2) << setfill(' ') << count << ".) "
          << "\"" << title << "\" [appears " << match.second << " " << times << "]." << endl;
        cout << "       \"" << url << "\"" << endl;
      }
    }
  }
}

/**
 * Private Constructor: NewsAggregator
 * -----------------------------------
 * Self-explanatory.
 */
static const size_t kNumFeedWorkers = 10;
static const size_t kNumArticleWorkers = 50;
NewsAggregator::NewsAggregator(const string& rssFeedListURI, bool verbose): 
  log(verbose), rssFeedListURI(rssFeedListURI), built(false), feedPool(kNumFeedWorkers), articlePool(kNumArticleWorkers) {}

  bool downloadArticle(const string& articleUrl, std::set<std::string>& urlSet, mutex& urlSetLock) {
    lock_guard urlSetLg(urlSetLock); // ADDED THIS
    // existing URL; skip
    if (urlSet.count(articleUrl)) return false;
    // new URL; process
    urlSet.insert(articleUrl);
    return true;
  }


/**
 * Private Method: processAllFeeds
 * -------------------------------
 * The provided code (commented out, but it compiles) illustrates how one can
 * programmatically drill down through an RSSFeedList to arrive at a collection
 * of RSSFeeds, each of which can be used to fetch the series of articles in that feed.
 *
 * You'll want to erase much of the code below and ultimately replace it with
 * your multithreaded aggregator.  It's only being presented to make the APIs of
 * all of the support classes as clear as possible.
 */
void NewsAggregator::processAllFeeds() {
  RSSFeedList feedList(rssFeedListURI);
  try {
    feedList.parse();
  } catch (const RSSFeedListException& rfle) {
    log.noteFullRSSFeedListDownloadFailureAndExit(rssFeedListURI);
  }

  const map<string, string>& feeds = feedList.getFeeds();
  if (feeds.empty()) {
    return;
  }

  for (map<string, string>::const_iterator myFeed = feeds.begin(); myFeed != feeds.end(); myFeed++){
    const string& feedUrl = myFeed->first;
    feedPool.schedule([this, &feedUrl]() {
        RSSFeed feed(feedUrl);
        try {
        feed.parse();
        } catch (const RSSFeedException& rfe) {
        log.noteSingleFeedDownloadFailure(feedUrl);
        return;
        }

        const vector<Article>& articles = feed.getArticles();
        if (articles.empty()) {
        return;
        }

        for (auto& article: articles){
        articlePool.schedule([this, article]() {
            const string& articleTitle = article.title;
            const string& articleUrl = article.url;
            bool articleDownloaded = downloadArticle(articleUrl, urlSet, urlSetLock);
            if (!articleDownloaded) return;
            HTMLDocument document(articleUrl);
            try {
            document.parse();
            } catch (const HTMLDocumentException& hde) {
            log.noteSingleArticleDownloadFailure(article);
            return;
            }
            const string& subdomain = getURLServer(article.url);
            pair<const string, const string> keyPair = make_pair(subdomain, articleTitle);
            vector<string> tokens = document.getTokens();
            sort(tokens.begin(), tokens.end());

            lock_guard articleMaplg(articleMapLock);
            if (articleMap.count(keyPair) == 0){
            // keyPair does not exist; add it
            articleMap[keyPair] = make_pair(article, tokens);
            }
            else {
              // keyPair already exists; keep first article and intersect tokens
              Article smallestArticle = min(articleMap.at(keyPair).first, article);
              const vector<string>& existingTokens = articleMap.at(keyPair).second;
              vector<string> intersectionTokens;
              set_intersection(existingTokens.cbegin(), existingTokens.cend(), tokens.cbegin(), tokens.cend(), back_inserter(intersectionTokens));
              articleMap[keyPair] = make_pair(smallestArticle, intersectionTokens);
            }
        });
        }
    });
  }
  feedPool.wait();
  articlePool.wait();
  // add (smallestArticle,tokenIntersection) to index
  for (const auto & [keyPair, valuePair] : articleMap) index.add(valuePair.first, valuePair.second);
}
