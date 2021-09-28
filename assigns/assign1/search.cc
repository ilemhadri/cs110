#include <sstream>
#include <vector>
#include <list>
#include <set>
#include <unordered_set>
#include <string>
#include <iostream>
#include <iomanip>
#include <functional>
#include "imdb.h"
#include "imdb-utils.h"
#include "path.h"
using namespace std;

static const int kWrongArgumentCount = 1;
static const int kAdditionalArgumentIncorrect = 2;
static const int kDatabaseNotFound = 3;

/**
 * Serves as the main entry point for the six-degrees executable.
 */
static const size_t kMaxDegreeOfSeparation = 6;
int main(int argc, char *argv[]) {
  size_t maxLength = kMaxDegreeOfSeparation;
  if (argc != 3 && argc != 4) {
    cout << "Usage: " << argv[0] << " <source-actor> <target-actor> [<max-path-length>]" << endl;
    return kWrongArgumentCount;
  }
  if (argc == 4) {
    try {
      maxLength = stoi(argv[3]);
    } catch (const exception& e) {
      cout << "Optional path length argument either malformed or too large a number." << endl;
      return kAdditionalArgumentIncorrect;
    }
    if (maxLength < 1 || maxLength > kMaxDegreeOfSeparation) {
      cout << "Optional path length argument must be non-negative and less than or equal to "
           << kMaxDegreeOfSeparation << "." << endl;
      return kAdditionalArgumentIncorrect;      
    }
  }
  
  imdb db(kIMDBDataDirectory);
  if (!db.good()) {
    cout << "Failed to properly initialize the imdb database." << endl;
    cout << "Please check to make sure the source files exist and that you have permission to read them." << endl;
    return kDatabaseNotFound;
  }
  
  string source = argv[1];
  string target = argv[2];
  if (source == target) {
    cout << "Ensure that source and target actors are different!" << endl;
  } else {
    vector<film> films = {};

    /* reverse source and target if it improves search efficiency */
    bool reverse = false;
    films.clear();
    db.getCredits(source, films);
    size_t numSource = films.size();
    db.getCredits(target, films);
    size_t numTarget = films.size();
    if (numSource > numTarget) {reverse = true; source = argv[2]; target = argv[1];};

    /* declare initial variables */
    set<string> visitedActors = {source};
    set<film> visitedMovies = {};
    path initialPath(source);
    list<path> pathsList = {initialPath};
    vector<string> players;
    path foundPath(source);
    bool found = false;

    /* run BFS */
    while (!found and !pathsList.empty()){
        path currPath = pathsList.front();
        pathsList.pop_front();
        string currPlayer = currPath.getLastPlayer();
        visitedActors.insert(currPlayer);

        /* # path is too long; can't explore it further */
        if (currPath.getLength() == maxLength) break;

        db.getCredits(currPlayer, films);
        for (const film& f: films) {
            /* # already explored this film; skip it */
            auto findMovie = visitedMovies.find(f);
            if (findMovie != visitedMovies.end()) continue;

            /* # never explored this film; mark and explore it */
            visitedMovies.insert(f);
            db.getCast(f, players);

            for (const string& player: players){
                /* # already explored this player; skip it */
                auto findActor = visitedActors.find(player);
                if (findActor != visitedActors.end()) continue;

                /* # never explored this player; */
                /* # mark and explore */
                visitedActors.insert(player);
                /* # remove any connection due to previous player in for loop */
                if (currPath.getLastPlayer() != currPlayer) currPath.undoConnection();

                currPath.addConnection(f, player);
                /* # found player; break and terminate search */
                if (player == target) {found = true; foundPath = currPath; break;}
                /* # add new path to queue */
                pathsList.push_back(currPath);
            }
            if (found) 
                break;
        }
    }

  /* # found path between source and target */
  if (found){
      if (reverse) foundPath.reverse();
      cout << foundPath << endl;
  }
  
  /* # no path found */
  else cout << "No path between those two people could be found." << endl;
  }

  return 0;
}
