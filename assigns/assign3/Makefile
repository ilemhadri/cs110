# CS110 trace Solution Makefile Hooks

C_PROGS =
CXX_PROGS = trace farm
PROGS = $(C_PROGS) $(CXX_PROGS)
PROGS_ASAN = $(patsubst %,%_asan,$(CXX_PROGS))
EXTRA_C_PROGS = 
EXTRA_CXX_PROGS = simple-test1 simple-test2 simple-test3 simple-test4 simple-test5 trace-system-calls-test trace-error-constants-test
EXTRA_PROGS = $(EXTRA_C_PROGS) $(EXTRA_CXX_PROGS)
# CC = gcc
# CXX = /usr/bin/g++-5

CC = /usr/bin/clang-10
CXX = /usr/bin/clang++-10

C_WARNINGS = -Wall -pedantic
C_DEPS = -MMD -MF $(@:.o=.d)
C_DEFINES = 
C_INCLUDES = -I/afs/ir/class/cs110/local/include

CFLAGS = -g -fno-limit-debug-info $(C_WARNINGS) $(C_DEPS) -std=gnu99 $(C_INCLUDES)

CXX_WARNINGS = -Wall -pedantic -Wno-vla
CXX_DEPS = -MMD -MF $(@:.o=.d)
CXX_DEFINES =
CXX_INCLUDES = -I/afs/ir/class/cs110/local/include

CXXFLAGS = -g -fno-limit-debug-info $(CXX_WARNINGS) -O0 -std=c++20 $(CXX_DEPS) $(CXX_DEFINES) $(CXX_INCLUDES)
LDFLAGS = -L/usr/class/cs110/samples/assign3 -L/afs/ir/class/cs110/local/lib -lsubprocess

TRACE_LIB_SRC = trace-options.cc trace-error-constants.cc trace-system-calls.cc
TRACE_LIB_OBJ = $(patsubst %.cc,%.o,$(patsubst %.S,%.o,$(TRACE_LIB_SRC)))
TRACE_LIB_DEP = $(patsubst %.o,%.d,$(TRACE_LIB_OBJ))
TRACE_LIB = libtrace.a

C_PROGS_SRC = $(patsubst %,%.c,$(C_PROGS))
C_PROGS_OBJ = $(patsubst %.c,%.o,$(patsubst %.S,%.o,$(C_PROGS_SRC)))
C_PROGS_DEP = $(patsubst %.o,%.d,$(C_PROGS_OBJ))

CXX_PROGS_SRC = $(patsubst %,%.cc,$(CXX_PROGS))
CXX_PROGS_OBJ = $(patsubst %.cc,%.o,$(patsubst %.S,%.o,$(CXX_PROGS_SRC)))
CXX_PROGS_DEP = $(patsubst %.o,%.d,$(CXX_PROGS_OBJ))

EXTRA_C_PROGS_SRC = $(patsubst %,%.c,$(EXTRA_C_PROGS))
EXTRA_C_PROGS_OBJ = $(patsubst %.c,%.o,$(patsubst %.S,%.o,$(EXTRA_C_PROGS_SRC)))
EXTRA_C_PROGS_DEP = $(patsubst %.o,%.d,$(EXTRA_C_PROGS_OBJ))

EXTRA_CXX_PROGS_SRC = $(patsubst %,%.cc,$(EXTRA_CXX_PROGS))
EXTRA_CXX_PROGS_OBJ = $(patsubst %.cc,%.o,$(patsubst %.S,%.o,$(EXTRA_CXX_PROGS_SRC)))
EXTRA_CXX_PROGS_DEP = $(patsubst %.o,%.d,$(EXTRA_CXX_PROGS_OBJ))

PROGS_ASAN_OBJ = $(patsubst %.cc,%_asan.o,$(patsubst %.S,%.o,$(CXX_PROGS_SRC)))
PROGS_ASAN_DEP = $(patsubst %.o,%.d,$(PROGS_ASAN_OBJ))

all: $(PROGS) $(EXTRA_PROGS) $(PROGS_ASAN)
default: $(PROGS) $(EXTRA_PROGS) $(PROGS_ASAN)

$(CXX_PROGS) $(EXTRA_CXX_PROGS): %:%.o $(TRACE_LIB)
	$(CXX) $^ $(LDFLAGS) -o $@

$(C_PROGS): %:%.o
	$(CC) $^ $(LDFLAGS) -o $@

$(TRACE_LIB): $(TRACE_LIB_OBJ)
	rm -f $@
	ar r $@ $^
	ranlib $@

$(PROGS_ASAN_OBJ): %_asan.o:%.cc
	$(CXX) $(CXXFLAGS) -fsanitize=address -c -o $@ $<
$(PROGS_ASAN): %:%.o $(TRACE_LIB)
	$(CXX) $^ $(LDFLAGS) -o $@ -fsanitize=address

clean::
	rm -fr $(C_PROGS) $(C_PROGS_OBJ) $(C_PROGS_DEP)
	rm -fr $(CXX_PROGS) $(CXX_PROGS_OBJ) $(CXX_PROGS_DEP)
	rm -fr $(EXTRA_C_PROGS) $(EXTRA_C_PROGS_OBJ) $(EXTRA_C_PROGS_DEP)
	rm -fr $(EXTRA_CXX_PROGS) $(EXTRA_CXX_PROGS_OBJ) $(EXTRA_CXX_PROGS_DEP)
	rm -fr $(PROGS_ASAN) $(PROGS_ASAN_OBJ) $(PROGS_ASAN_DEP)
	rm -fr $(TRACE_LIB) $(TRACE_LIB_OBJ) $(TRACE_LIB_DEP)

spartan:: clean
	rm -fr *~
	rm -fr .trace_signatures.txt
	rm -fr padvtest padvtest.* sadvtest sadvtest.cc

.PHONY: all clean spartan

-include $(C_PROGS_DEP) $(CXX_PROGS_DEP) $(TRACE_LIB_DEP) $(EXTRA_C_PROGS_DEP) $(EXTRA_CXX_PROGS_DEP) $(PROGS_ASAN_DEP)
