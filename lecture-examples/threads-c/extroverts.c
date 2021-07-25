/**
 * File: extroverts.c
 * ------------------
 * Provides a (fortunately, fairly simple, soon-to-be-obvious) fix
 * to the same code presented in broken-extroverts.c.
 */

#include <pthread.h>  // provides pthread_t type, thread functions
#include <stdio.h>    // provides printf, which is thread-safe

static const char *kExtroverts[] = {
  "Frank", "Jon", "Lauren", "Marco", "Julie", "Patty",
  "Tagalong Introvert Jerry"
};

static const size_t kNumExtroverts = sizeof(kExtroverts)/sizeof(kExtroverts[0]) - 1;

static void *recharge(void *args) {
  const char *name = args;
  printf("Hey, I'm %s.  Empowered to meet you.\n", name);
  return NULL;
}

int main() {
  printf("Let's hear from %zu extroverts.\n", kNumExtroverts);
  pthread_t extroverts[kNumExtroverts];
  for (size_t i = 0; i < kNumExtroverts; i++)
    pthread_create(&extroverts[i], NULL, recharge, (void *) kExtroverts[i]);
  for (size_t i = 0; i < kNumExtroverts; i++)
    pthread_join(extroverts[i], NULL);
  printf("Everyone's recharged!\n");
  return 0;
}
