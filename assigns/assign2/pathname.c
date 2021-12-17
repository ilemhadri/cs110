
#include "pathname.h"
#include "directory.h"
#include "inode.h"
#include "diskimg.h"
#include <stdio.h>
#include <string.h>

int pathname_lookup(struct unixfilesystem *fs, const char *pathname) {
    size_t pathLength = strlen(pathname);

    // deal with "/" pathname
    if (pathLength == 1) return ROOT_INUMBER;
    
    struct direntv6 dirEnt;
    int curr_inumber = ROOT_INUMBER;
    char * name;

    // strip leading virgule to make strsep behave
    char temp[pathLength];
    char *pathnameWithoutRoot = temp;
    strcpy(pathnameWithoutRoot, pathname + 1);

    // traverse pathname
    while ((name = strsep(&pathnameWithoutRoot, "/")) != NULL){
      if (directory_findname(fs, name, curr_inumber, &dirEnt) == -1){
	fprintf(stderr, "directory_findname failed in pathname_lookup\n");
	return -1;
      }
      // update inumber
      curr_inumber = dirEnt.d_inumber;
    }

    // path traversal complete; return final inumber
    return curr_inumber; 
}
