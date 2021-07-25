# CS110 C Threading and Concurrency Examples
CC = gcc

# The CFLAGS variable sets compile flags for g++:
#  -g          compile with debug information
#  -Wall       give all diagnostic warnings
#  -pedantic   require compliance with ANSI standard
#  -O0         do not optimize generated code
#  -std=gnu99  go with the C99 standard
CFLAGS = -g -Wall -pedantic -O0 -std=gnu99

# The LDFLAGS variable sets flags for linker
#  -lpthread link in libpthread (thread library)
LDFLAGS = -lm -lpthread

# In this section, you list the files that are part of the project.
# If you add/change names of header/source files, here is where you
# edit the Makefile.
HEADERS = 
SOURCES = introverts.c confused-extroverts.c extroverts.c
OBJECTS = $(SOURCES:.c=.o)
TARGETS = $(SOURCES:.c=)

default: $(TARGETS)

introverts: introverts.o
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

confused-extroverts: confused-extroverts.o
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

extroverts: extroverts.o
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# In make's default rules, a .o automatically depends on its .c file
# (so editing the .cc will cause recompilation into its .o file).
# The line below creates additional dependencies, most notably that it
# will cause the .c to recompiled if any included .h file changes.

Makefile.dependencies:: $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) -MM $(SOURCES) > Makefile.dependencies

-include Makefile.dependencies

# Phony means not a "real" target, it doesn't build anything
# The phony target "clean" is used to remove all compiled object files.
# The phony target "spartan" is used to remove all compilation products and extra backup files. 

.PHONY: clean spartan

clean:
	@rm -f $(TARGETS) $(OBJECTS) core Makefile.dependencies

spartan: clean
	@rm -f *~
