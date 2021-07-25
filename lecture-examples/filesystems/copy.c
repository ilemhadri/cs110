#include <stdbool.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>

static const int kWrongArgumentCount = 1;
static const int kSourceFileNonExistent = 2;
static const int kDestinationFileOpenFailure = 4;
static const int kReadFailure = 8;
static const int kWriteFailure = 16;
static const int kDefaultPermissions = 0644; // number equivalent of "rw-r--r--"

int main(int argc, char *argv[]) {
  if (argc != 3) {
    fprintf(stderr, "%s <source-file> <destination-file>.\n", argv[0]);
    return kWrongArgumentCount;
  }
  
  int fdin = open(argv[1], O_RDONLY);
  if (fdin == -1) {
    fprintf(stderr, "%s: source file could not be opened.\n", argv[1]);
    return kSourceFileNonExistent;
  }
  
  int fdout = open(argv[2], O_WRONLY | O_CREAT | O_EXCL, kDefaultPermissions);
  if (fdout == -1) {
    switch (errno) {
    case EEXIST:
      fprintf(stderr, "%s: destination file already exists.\n", argv[2]);
      break;
    default:
      fprintf(stderr, "%s: destination file could not be created.\n", argv[2]);
      break;
    }
    return kDestinationFileOpenFailure;
  }

  char buffer[1024];
  while (true) {
    ssize_t bytesRead = read(fdin, buffer, sizeof(buffer));
    if (bytesRead == 0) break;
    if (bytesRead == -1) {
      fprintf(stderr, "%s: lost access to file while reading.\n", argv[1]);
      return kReadFailure;
    }

    size_t bytesWritten = 0;
    while (bytesWritten < bytesRead) {
      ssize_t count = write(fdout, buffer + bytesWritten, bytesRead - bytesWritten);
      if (count == -1) {
	fprintf(stderr, "%s: lost access to file while writing.\n", argv[2]);
	return kWriteFailure;
      }
      bytesWritten += count;
    }
  }

  if (close(fdin) == -1) fprintf(stderr, "%s: had trouble closing file.\n", argv[1]);
  if (close(fdout) == -1) fprintf(stderr, "%s: had trouble closing file.\n", argv[2]);
  return 0;
}
