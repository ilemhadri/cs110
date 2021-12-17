# CS110 Makefile Hooks: aggregate

PROGS = aggregate tptest tpcustomtest
PROGS_ASAN = $(patsubst %,%_asan,$(PROGS))
PROGS_TSAN = $(patsubst %,%_tsan,$(PROGS))
EXTRA_PROGS = test-union-and-intersection
CXX = clang++-10

NA_LIB_SRC = news-aggregator.cc log.cc utils.cc rss-index.cc

TP_LIB_SRC = thread-pool.cc

WARNINGS = -Wall -pedantic
DEPS = -MMD -MF $(@:.o=.d)
DEFINES = -D_GLIBCXX_USE_NANOSLEEP -D_GLIBCXX_USE_SCHED_YIELD
INCLUDES = -I/afs/ir/class/cs110/local/include -I/usr/include/libxml2 \
					-isystem /afs/ir/class/cs110/include/netlib \
					-I/afs/ir/class/cs110/include/myhtml

CXXFLAGS = -g -fno-limit-debug-info $(WARNINGS) -fPIE -O0 -std=c++20 $(DEPS) $(DEFINES) $(INCLUDES)
LDFLAGS = -lm -lxml2 -L/afs/ir/class/cs110/local/lib -lrand -lthreadpoolrelease -lthreads -lrssnet -pthread -lboost_thread \
          -L/afs/ir/class/cs110/lib/netlib -lcppnetlib-client-connections -lcppnetlib-uri -lcppnetlib-server-parsers \
          -L/afs/ir/class/cs110/lib/myhtml -lmyhtml -lssl -lcrypto -ldl

NA_LIB_OBJ = $(patsubst %.cc,%.o,$(patsubst %.S,%.o,$(NA_LIB_SRC)))
NA_LIB_DEP = $(patsubst %.o,%.d,$(NA_LIB_OBJ))
NA_LIB = libna.a

TP_LIB_OBJ = $(patsubst %.cc,%.o,$(patsubst %.S,%.o,$(TP_LIB_SRC)))
TP_LIB_DEP = $(patsubst %.o,%.d,$(TP_LIB_OBJ))
TP_LIB = libthreadpool.a

PROGS_SRC = aggregate.cc tptest.cc tpcustomtest.cc
PROGS_OBJ = $(patsubst %.cc,%.o,$(patsubst %.S,%.o,$(PROGS_SRC)))
PROGS_DEP = $(patsubst %.o,%.d,$(PROGS_OBJ))

ASAN_OBJ = $(patsubst %.cc,%_asan.o,$(PROGS_SRC) $(NA_LIB_SRC) $(TP_LIB_SRC))
ASAN_DEP = $(patsubst %.o,%.d,$(ASAN_OBJ))
TSAN_OBJ = $(patsubst %.cc,%_tsan.o,$(PROGS_SRC) $(NA_LIB_SRC) $(TP_LIB_SRC))
TSAN_DEP = $(patsubst %.o,%.d,$(TSAN_OBJ))

EXTRA_PROGS_SRC = test-union-and-intersection.cc
EXTRA_PROGS_OBJ = $(patsubst %.cc,%.o,$(patsubst %.S,%.o,$(EXTRA_PROGS_SRC)))
EXTRA_PROGS_DEP = $(patsubst %.o,%.d,$(EXTRA_PROGS_OBJ))

all: $(NA_LIB) $(TP_LIB) $(PROGS) $(EXTRA_PROGS) $(PROGS_ASAN) $(PROGS_TSAN)

$(PROGS): %:%.o $(NA_LIB) $(TP_LIB)
	$(CXX) $^ $(LDFLAGS) -o $@

$(PROGS_ASAN): %:%.o $(patsubst %.cc,%_asan.o,$(NA_LIB_SRC) $(TP_LIB_SRC))
	$(CXX) $^ $(LDFLAGS) -o $@ -fsanitize=address

$(PROGS_TSAN): %:%.o $(patsubst %.cc,%_tsan.o,$(NA_LIB_SRC) $(TP_LIB_SRC))
	$(CXX) $^ $(LDFLAGS) -o $@ -fsanitize=thread

$(ASAN_OBJ): %_asan.o:%.cc
	$(CXX) $(CXXFLAGS) -MMD -MF $(@:.o=.d) -fsanitize=address -c -o $@ $<

$(TSAN_OBJ): %_tsan.o:%.cc
	$(CXX) $(CXXFLAGS) -MMD -MF $(@:.o=.d) -fsanitize=thread -c -o $@ $<

$(EXTRA_PROGS): %:%.o $(TP_LIB)
	$(CXX) $^ $(LDFLAGS) -o $@

$(NA_LIB): $(NA_LIB_OBJ)
	rm -f $@
	ar r $@ $^
	ranlib $@

$(TP_LIB): $(TP_LIB_OBJ)
	rm -f $@
	ar r $@ $^
	ranlib $@

clean:
	rm -f $(PROGS) $(EXTRA_PROGS) $(PROGS_OBJ) $(EXTRA_PROGS_OBJ) $(PROGS_DEP) $(EXTRA_PROGS_DEP)
	rm -f $(NA_LIB) $(NA_LIB_DEP) $(NA_LIB_OBJ)
	rm -f $(TP_LIB) $(TP_LIB_DEP) $(TP_LIB_OBJ)
	rm -f $(PROGS_ASAN) $(ASAN_OBJ) $(ASAN_DEP)
	rm -f $(PROGS_TSAN) $(TSAN_OBJ) $(TSAN_DEP)

spartan: clean
	@\rm -fr *~

.PHONY: all clean spartan

-include $(NA_LIB_DEP) $(TP_LIB_DEP) $(PROGS_DEP) $(EXTRA_PROGS_DEP) $(ASAN_DEP) $(TSAN_DEP)
