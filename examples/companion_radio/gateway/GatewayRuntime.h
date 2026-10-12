#pragma once

#include "TelemetryScheduler.h"
#include <stdio.h>

// Local, ignored configuration. Never put real node keys/passwords in defaults.
#if __has_include("gateway.local.h")
#include "gateway.local.h"
#endif
#ifndef GATEWAY_TARGET_KEYS
#define GATEWAY_TARGET_KEYS {nullptr}
#endif
#ifndef GATEWAY_INTERVAL_MS
#define GATEWAY_INTERVAL_MS 900000UL
#endif

namespace gateway {

class GatewayRuntime : public TelemetryScheduler::Transport {
public:
  explicit GatewayRuntime(MyMesh& mesh) : mesh_(mesh), scheduler_(*this) {
    static_assert(PUB_KEY_SIZE == TelemetryScheduler::KeySize, "Unexpected key size");
    static_assert(MAX_PACKET_PAYLOAD - 4 <= TelemetryScheduler::MaxPayload, "Sample buffer too small");
  }
  void begin() {
    const char* keys[] = GATEWAY_TARGET_KEYS;
    for (const char* key : keys) {
      if (key && !scheduler_.addTarget(key)) ++invalid_targets_;
    }
    scheduler_.begin(millis(), GATEWAY_INTERVAL_MS);
    mesh_.setGatewayScheduler(&scheduler_);
  }
  void loop() {
    const uint32_t now = millis();
    scheduler_.tick(now, mesh_.gatewayClockReady());
    if (log_offset_ == log_length_) {
      TelemetryScheduler::Sample sample;
      if (scheduler_.pop(sample)) {
        char key[65], lpp[TelemetryScheduler::MaxPayload * 2 + 1];
        hex(sample.public_key, sizeof(sample.public_key), key);
        hex(sample.lpp, sample.length, lpp);
        setLogLength(snprintf(log_, sizeof(log_),
          "{\"gateway\":\"telemetry\",\"public_key\":\"%s\",\"tag\":%lu,\"received_at\":%lu,\"lpp_hex\":\"%s\"}\n",
          key, (unsigned long)sample.tag, (unsigned long)sample.received_at, lpp));
      } else if (!status_written_ || uint32_t(now - last_status_) >= 60000) {
        const auto& s = scheduler_.stats();
        setLogLength(snprintf(log_, sizeof(log_),
          "{\"gateway\":\"status\",\"clock_ready\":%s,\"targets\":%u,\"invalid_targets\":%u,"
          "\"sent\":%lu,\"received\":%lu,\"timeouts\":%lu,\"send_failed\":%lu,\"dropped\":%lu,\"malformed\":%lu}\n",
          mesh_.gatewayClockReady() ? "true" : "false", (unsigned)scheduler_.targetCount(),
          invalid_targets_, (unsigned long)s.sent, (unsigned long)s.received,
          (unsigned long)s.timeouts, (unsigned long)s.send_failed,
          (unsigned long)s.dropped, (unsigned long)s.malformed));
        last_status_ = now;
        status_written_ = true;
      }
    }
    // USB console diagnostics are drained in short chunks, never in RX callbacks.
    int available = Serial.availableForWrite();
    if (available > 0 && log_offset_ < log_length_) {
      size_t count = log_length_ - log_offset_;
      if (count > 64) count = 64;
      if (count > (size_t)available) count = (size_t)available;
      log_offset_ += Serial.write((const uint8_t*)log_ + log_offset_, count);
    }
  }
  bool sendTelemetry(const uint8_t* key, uint32_t& tag, uint32_t& timeout_ms) override {
    ContactInfo* contact = mesh_.lookupContactByPubKey(key, PUB_KEY_SIZE);
    if (!contact) return false;
    // Preserve Companion pending_* state. This scheduler owns its own correlation.
    return mesh_.sendRequest(*contact, REQ_TYPE_GET_TELEMETRY_DATA, tag, timeout_ms) != MSG_SEND_FAILED;
  }
private:
  static void hex(const uint8_t* bytes, size_t size, char* dest) {
    static const char digits[] = "0123456789abcdef";
    for (size_t i = 0; i < size; ++i) {
      dest[i * 2] = digits[bytes[i] >> 4];
      dest[i * 2 + 1] = digits[bytes[i] & 15];
    }
    dest[size * 2] = 0;
  }
  void setLogLength(int length) {
    log_offset_ = 0;
    log_length_ = length > 0 ? (size_t)length : 0;
    if (log_length_ >= sizeof(log_)) log_length_ = sizeof(log_) - 1;
  }
  MyMesh& mesh_;
  TelemetryScheduler scheduler_;
  unsigned invalid_targets_ = 0;
  char log_[640] = {};
  size_t log_offset_ = 0, log_length_ = 0;
  uint32_t last_status_ = 0;
  bool status_written_ = false;
};

} // namespace gateway
