#pragma once
#include <cstdint>

namespace dolly {
// Optional hook for the pinned Deadlock soundsystem.dll. The caller verifies
// the complete module fingerprint before passing its loaded base address.
bool sound_capture_install(void* module) noexcept;
bool sound_capture_available() noexcept;
void sound_capture_clock(std::int32_t tick, double engine_seconds) noexcept;
bool sound_capture_start(const wchar_t* csv_path) noexcept;
void sound_capture_stop() noexcept;
void sound_capture_worker_tick() noexcept;
std::uint64_t sound_capture_dropped() noexcept;
const char* sound_capture_error() noexcept;
}
