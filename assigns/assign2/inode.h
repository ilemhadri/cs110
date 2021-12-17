#ifndef _INODE_H
#define _INODE_H

#include "unixfilesystem.h"

/**
 * Fetches the specified inode from the filesystem. 
 * Returns 0 on success, -1 on error.  
 */
int inode_iget(struct unixfilesystem *fs, int inumber, struct inode *inp);

/**
 * Given an index of a file block, retrieves the file's actual block number
 * from the given inode.
 *
 * Returns the disk block number on success, -1 on error.  
 */
int inode_indexlookup(struct unixfilesystem *fs, struct inode *inp, int fileBlockIndex);

/**
 * Computes the size in bytes of the file identified by the given inode
 */
int inode_getsize(struct inode *inp);

#endif // _INODE_
