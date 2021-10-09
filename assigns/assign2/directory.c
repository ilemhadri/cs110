#include "directory.h"
#include "inode.h"
#include "diskimg.h"
#include "file.h"
#include <stdio.h>
#include <string.h>

#define DIRNAME_SIZE 14
#define DIRENT_SIZE 16
#define NUM_DIRENTS_PER_BLOCK 32

int directory_findname(struct unixfilesystem *fs, const char *name,
		       int dirinumber, struct direntv6 *dirEnt) {
    // compute directory size
    struct inode inp;
    if (inode_iget(fs, dirinumber, &inp) == -1){
      fprintf(stderr, "Could not read directory inode in directory_findname");
      return -1;
    }
    int dirSize = inode_getsize(&inp);
    if (dirSize == -1){
      fprintf(stderr,"could not get dirSize in directory_findname");
      return -1;
    }

    struct direntv6 direntArr[NUM_DIRENTS_PER_BLOCK];
    /* iterate over sector blocks */
    /* fprintf(stdout, "current fileBlock: %d\n"); */
    for (int fileBlockIndex = 0; fileBlockIndex <= dirSize / DISKIMG_SECTOR_SIZE; fileBlockIndex++){
      // fetch dirents within current sector block into direntArr
      int currentBlockSize = file_getblock(fs, dirinumber, fileBlockIndex, &direntArr);
      if (currentBlockSize == -1){
	fprintf(stderr, "file_getblock failed in directory_findname");
	return -1;
      }

      /* fprintf(stdout, "current block size: %d\n",currentBlockSize); */
      for (int i = 0; i < currentBlockSize / DIRENT_SIZE; i++){
	// found name; terminate 
	if (strncmp(name, direntArr[i].d_name, DIRNAME_SIZE) == 0){
	  *dirEnt = direntArr[i];
	  return 0;
	}
      }
    }

    // did not find name
    return -1;    
}
