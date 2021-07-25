/**
 * File: search.c
 * --------------
 * Designed to emulate the properties of the GNU find shell program.
 * The built-in version of find is much more robust than what we provide here.
 *
 * To help focus on the file system directives, I omit most error checking from 
 * this particular implementation.
 */

#include <stdbool.h>   // for bool
#include <stddef.h>    // for size_t
#include <stdio.h>     // for printf, fprintf, etc.
#include <stdlib.h>    // for exit
#include <stdarg.h>    // for va_list, etc.
#include <sys/stat.h>  // for stat
#include <string.h>    // for strlen, strcpy, strcmp
#include <dirent.h>    // for DIR, struct dirent

static const size_t kMaxPath = 1024;

static const int kWrongArgumentCount = 1;
static const int kDirectoryNeeded = 2;

static void exitUnless(bool test, FILE *stream, int code, const char *control, ...) {
  if (test) return;
  va_list arglist;
  va_start(arglist, control);
  vfprintf(stream, control, arglist);
  va_end(arglist);
  exit(code);
}

static void listMatches(char path[], size_t length, const char *pattern) {
  DIR *dir = opendir(path);
  if (dir == NULL) return;
  strcpy(path + length, "/");
  length++;
  while (true) {
    struct dirent *de = readdir(dir);
    if (de == NULL) break;
    if (strcmp(de->d_name, ".") == 0 || strcmp(de->d_name, "..") == 0) continue;
    if (length + strlen(de->d_name) > kMaxPath) continue;
    strcpy(path + length, de->d_name);
    struct stat st;
    lstat(path, &st);
    if (S_ISREG(st.st_mode)) {
      if (strcmp(de->d_name, pattern) == 0) printf("%s\n", path);
    } else if (S_ISDIR(st.st_mode)) {
      listMatches(path, length + strlen(de->d_name), pattern);
    }
  }
  
  closedir(dir);
}

int main(int argc, char *argv[]) {
  exitUnless(argc == 3, stderr, kWrongArgumentCount, "Usage: %s <directory> <pattern>\n", argv[0]);
  const char *directory = argv[1];
  struct stat st;
  stat(directory, &st);
  exitUnless(S_ISDIR(st.st_mode), stderr, kDirectoryNeeded, "<directory> must be an actual directory, %s is not", directory);
  size_t length = strlen(directory);
  if (length > kMaxPath) return 0;
  const char *pattern = argv[2];
  char path[kMaxPath + 1];
  strcpy(path, directory); // no buffer overflow because of above check
  listMatches(path, length, pattern);
  return 0;
}

