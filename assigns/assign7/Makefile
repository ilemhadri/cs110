# CS110 Assignment 8 Makefile

# Compile parallel jobs by default
MAKEFLAGS := --jobs=$(shell nproc) --output-sync=target

CXX = /usr/bin/clang++-10

# The CPPFLAGS variable sets compile flags for g++:
#  -g          compile with debug information
#  -Wall       give all diagnostic warnings
#  -pedantic   require compliance with ANSI standard
#  -O0         do not optimize generated code
#  -std=c++0x  go with the c++0x experimental extensions for thread support (and other nifty things)
#  -D_GLIBCXX_USE_NANOSLEEP included for this_thread::sleep_for and this_thread::sleep_until support
#  -D_GLIBCXX_USE_SCHED_YIELD included for this_thread::yield support
CPPFLAGS = -g -fno-limit-debug-info -Wall -pedantic -O0 -std=c++20 -D_GLIBCXX_USE_NANOSLEEP -D_GLIBCXX_USE_SCHED_YIELD -I/afs/ir/class/cs110/local/include/ -I/afs/ir/class/cs110/include

# The LDFLAGS variable sets flags for linker
# -lm        link to libm (math library)
# -pthread   link in libpthread (thread library) to back C++11 extensions
# -lthreads  link to course-specific concurrency functions and classes
# -lrand     link to a C++11-backed random number generator module
# -socket++  link to third party socket++ library for sockbuf and iosockstream classes
LDFLAGS = -lm -lpthread -L/afs/ir/class/cs110/local/lib -lthreadpoolrelease -L/afs/ir/class/cs110/local/lib -lthreads -L/afs/ir/class/cs110/local/lib -lrand -L/afs/ir/class/cs110/lib/socket++ -lsocket++ -Wl,-rpath=/afs/ir/class/cs110/lib/socket++

# In this section, you list the files that are part of the project.
# If you add/change names of header/source files, here is where you
# edit the Makefile.
PROGRAMS = mr.cc mrm.cc mrr.cc word-count-mapper.cc word-count-reducer.cc
PROGS_ASAN = mr_asan mrm_asan mrr_asan
PROGS_TSAN = mr_tsan mrm_tsan mrr_tsan
STUDENT_SRC = mapreduce-server.cc mapreduce-mapper.cc mapreduce-reducer.cc
EXTRAS = $(STUDENT_SRC) mapreduce-worker.cc \
         client-socket.cc server-socket.cc mr-nodes.cc mr-messages.cc mr-env.cc mr-utils.cc mr-random.cc \
         mr-names.cc
HEADERS = $(EXTRAS:.cc=.h) mapreduce-server-exception.h
SOURCES = $(PROGRAMS) $(EXTRAS)
OBJECTS = $(SOURCES:.cc=.o)

ASAN_OBJ = $(patsubst %.cc,%_asan.o,$(PROGRAMS) $(EXTRAS))
ASAN_DEP = $(patsubst %.o,%.d,$(ASAN_OBJ))
TSAN_OBJ = $(patsubst %.cc,%_tsan.o,$(PROGRAMS) $(EXTRAS))
TSAN_DEP = $(patsubst %.o,%.d,$(TSAN_OBJ))

default: $(PROGRAMS:.cc=) $(PROGS_ASAN) $(PROGS_TSAN)

directories:
	rm -fr files/intermediate
	rm -fr files/output
	mkdir -p files/intermediate
	mkdir -p files/output

mr: mr.o mapreduce-server.o server-socket.o client-socket.o mr-nodes.o mr-messages.o mr-env.o mr-utils.o mr-names.o
	$(CXX) $(CPPFLAGS) -o $@ $^ $(LDFLAGS)

mrm: mrm.o mapreduce-worker.o mapreduce-mapper.o client-socket.o mr-messages.o mr-env.o mr-names.o
	$(CXX) $(CPPFLAGS) -o $@ $^ $(LDFLAGS)

mrr: mrr.o mapreduce-worker.o mapreduce-reducer.o client-socket.o mr-messages.o mr-env.o mr-names.o
	$(CXX) $(CPPFLAGS) -o $@ $^ $(LDFLAGS)

word-count-mapper: word-count-mapper.o mr-random.o
	$(CXX) $(CPPFLAGS) -o $@ $^ $(LDFLAGS)

word-count-reducer: word-count-reducer.o mr-random.o
	$(CXX) $(CPPFLAGS) -o $@ $^ $(LDFLAGS)

$(PROGS_ASAN): %:%.o $(patsubst %.cc,%_asan.o,$(EXTRAS))
	$(CXX) $^ $(LDFLAGS) -o $@ -fsanitize=address

$(PROGS_TSAN): %:%.o $(patsubst %.cc,%_tsan.o,$(EXTRAS))
	$(CXX) $^ $(LDFLAGS) -o $@ -fsanitize=thread

$(ASAN_OBJ): %_asan.o:%.cc
	$(CXX) $(CPPFLAGS) -fsanitize=address -c -o $@ $<

$(TSAN_OBJ): %_tsan.o:%.cc
	$(CXX) $(CPPFLAGS) -fsanitize=thread -c -o $@ $<

$(addprefix tidy_,$(STUDENT_SRC))::
	$(info "Checking style for $(@:tidy_%=%)...")
	clang-tidy $(@:tidy_%=%)

tidy:: $(addprefix tidy_,$(STUDENT_SRC))

# In make's default rules, a .o automatically depends on its .cc file
# (so editing the .cc will cause recompilation into its .o file).
# The line below creates additional dependencies, most notably that it
# will cause the .cc to recompiled if any included .h file changes.

Makefile.dependencies:: $(SOURCES) $(HEADERS)
	$(CXX) $(CPPFLAGS) -MM $(SOURCES) > Makefile.dependencies

-include Makefile.dependencies $(ASAN_DEP) $(TSAN_DEP)

# Phony means not a "real" target, it doesn't build anything
# The phony target "clean" is used to remove all compiled object files.
# The phony target "spartan" is used to remove all compilation products and extra backup files. 

.PHONY: clean spartan filefree

filefree::
	@rm -fr files/intermediate/* files/output/*	

clean:: filefree
	@rm -f $(PROGRAMS:.cc=) $(OBJECTS) core Makefile.dependencies
	rm -f $(PROGS_ASAN) $(ASAN_OBJ) $(ASAN_DEP)
	rm -f $(PROGS_TSAN) $(TSAN_OBJ) $(TSAN_DEP)

spartan:: clean
	@rm -f *~
