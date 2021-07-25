/**
 * File: publish.c
 * ---------------
 * This buggy program attempts to publish the date all of the named
 * files supplied via argv[1] and beyond.
 */

#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>

static void publish(const char *name) {
    printf("Publishing date and time to file named \"%s\".\n", name);
    int outfile = open(name, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    dup2(outfile, STDOUT_FILENO);
    close(outfile);
    if (fork() > 0) return;
    char *argv[] = { "date", NULL };
    execvp(argv[0], argv);
}

int main(int argc, char *argv[]) {
    for (size_t i = 1; i < argc; i++) publish(argv[i]);
    return 0;
}
