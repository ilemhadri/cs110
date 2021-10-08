#include <stdio.h>
#include "inode.h"
#include "diskimg.h"

#define INODES_PER_BLOCK 16
#define NUM_BLOCK_NUMS_PER_BLOCK 256
#define LAST_IADDR 7

int inode_iget(struct unixfilesystem *fs, int inumber, struct inode *inp) {
  int sectorQuotient = (inumber - ROOT_INUMBER) / INODES_PER_BLOCK;
  int sectorRemainder = (inumber - ROOT_INUMBER) % INODES_PER_BLOCK;
  struct inode inodesFromSector[INODES_PER_BLOCK];
  int read = diskimg_readsector(fs->dfd, sectorQuotient + INODE_START_SECTOR, &inodesFromSector);
  if (read == -1) {
      fprintf(stderr, "inode_iget can't read sector %d\n", sectorQuotient);
      return -1;
  }
  *inp = inodesFromSector[sectorRemainder];
  return 0;
}

int inode_indexlookup(struct unixfilesystem *fs, struct inode *inp, int fileBlockIndex) {
    /* inode not allocated; do nothing */
    if (!(inp->i_mode & IALLOC)){
        fprintf(stderr, "inode unallocated. inode_indexlookup cannot proceed."); 
        return -1;
    }

    /* deal with direct addressing first */
    if ((inp->i_mode & ILARG) == 0){
        if (fileBlockIndex > LAST_IADDR) {
           fprintf(stderr, "fileBlockIndex exceeds number of direct blocks available");
           return -1;
       }
       return inp->i_addr[fileBlockIndex];
    }

    /* deal with indirect addressing */
    uint16_t singlyIndirect, direct;
    /* determine whether singly or doubly indirect */
    int fileBlockIndexSub = fileBlockIndex - LAST_IADDR * NUM_BLOCK_NUMS_PER_BLOCK;

    /* process doubly indirect addressing */
    if (fileBlockIndexSub >= 0){
        uint16_t doublyIndirectBlocks[NUM_BLOCK_NUMS_PER_BLOCK];
        if (diskimg_readsector(fs->dfd, inp->i_addr[LAST_IADDR], &doublyIndirectBlocks) == -1) {
            fprintf(stderr, "could not read singly indirect blocks from doubly indirect");
            return -1;
        }
        uint16_t doublyIndirect = fileBlockIndexSub / NUM_BLOCK_NUMS_PER_BLOCK;

        singlyIndirect = doublyIndirectBlocks[doublyIndirect];
        direct = fileBlockIndexSub % NUM_BLOCK_NUMS_PER_BLOCK;
    } 
    /* process singly indirect addressing */
    else {
        uint16_t fbiQuotient = fileBlockIndex / NUM_BLOCK_NUMS_PER_BLOCK;
        uint16_t fbiRemainder = fileBlockIndex % NUM_BLOCK_NUMS_PER_BLOCK;

        singlyIndirect = inp->i_addr[fbiQuotient];
        direct = fbiRemainder;
    }

    /* read direct block */
    uint16_t directBlocks[NUM_BLOCK_NUMS_PER_BLOCK];
    if (diskimg_readsector(fs->dfd, singlyIndirect, &directBlocks) == -1) {
        fprintf(stderr, "could not read direct blocks from singly indirect");
        return -1;
    }
    return directBlocks[direct];
}

int inode_getsize(struct inode *inp) {
  return ((inp->i_size0 << 16) | inp->i_size1); 
}
