/**
 * File: openversusdup.c
 * ---------------------
 * This program illustrates how the open system call
 * creates independent file sessions (e.g. multiple entries
 * in the open file table), whereas dup can be used to create
 * new descriptors that alias existing file sessions.
 *
 * This particular program isn't referenced in the lecture
 * slides or in lecture.  It's just here to clarify the
 * difference between open (a session creator) and
 * dup (a session aliaser)
 */

#include <fcntl.h>    // for open
#include <unistd.h>   // for read, write, close
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <errno.h>

int main(int argc, char *argv[]) {
    int fd1 = open("vowels.txt", O_RDONLY);
    int fd2 = open("vowels.txt", O_RDONLY);
    // fd1 and fd2 are descriptors linked to independent sessions in the open file table
    char ch1, ch2;
    read(fd1, &ch1, 1);
    printf("First char read from fd1 is first character of file: %c\n", ch1);
    read(fd2, &ch2, 1);
    printf("First char read from fd2 is first character of file: %c\n", ch2);
    // why the first char twice?  Each session maintains a count on the number
    // of characters that have been read in from the file.
    close(fd2); // don't need it any more
    int fd3 = dup(fd1);
    // fd1 and fd3 alias the same exact session
    // unusual to do this in a single process program, but very common in
    // programs we write that create multiple helper processes..
    // that's a topic for weeks 2 and 3
    char ch3, ch4;
    read(fd1, &ch3, 1);
    printf("Second char read through fd1 is second character of file: %c\n", ch3);
    read(fd3, &ch4, 1);
    printf("First char read through fd3 is third character of file, %c\n", ch4);
    // why the third? because the second character was consumed from
    // the same session through another descriptor
    close(fd1);
    close(fd3); // let's be good descriptor citizens and close everything before exit
    return 0;
}
