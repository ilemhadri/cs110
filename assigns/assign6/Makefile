# Makefile for proxy
# Based on Makefiles previously written by Julie Zelenski.

# Compile parallel jobs by default
MAKEFLAGS := --jobs=$(shell nproc) --output-sync=target


CXX = clang++-10
DEPS = -MMD -MF $(@:.o=.d)

# The CFLAGS variable sets compile flags for gcc:
#  -g                         compile with debug information
#  -Wall                      give all diagnostic warnings
#  -pedantic                  require compliance with ANSI standard
#  -O0                        do not optimize generated code
#  -std=c++14                 go with the c++14 extensions for thread support, unordered maps, etc
#  -D_GLIBCXX_USE_NANOSLEEP   included for this_thread::sleep_for and this_thread::sleep_until support
#  -D_GLIBCXX_USE_SCHED_YIELD included for this_thread::yield support
CXXFLAGS = -g -fno-limit-debug-info -Wall -pedantic -O0 -std=c++20 -D_GLIBCXX_USE_NANOSLEEP -D_GLIBCXX_USE_SCHED_YIELD -I/afs/ir/class/cs110/include -I/afs/ir/class/cs110/local/include $(DEPS) -Wno-deprecated-declarations

# The LDFLAGS variable sets flags for linker
#  -pthread   link in libpthread (thread library) to back C++11 extensions (note -pthread and not -lpthread)
#  -lthread   link to course-specific concurrency functions and classes
#  -lsocket++ link to open source socket++ library, which layers iostream objects over sockets
LDFLAGS = -lpthread -L/afs/ir/class/cs110/local/lib -lthreadpoolrelease -L/afs/ir/class/cs110/local/lib -lthreads -L/afs/ir/class/cs110/lib/socket++ -lsocket++ -Wl,-rpath=/afs/ir/class/cs110/lib/socket++

# The ARFLAGS variable, if absent, defaults to rv, but I don't want a verbose printout
ARFLAGS = r

# In this section, you list the files that are part of the project.
# If you add/change names of header/source files, here is where you
# edit the Makefile.

STUDENT_SOURCES = \
	proxy.cc \
	request.cc \
	request-handler.cc \
	response.cc \
	scheduler.cc \
	cache.cc

SOURCES = $(STUDENT_SOURCES) \
	main.cc \
	proxy-options.cc \
	header.cc \
	payload.cc \
	strike-set.cc \
	client-socket.cc \
	watchset.cc

HEADERS = $(SOURCES:.cc=.h)
OBJECTS = $(SOURCES:.cc=.o)
DEPENDENCIES = $(patsubst %.o,%.d,$(OBJECTS))
TARGET = proxy

TARGET_ASAN = $(TARGET)_asan
TARGET_TSAN = $(TARGET)_tsan
ASAN_OBJ = $(patsubst %.cc,%_asan.o,$(SOURCES))
ASAN_DEP = $(patsubst %.o,%.d,$(ASAN_OBJ))
TSAN_OBJ = $(patsubst %.cc,%_tsan.o,$(SOURCES))
TSAN_DEP = $(patsubst %.o,%.d,$(TSAN_OBJ))

default: $(TARGET) $(TARGET_ASAN) $(TARGET_TSAN)

proxy: $(OBJECTS)
	$(CXX) $(CXXFLAGS) -o $@ $(OBJECTS) $(LDFLAGS)

$(ASAN_OBJ): %_asan.o:%.cc
	$(CXX) $(CXXFLAGS) -MMD -MF $(@:.o=.d) -fsanitize=address -c -o $@ $<

$(TSAN_OBJ): %_tsan.o:%.cc
	$(CXX) $(CXXFLAGS) -MMD -MF $(@:.o=.d) -fsanitize=thread -c -o $@ $<

$(TARGET_ASAN): %:%.o $(patsubst %.cc,%_asan.o,$(SOURCES))
	$(CXX) $^ $(LDFLAGS) -o $@ -fsanitize=address

$(TARGET_TSAN): %:%.o $(patsubst %.cc,%_tsan.o,$(SOURCES))
	$(CXX) $^ $(LDFLAGS) -o $@ -fsanitize=thread

-include $(SOURCES:.cc=.d) $(ASAN_DEP) $(TSAN_DEP)

# Phony means not a "real" target, it doesn't build anything
# The phony target "clean" is used to remove all compiled object files.
# The phony target "spartan" is used to remove all compiled object and backup files.
.PHONY: clean spartan

clean:
	@rm -f $(TARGET) $(OBJECTS) $(DEPENDENCIES) *.o core
	rm -f $(TARGET_ASAN) $(ASAN_OBJ) $(ASAN_DEP)
	rm -f $(TARGET_TSAN) $(TSAN_OBJ) $(TSAN_DEP)

spartan: clean
	@rm -f *~
