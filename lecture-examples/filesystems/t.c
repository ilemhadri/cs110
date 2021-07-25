/**
 * File: t.c
 * ---------
 * Emulates the core functionality of the tee user program that comes with most
 * Unix and Linux installation.  tee (and our program, called t) reads everything
 * from standard input and copies everything to standard output *and* to all of the
 * names files supplies as arguments.  This version is low on error checking, because
 * want to you to focus on the use of the open, close, read, and write system calls.
 */

#include <fcntl.h>    // for open
#include <unistd.h>   // for read, write, close
#include <stdbool.h>  // for bool type

#define DEFAULT_FLAGS (O_WRONLY | O_CREAT | O_TRUNC)
#define DEFAULT_PERMISSIONS 0644

static void writeall(int fd, const char buffer[], size_t len) {
  size_t numWritten = 0;
  while (numWritten < len) {
    numWritten += write(fd, buffer + numWritten, len - numWritten);
  }
}

int main(int argc, char *argv[]) {
  int fds[argc];
  fds[0] = STDOUT_FILENO;
  for (size_t i = 1; i < argc; i++)
    fds[i] = open(argv[i], DEFAULT_FLAGS, DEFAULT_PERMISSIONS);
  
  char buffer[2048];
  while (true) {
    ssize_t numRead = read(STDIN_FILENO, buffer, sizeof(buffer));
    if (numRead == 0) break;
    for (size_t i = 0; i < argc; i++)
      writeall(fds[i], buffer, numRead);
  }
  
  for (size_t i = 1; i < argc; i++) close(fds[i]);
  return 0;
}


