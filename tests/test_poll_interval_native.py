import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class PollIntervalTests(unittest.TestCase):
    def test_runtime_interval_validation_and_scheduler(self):
        compiler = shutil.which('c++')
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'test.cpp'
            source.write_text(r'''
#include "TelemetryScheduler.h"
#include <cassert>
#include <initializer_list>
using namespace cloud_gateway;
int main() {
  assert(pollIntervalMs(10) == 600000UL);
  assert(pollIntervalMs(0) == 600000UL);
  assert(pollIntervalMs(1441) == 600000UL);
  assert(pollIntervalMs(1440) == 86400000UL);
  uint32_t minutes = 7;
  for (const char* bad : {"", "0", "-1", "1.5", "10minutes", "1441", "99999999999999999999999"}) {
    assert(!parsePollMinutes(bad, minutes));
    assert(minutes == 7);
  }
  assert(parsePollMinutes("10", minutes) && minutes == 10);
  uint8_t key[] = {1}; PollTarget target = {"test",key,1};
  TelemetryScheduler scheduler(&target,1);
  assert(scheduler.intervalMs() == 600000UL);
  assert(scheduler.next(0,false)); scheduler.markSent(0,42);
  assert(scheduler.markReply(100,42));
  assert(!scheduler.next(600099,false));
  assert(scheduler.next(600100,false));
  scheduler.markSent(600100,43); scheduler.markReply(600200,43);
  scheduler.setIntervalMs(pollIntervalMs(20));
  assert(!scheduler.next(1800199,false));
  assert(scheduler.next(1800200,false));
  scheduler.setIntervalMs(0); assert(scheduler.intervalMs() == 1200000UL);
  TelemetryScheduler rollover(&target,1,pollIntervalMs(10),30000);
  rollover.next(0xfffffff0UL,false); rollover.markSent(0xfffffff0UL,1);
  rollover.markReply(0xfffffff5UL,1);
  assert(!rollover.next(uint32_t(0xfffffff5UL + 599999UL),false));
  assert(rollover.next(uint32_t(0xfffffff5UL + 600000UL),false));
}
''')
            exe = Path(tmp) / 'test'
            subprocess.run([compiler,'-std=c++11','-Wall','-Wextra','-Werror',
                            '-I'+str(root/'firmware/include'),str(source),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
