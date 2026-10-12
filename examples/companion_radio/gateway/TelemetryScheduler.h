#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace gateway {

// No Arduino or radio dependencies: all calls run on the mesh loop task.
class TelemetryScheduler {
public:
  static constexpr size_t KeySize = 32;
  static constexpr size_t MaxTargets = 8;
  static constexpr size_t MaxPayload = 180;
  static constexpr size_t QueueSize = 8;
  struct Sample {
    uint8_t public_key[KeySize];
    uint32_t tag;
    uint32_t received_at;
    uint8_t length;
    uint8_t lpp[MaxPayload];
  };
  struct Stats {
    uint32_t sent = 0, received = 0, timeouts = 0, send_failed = 0;
    uint32_t dropped = 0, malformed = 0;
  };
  class Transport {
  public:
    virtual ~Transport() = default;
    virtual bool sendTelemetry(const uint8_t* key, uint32_t& tag, uint32_t& timeout_ms) = 0;
  };

  explicit TelemetryScheduler(Transport& transport) : transport_(transport) {}

  bool addTarget(const char* hex) {
    if (!hex || strlen(hex) != KeySize * 2 || target_count_ == MaxTargets) return false;
    uint8_t key[KeySize];
    for (size_t i = 0; i < KeySize; ++i) {
      int hi = nibble(hex[i * 2]), lo = nibble(hex[i * 2 + 1]);
      if (hi < 0 || lo < 0) return false;
      key[i] = static_cast<uint8_t>((hi << 4) | lo);
    }
    for (size_t i = 0; i < target_count_; ++i) {
      if (memcmp(targets_[i], key, KeySize) == 0) return false;
    }
    memcpy(targets_[target_count_++], key, KeySize);
    return true;
  }

  // Call once at boot. A fresh time synchronization is required before any send.
  void begin(uint32_t now, uint32_t interval_ms = 900000) {
    interval_ = interval_ms >= 60000 && interval_ms <= 86400000 ? interval_ms : 900000;
    next_action_ = now + 30000;
  }

  void tick(uint32_t now, bool clock_ready) {
    if (waiting_) {
      if (due(now, deadline_)) {
        ++stats_.timeouts;
        finish(now);
      }
      return;
    }
    if (!clock_ready || target_count_ == 0 || !due(now, next_action_)) return;
    uint32_t tag = 0, timeout_ms = 0;
    if (!transport_.sendTelemetry(targets_[target_index_], tag, timeout_ms)) {
      ++stats_.send_failed;
      finish(now);
      return;
    }
    // Keep completed/expired requests too, so late replies cannot be mistaken
    // for the Companion's legacy status/login responses from this contact.
    History& entry = history_[history_index_];
    memcpy(entry.public_key, targets_[target_index_], KeySize);
    entry.tag = tag;
    entry.valid = true;
    active_history_ = history_index_;
    history_index_ = (history_index_ + 1) % HistorySize;
    waiting_ = true;
    // Saturate the estimate; deadlines must stay within signed millis range.
    if (timeout_ms > 300000) timeout_ms = 300000;
    deadline_ = now + timeout_ms + 2000;
    ++stats_.sent;
  }

  // True means this belongs to the gateway, including duplicate/late replies.
  bool onResponse(const uint8_t* key, const uint8_t* data, size_t len,
                  uint32_t now, uint32_t received_at) {
    if (len < 4) return false;
    uint32_t tag = uint32_t(data[0]) | (uint32_t(data[1]) << 8) |
                   (uint32_t(data[2]) << 16) | (uint32_t(data[3]) << 24);
    for (size_t i = 0; i < HistorySize; ++i) {
      const History& entry = history_[i];
      if (!entry.valid || entry.tag != tag || memcmp(entry.public_key, key, KeySize)) continue;
      if (!waiting_ || i != active_history_) return true;
      if (due(now, deadline_)) {
        ++stats_.timeouts;
        finish(now);
        return true;
      }
      if (len <= 4 || len - 4 > MaxPayload) {
        ++stats_.malformed;
        return true;
      }
      if (queued_ == QueueSize) {
        ++stats_.dropped; // bounded RAM, discard the newest sample on overflow
      } else {
        Sample& sample = samples_[(head_ + queued_) % QueueSize];
        memcpy(sample.public_key, key, KeySize);
        sample.tag = tag;
        sample.received_at = received_at;
        sample.length = static_cast<uint8_t>(len - 4);
        memcpy(sample.lpp, data + 4, sample.length);
        ++queued_;
      }
      ++stats_.received;
      finish(now);
      return true;
    }
    return false;
  }

  bool pop(Sample& sample) {
    if (!queued_) return false;
    sample = samples_[head_];
    head_ = (head_ + 1) % QueueSize;
    --queued_;
    return true;
  }
  const Stats& stats() const { return stats_; }
  size_t targetCount() const { return target_count_; }

private:
  static constexpr size_t HistorySize = 16;
  struct History { uint8_t public_key[KeySize]; uint32_t tag; bool valid = false; };
  static int nibble(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
  }
  static bool due(uint32_t now, uint32_t deadline) { return int32_t(now - deadline) >= 0; }
  void finish(uint32_t now) {
    waiting_ = false;
    if (++target_index_ >= target_count_) {
      target_index_ = 0;
      next_action_ = now + interval_;
    } else {
      next_action_ = now + 5000;
    }
  }
  Transport& transport_;
  uint8_t targets_[MaxTargets][KeySize] = {};
  size_t target_count_ = 0, target_index_ = 0;
  uint32_t interval_ = 900000, next_action_ = 0, deadline_ = 0;
  bool waiting_ = false;
  History history_[HistorySize] = {};
  size_t history_index_ = 0, active_history_ = 0;
  Sample samples_[QueueSize] = {};
  size_t head_ = 0, queued_ = 0;
  Stats stats_;
};

} // namespace gateway
