/**
 * File: contains.c
 * ----------------
 * Utility program that has no UNIX equivalent, but nonetheless illustrates
 * how opendir/readdir/closedir all work.  The program expects a directory to
 * be supplied as its only argument, and then lists the names of all of the
 * entires within that directory.
 *
 * I don't explicitly cover this in today's slide decks, but instead rely on
 * it to prepare us for the larger program in the search.c file.
 */

#include <string.h>          // for strcmp
#include <stdlib.h>          // for EXIT_FAILURE
#include <stdbool.h>         // for bool support
#include <dirent.h>          // for DIR *, struct dirent
#include <sys/stat.h>        // for struct stat, stat
#include "exit-utils.h"      // for exitIf, exitUnless

enum {
  kWrongArgumentCount = EXIT_FAILURE, kBogusFlag, kDirectoryNotFound
};

/**
 * Function: surfaceFileType
 * -------------------------
 * Returns the file type as a string (e.g. "symlink").  The two supplied
 * arguments should be able to be concatenated to construct the absolute
 * path name of the file whose type is needed.
 */
static const char *surfaceFileType(const char *dirName, const char *entryName) {
  char absolutePathname[strlen(dirName) + strlen(entryName) + 2]; // +2 is really +1 (for possible '/' separator) and +1 (for '\0')
  strcpy(absolutePathname, dirName);
  if (absolutePathname[strlen(absolutePathname) - 1] != '/') strcpy(absolutePathname + strlen(absolutePathname), "/");
  strcpy(absolutePathname + strlen(absolutePathname), entryName);
  struct stat st;
  lstat(absolutePathname, &st);
  if (S_ISLNK(st.st_mode)) return "symlink";
  if (S_ISDIR(st.st_mode)) return "directory";
  if (S_ISREG(st.st_mode)) return "regular";
  return "unknown";
}

/**
 * Function: main
 * --------------
 * Defines the entry point of the program.
 */
int main(int argc, char **argv) {
  exitUnless(argc == 2 || argc == 3, kWrongArgumentCount, stderr, "Executable expects exactly one or two arguments.\n");
  exitUnless(argc == 2 || strcmp(argv[2], "--full") == 0, kBogusFlag, stderr, "Second argument can only be \"--full\".\n");
  const char *dirName = argv[1];
  bool showFileType = argc == 3;
  DIR *dir = opendir(dirName);
  exitIf(dir == NULL, kDirectoryNotFound, stderr, "Count not open the directory named \"%s\".\n", dirName);
  printf("Directory contains the following:\n\n");
  while (true) {
    struct dirent *de = readdir(dir);
    if (de == NULL) break;
    printf(" + %s", de->d_name);
    if (showFileType) printf(" (%s)", surfaceFileType(dirName, de->d_name));
    printf("\n");
  }
  printf("\n");
  closedir(dir);
  return 0;
}
