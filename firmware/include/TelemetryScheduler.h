#pragma once

// Portable, non-blocking sequential poll scheduler for MeshCore telemetry.
// This module intentionally does not send radio packets itself.
// Wire callbacks to MyMesh::sendRequest() and onContactResponse() in the firmware fork.
#include <stddef.h>
#include <stdint.h>

namespace cloud_gateway {

struct PollTarget {
  const char* name;
  const uint8_t* public_key;
  size_t public_key_size;
};

enum class PollState : uint8_t { Idle, AwaitingReply };

class TelemetryScheduler {
 public:
  static constexpr uint32_t kDefaultIntervalMs = 15UL * 60UL * 1000UL;
  static constexpr uint32_t kDefaultTimeoutMs = 30UL * 1000UL;

  TelemetryScheduler(const PollTarget* targets, size_t count,
                     uint32_t interval_ms = kDefaultIntervalMs,
                     uint32_t timeout_ms = kDefaultTimeoutMs)
      : targets_(targets), count_(count), interval_ms_(interval_ms),
        timeout_ms_(timeout_ms) {}

  // Must be called from the main radio loop. Returns the target to query
  // exactly once per cycle; caller must invoke markSent() after sendRequest().
  const PollTarget* next(uint32_t now_ms, bool companion_busy) {
    if (companion_busy || state_ != PollState::Idle || count_ == 0) return nullptr;
    if (!due_ && static_cast<uint32_t>(now_ms - last_cycle_ms_) < interval_ms_)
      return nullptr;
    due_ = true;
    return &targets_[index_];
  }

  // Pass the tag returned by MeshCore sendRequest() only after successful send.
  void markSent(uint32_t now_ms, uint32_t request_tag) {
    tag_ = request_tag;
    started_ms_ = now_ms;
    state_ = PollState::AwaitingReply;
  }

  // Call when the radio reply has been verified as belonging to our request.
  // Returns true only when it completed the outstanding autonomous request.
  bool markReply(uint32_t now_ms, uint32_t response_tag) {
    if (state_ != PollState::AwaitingReply || response_tag != tag_) return false;
    advance(now_ms);
    return true;
  }

  // Returns true on timeout; caller can log the missing reply.
  bool tick(uint32_t now_ms) {
    if (state_ != PollState::AwaitingReply ||
        static_cast<uint32_t>(now_ms - started_ms_) < timeout_ms_) return false;
    advance(now_ms);
    return true;
  }

  void pauseForCompanion(uint32_t now_ms) {
    // Abort local tracking when an app request takes precedence.
    if (state_ == PollState::AwaitingReply) advance(now_ms);
  }

  PollState state() const { return state_; }
  size_t currentIndex() const { return index_; }
  uint32_t expectedTag() const { return tag_; }

 private:
  void advance(uint32_t now_ms) {
    state_ = PollState::Idle;
    tag_ = 0;
    if (++index_ >= count_) {
      index_ = 0;
      last_cycle_ms_ = now_ms;
      due_ = false;
    }
  }

  const PollTarget* targets_;
  size_t count_;
  uint32_t interval_ms_;
  uint32_t timeout_ms_;
  size_t index_ = 0;
  uint32_t started_ms_ = 0;
  uint32_t last_cycle_ms_ = 0;
  uint32_t tag_ = 0;
  bool due_ = true; // first poll immediately after boot
  PollState state_ = PollState::Idle;
};

} // namespace cloud_gateway
