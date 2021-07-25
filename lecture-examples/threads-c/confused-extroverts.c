/**
 * File: confused-extroverts.c
 * ---------------------------
 * Presents a pthreads examples illustrating how data is (clumsily) shared
 * with threads.  The example is intentionally broken, however, to illustrate
 * the simplest of race conditions.
 */

#include <pthread.h>  // provides pthread_t type, thread functions
#include <stdio.h>    // provides printf, which is thread-safe

static const char *kExtroverts[] = {
  "Frank", "Jon", "Lauren", "Marco", "Julie", "Patty",
  "Tagalong Introvert Jerry"
};
static const size_t kNumExtroverts = sizeof(kExtroverts)/sizeof(kExtroverts[0]) - 1;

static void *recharge(void *args) {
  const char *name = kExtroverts[*(size_t *)args];
  printf("Hey, I'm %s.  Empowered to meet you.\n", name);
  return NULL;
}

int main() {
  printf("Let's hear from %zu extroverts.\n", kNumExtroverts);
  pthread_t extroverts[kNumExtroverts];
  for (size_t i = 0; i < kNumExtroverts; i++)
    pthread_create(&extroverts[i], NULL, recharge, &i);
  for (size_t j = 0; j < kNumExtroverts; j++)
    pthread_join(extroverts[j], NULL);
  printf("Everyone's recharged!\n");
  return 0;
}
