#include <stdio.h>

#include "file.h"
#include "inode.h"
#include "diskimg.h"

int file_getblock(struct unixfilesystem *fs, int inumber, int fileBlockIndex, void *buf) {
    struct inode inp;

    // fetch inode from inumber
    if (inode_iget(fs, inumber, &inp) == -1){
      fprintf(stderr, "inode_iget failed in file_getblock\n");
      return -1;
    }

    // convert fileBlockIndex into actual block number
    int blockNumber = inode_indexlookup(fs, &inp, fileBlockIndex);
    if (blockNumber == -1){
      fprintf(stderr,"inode_indexlookup failed in file_getblock\n");
      return -1;
    }

    // read block number into buf
    if (diskimg_readsector(fs->dfd, blockNumber, buf) == -1){
      fprintf(stderr, "readsector failed in file_getblock\n");
      return -1;
    }

    // determine block file size
    int filesize = inode_getsize(&inp);
    // return 0 for empty file;
    if (filesize == 0) return 0;
    // return 512 if file size is a multiple of 512
    if (filesize % DISKIMG_SECTOR_SIZE == 0) return DISKIMG_SECTOR_SIZE;
    // return 512 except if the block is the very last payload block
    if (fileBlockIndex < filesize / DISKIMG_SECTOR_SIZE) return DISKIMG_SECTOR_SIZE;
    return filesize % DISKIMG_SECTOR_SIZE;

   return -1; 
}
