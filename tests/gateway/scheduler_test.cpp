#include "../../examples/companion_radio/gateway/TelemetryScheduler.h"
#include <assert.h>
#include <stdio.h>
#include <vector>
#include <array>

using Scheduler = gateway::TelemetryScheduler;
static const char* KeyA = "0101010101010101010101010101010101010101010101010101010101010101";
static const char* KeyB = "0202020202020202020202020202020202020202020202020202020202020202";
struct Radio : Scheduler::Transport {
  bool success = true;
  uint32_t next_tag = 1;
  uint32_t timeout = 1000;
  std::vector<std::array<uint8_t, 32>> sent;
  bool sendTelemetry(const uint8_t* key, uint32_t& tag, uint32_t& timeout_ms) override {
    if (!success) return false;
    std::array<uint8_t, 32> copy;
    memcpy(copy.data(), key, 32);
    sent.push_back(copy);
    tag = next_tag++;
    timeout_ms = timeout;
    return true;
  }
};
static bool response(Scheduler& s, uint8_t keyByte, uint32_t tag, uint32_t now) {
  uint8_t key[32]; memset(key, keyByte, sizeof(key));
  uint8_t frame[] = {uint8_t(tag), uint8_t(tag >> 8), uint8_t(tag >> 16), uint8_t(tag >> 24), 1, 103, 0, 215};
  return s.onResponse(key, frame, sizeof(frame), now, 1800000000);
}

static void clock_and_config() {
  Radio radio; Scheduler s(radio);
  assert(!s.addTarget(nullptr));
  assert(!s.addTarget("abcd"));
  assert(!s.addTarget("zz01010101010101010101010101010101010101010101010101010101010101"));
  assert(s.addTarget(KeyA)); assert(!s.addTarget(KeyA));
  s.begin(0);
  s.tick(29999, true); assert(radio.sent.empty());
  s.tick(30000, false); assert(radio.sent.empty());
  s.tick(30001, true); assert(radio.sent.size() == 1);
  s.tick(30002, true); assert(radio.sent.size() == 1);
}

static void correlation_and_copy() {
  Radio radio; Scheduler s(radio); s.addTarget(KeyA); s.begin(0); s.tick(30000, true);
  assert(!response(s, 2, 1, 30001)); // right tag, wrong full public key
  assert(!response(s, 1, 42, 30001)); // app's tag is left to Companion
  uint8_t key[32]; memset(key, 1, sizeof(key));
  key[31] = 2;
  uint8_t short_data[] = {1, 0, 0};
  assert(!s.onResponse(key, short_data, 3, 30001, 0));
  uint8_t frame[] = {1, 0, 0, 0, 1, 103, 0, 215};
  assert(!s.onResponse(key, frame, sizeof(frame), 30001, 0)); // same prefix, different tail
  key[31] = 1;
  assert(s.onResponse(key, frame, sizeof(frame), 30001, 1800000000));
  memset(frame, 0, sizeof(frame)); // sample owns bytes, not RX buffer pointers
  Scheduler::Sample sample;
  assert(s.pop(sample)); assert(sample.length == 4); assert(sample.lpp[3] == 215);
  assert(sample.tag == 1 && sample.received_at == 1800000000);
  assert(!s.pop(sample));
  assert(response(s, 1, 1, 30002)); // duplicate consumed, not routed to legacy status
  assert(!s.pop(sample)); assert(s.stats().received == 1);
}

static void sequencing_and_timeout() {
  Radio radio; Scheduler s(radio); s.addTarget(KeyA); s.addTarget(KeyB); s.begin(0);
  s.tick(30000, true);
  s.tick(32999, true); assert(s.stats().timeouts == 0);
  s.tick(33000, true); assert(s.stats().timeouts == 1);
  assert(response(s, 1, 1, 33001)); // late response consumed
  s.tick(37999, true); assert(radio.sent.size() == 1);
  s.tick(38000, true); assert(radio.sent.size() == 2 && radio.sent[1][0] == 2);
  assert(response(s, 2, 2, 38001));
  s.tick(938000, true); assert(radio.sent.size() == 2);
  s.tick(938001, true); assert(radio.sent.size() == 3 && radio.sent[2][0] == 1);
}

static void response_at_deadline() {
  Radio radio; Scheduler s(radio); s.addTarget(KeyA); s.begin(0); s.tick(30000, true);
  assert(response(s, 1, 1, 33000));
  assert(s.stats().timeouts == 1 && s.stats().received == 0);
}

static void failures_and_malformed() {
  Radio radio; Scheduler s(radio); s.addTarget(KeyA); s.begin(0, 60000);
  radio.success = false; s.tick(30000, true);
  assert(s.stats().send_failed == 1);
  radio.success = true; s.tick(89999, true); assert(radio.sent.empty());
  s.tick(90000, true);
  uint8_t key[32]; memset(key, 1, sizeof(key));
  uint8_t frame[Scheduler::MaxPayload + 5] = {1, 0, 0, 0};
  assert(s.onResponse(key, frame, sizeof(frame), 90001, 0));
  assert(s.onResponse(key, frame, 4, 90001, 0));
  assert(s.stats().malformed == 2);
  assert(response(s, 1, 1, 90002)); assert(s.stats().received == 1);
}

static void queue_overflow() {
  Radio radio; Scheduler s(radio); s.addTarget(KeyA); s.begin(0, 60000);
  uint32_t now = 30000;
  for (unsigned i = 0; i < Scheduler::QueueSize + 2; ++i) {
    s.tick(now, true); assert(response(s, 1, i + 1, now + 1)); now += 60001;
  }
  assert(s.stats().received == 10 && s.stats().dropped == 2);
  Scheduler::Sample sample;
  for (unsigned i = 0; i < Scheduler::QueueSize; ++i) {
    assert(s.pop(sample)); assert(sample.tag == i + 1);
  }
  assert(!s.pop(sample));
}

static void millis_wrap() {
  Radio radio; Scheduler s(radio); s.addTarget(KeyA);
  const uint32_t boot = UINT32_MAX - 15000;
  s.begin(boot); s.tick(boot + 29999, true); assert(radio.sent.empty());
  s.tick(boot + 30000, true); assert(radio.sent.size() == 1);
  assert(response(s, 1, 1, boot + 30001));
  s.tick(boot + 930000, true); assert(radio.sent.size() == 1);
  s.tick(boot + 930001, true); assert(radio.sent.size() == 2);
}

static void empty_configuration_and_limits() {
  Radio radio; Scheduler s(radio); s.begin(0); s.tick(30000, true); assert(radio.sent.empty());
  for (unsigned i = 0; i < Scheduler::MaxTargets; ++i) {
    char hex[65]; memset(hex, '0' + i, 64); hex[64] = 0; assert(s.addTarget(hex));
  }
  assert(!s.addTarget("8888888888888888888888888888888888888888888888888888888888888888"));
}

int main() {
  clock_and_config(); correlation_and_copy(); sequencing_and_timeout();
  response_at_deadline(); failures_and_malformed(); queue_overflow();
  millis_wrap(); empty_configuration_and_limits();
  puts("8 scheduler scenarios passed");
}
