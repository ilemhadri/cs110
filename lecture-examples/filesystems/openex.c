/**
 * File: openex.c
 * --------------
 * This program contains a short snippet of code you can
 * consult when you need to open and close files using
 * low-level I/O.
 */

#include <fcntl.h>    // for open
#include <unistd.h>   // for read, write, close
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <errno.h>

const char *kFilename = "my_file";
const int kFileExistsErr = 17;
int main() {
    umask(0); // set to 0 to enable all permissions to be set
    int file_descriptor = open(kFilename, O_WRONLY | O_CREAT | O_EXCL, 0644);
    if (file_descriptor == -1) {
        printf("There was a problem creating '%s'!\n",kFilename);
        if (errno == kFileExistsErr) {
            printf("The file already exists.\n");
        } else {
            printf("Unknown errorno: %d\n",errno);
        }
        return -1;
    }
    printf("Successfully opened the file called \"%s\", and about to close it.\n", kFilename);
    close(file_descriptor);
    return 0;
}
