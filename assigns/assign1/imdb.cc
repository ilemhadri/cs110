#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include "imdb.h"
using namespace std;
#include <string.h>
#include <algorithm>

const char *const imdb::kActorFileName = "actordata";
const char *const imdb::kMovieFileName = "moviedata";
imdb::imdb(const string& directory) {
  const string actorFileName = directory + "/" + kActorFileName;
  const string movieFileName = directory + "/" + kMovieFileName;  
  actorFile = acquireFileMap(actorFileName, actorInfo);
  movieFile = acquireFileMap(movieFileName, movieInfo);
}

bool imdb::good() const {
  return !( (actorInfo.fd == -1) || 
	    (movieInfo.fd == -1) ); 
}

imdb::~imdb() {
  releaseFileMap(actorInfo);
  releaseFileMap(movieInfo);
}


bool imdb::compareActorAtOffset(int offset, const std::string& player) const {
    const char * playerAtOffset = (const char *) actorFile + offset;
    return strcmp(playerAtOffset, player.c_str()) < 0;
}


bool imdb::getCredits(const string& player, vector<film>& films) const {
  /* clear the vector */
  films.clear();

  /* find the player's offset in actorFile */
  const int *countp = (const int *) actorFile;
  const int *begin = (const int *) actorFile + 1;
  const int *end = begin + *countp;
  const int *found = lower_bound(begin, end, player, [this](int offset, const string& player) {
          return compareActorAtOffset(offset, player);
  });
  /* check that the player exists in actorFile */
  const char * playerFound = (const char *)actorFile + *found;
  const int match = strcmp(playerFound, player.c_str());

  /* player not found */
  if (match != 0) return false; 

  /* player found */
  /* get movie offsets after padding*/
  int nameLength = strlen(playerFound) + 1;
  if (nameLength%2 == 1) nameLength++;
  int length = nameLength + 2;
  if (length%4 != 0) length += 2;
  const int * movieOffsets =  (const int *)(playerFound + length);

  /* push actor's movies */
  short numMovies = (short) *(playerFound + nameLength);
  for (int i = 0; i < (int)numMovies; i++){
      film f(movieFile, *(movieOffsets + i));
      films.push_back(f);
  }

  return true;
}

bool imdb::getCast(const film& movie, vector<string>& players) const { 
  /* clear the vector */
  players.clear();

  /* find the movie's offset in movieFile */
  const int *countp = (const int *) movieFile;
  const int *begin = (const int *) movieFile + 1;
  const int *end = begin + *countp;
  const int *found = lower_bound(begin, end, movie, [this](int offset, const film& movie) {
          film movieAtOffset(movieFile, offset);
          return movieAtOffset < movie;
  });

  /* check that the movie exists in movieFile */
  film movieFound(movieFile, *found);
  /* movie not found */
  if (movie != movieFound) return false; 

  /* movie found */
  /* get cast offsets after padding */
  /* include one byte for year */
  int titleLength = movieFound.title.length() + 2;
  if (titleLength%2 == 1) titleLength++;
  /* include two bytes for numActors */
  int length = titleLength + 2;
  if (length%4 != 0) length += 2;
  const int * castOffsets = (const int *)((const char *)movieFile + *found + length);

  /* push film's cast */
  short * numActors = (short *)((const char *)movieFile + *found + titleLength);
  for (short i = 0; i < *numActors; i++){
      const string player = (const char *)actorFile + *(castOffsets + (int)i);
      players.push_back(player);
  }

  return true;

}

const void *imdb::acquireFileMap(const string& fileName, struct fileInfo& info) {
  struct stat stats;
  stat(fileName.c_str(), &stats);
  info.fileSize = stats.st_size;
  info.fd = open(fileName.c_str(), O_RDONLY);
  return info.fileMap = mmap(0, info.fileSize, PROT_READ, MAP_SHARED, info.fd, 0);
}

void imdb::releaseFileMap(struct fileInfo& info) {
  if (info.fileMap != NULL) munmap((char *) info.fileMap, info.fileSize);
  if (info.fd != -1) close(info.fd);
}
