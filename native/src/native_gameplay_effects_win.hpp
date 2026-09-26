// Included inside bridge_win.cpp's anonymous namespace. The reviewed game's
// post-process controller still evaluates selected-player damage/death events
// in Free Cam. Filter their render weights, not their queues or scene grading.
// Event records and scene grading are untouched; F9/POV resumes original weights.
#pragma once

constexpr char kGameplayEffectsClientHash[] =
    "cb831d124403ee2f3afa54981e69d8acf71251ba1129d0733757251f74a157c2";
constexpr std::uintptr_t kGameplayEffectsController = 0x2df4cf0;
constexpr std::uintptr_t kGameplayEffectWeight = 0x7ed690;
constexpr std::uintptr_t kGameplayEffectWeightCaller = 0x7f734d;
constexpr unsigned char kGameplayEffectWeightBytes[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x57, 0x48,
                                                        0x83, 0xec, 0x60, 0x48, 0x8b, 0xd9, 0x33};
constexpr unsigned char kGameplayEffectCallBytes[] = {0xe8, 0x43, 0x63, 0xff, 0xff};
using GameplayEffectWeightFn = float(__fastcall*)(void*);
GameplayEffectWeightFn gOriginalGameplayEffectWeight = nullptr;
std::atomic<bool> gGameplayCameraActive{false};

// The reviewed render-graph option controls only screen-space particles,
// including the selected hero's damage/low-health borders. World particles
// have a separate pass. Disable drawing, keeping simulation alive for F9/POV.
constexpr std::uintptr_t kGameplayRenderOption = 0x576fd0;
constexpr std::uintptr_t kGameplayScreenParticlesCaller = 0x5a7304;
constexpr unsigned char kGameplayRenderOptionBytes[] = {
    0x66, 0x0f, 0x6e, 0xca, 0x4c, 0x8d, 0x1d, 0xa5, 0x45, 0x9f, 0x02, 0x66, 0x0f, 0x70, 0xc9, 0x00};
constexpr unsigned char kGameplayScreenParticlesCallBytes[] = {0xe8, 0xcc, 0xfc, 0xfc, 0xff};
using GameplayRenderOptionFn = int(__fastcall*)(void*, std::uint32_t, int);
GameplayRenderOptionFn gOriginalGameplayRenderOption = nullptr;

static bool gameplay_camera_owns_view(const Command* command, bool active, bool healthy) noexcept {
    return active && healthy && command && !(command->wire.flags & kGamePov) &&
           command->wire.mode != std::uint32_t(Mode::Release);
}

static bool gameplay_camera_active() noexcept {
    const auto command = std::atomic_load_explicit(&gCommand, std::memory_order_acquire);
    return gameplay_camera_owns_view(command.get(), gGameplayCameraActive.load(),
                                     !gWorkerError.load() &&
                                         now_seconds() - gHeartbeatTime.load() < 2.0);
}

static int gameplay_render_option(void* options, std::uint32_t key, int fallback,
                                  std::uintptr_t caller) noexcept {
    if (caller == gClient + kGameplayScreenParticlesCaller && gameplay_camera_active())
        return 0;
    return gOriginalGameplayRenderOption(options, key, fallback);
}

__declspec(noinline) static int __fastcall gameplay_render_option_hook(void* options,
                                                                       std::uint32_t key,
                                                                       int fallback) {
#if defined(_MSC_VER)
    const auto caller = reinterpret_cast<std::uintptr_t>(_ReturnAddress());
#else
    const auto caller = reinterpret_cast<std::uintptr_t>(__builtin_return_address(0));
#endif
    return gameplay_render_option(options, key, fallback, caller);
}

static bool gameplay_damage_or_death(std::uintptr_t controller, std::uintptr_t row) noexcept {
    // The controller's Damaged and Killed vectors are the first two of six.
    // Each vector has a 32-byte event row. Other game-state effects and calls
    // outside the controller's render update always keep the game's result.
    for (unsigned i = 0; i < 2; ++i) {
        const auto vector = controller + 0x20 + i * 0x28;
        std::int32_t count = 0;
        std::uintptr_t first = 0;
        if (!read_value(vector, count) || count <= 0 || count > 4096 ||
            !read_value(vector + 8, first) || first < 0x10000 || row < first)
            continue;
        const auto offset = row - first;
        if (offset < std::uintptr_t(count) * 32 && offset % 32 == 0)
            return true;
    }
    return false;
}

static float gameplay_effect_weight(void* effect, std::uintptr_t caller) noexcept {
    if (caller == gClient + kGameplayEffectWeightCaller && gameplay_camera_active() &&
        gameplay_damage_or_death(gClient + kGameplayEffectsController,
                                 reinterpret_cast<std::uintptr_t>(effect)))
        return 0.0f;
    return gOriginalGameplayEffectWeight(effect);
}

__declspec(noinline) static float __fastcall gameplay_effect_weight_hook(void* effect) {
#if defined(_MSC_VER)
    const auto caller = reinterpret_cast<std::uintptr_t>(_ReturnAddress());
#else
    const auto caller = reinterpret_cast<std::uintptr_t>(__builtin_return_address(0));
#endif
    return gameplay_effect_weight(effect, caller);
}

static bool install_gameplay_effect_filter(HMODULE client) {
    // Optional for older reviewed camera profiles. Never use these addresses
    // for a signature-only camera match or a different client fingerprint.
    if (!module_matches(client, kGameplayEffectsClientHash, 0x3cd0000))
        return true;
    unsigned char weight[sizeof(kGameplayEffectWeightBytes)]{};
    unsigned char caller[sizeof(kGameplayEffectCallBytes)]{};
    unsigned char option[sizeof(kGameplayRenderOptionBytes)]{};
    unsigned char screen_call[sizeof(kGameplayScreenParticlesCallBytes)]{};
    if (!read_memory(gClient + kGameplayEffectWeight, weight, sizeof(weight)) ||
        std::memcmp(weight, kGameplayEffectWeightBytes, sizeof(weight)) ||
        !read_memory(gClient + kGameplayEffectWeightCaller - sizeof(caller), caller,
                     sizeof(caller)) ||
        std::memcmp(caller, kGameplayEffectCallBytes, sizeof(caller)) ||
        !read_memory(gClient + kGameplayRenderOption, option, sizeof(option)) ||
        std::memcmp(option, kGameplayRenderOptionBytes, sizeof(option)) ||
        !read_memory(gClient + kGameplayScreenParticlesCaller - sizeof(screen_call), screen_call,
                     sizeof(screen_call)) ||
        std::memcmp(screen_call, kGameplayScreenParticlesCallBytes, sizeof(screen_call)))
        return false;
    auto target = reinterpret_cast<void*>(gClient + kGameplayEffectWeight);
    return MH_CreateHook(target, reinterpret_cast<void*>(gameplay_effect_weight_hook),
                         reinterpret_cast<void**>(&gOriginalGameplayEffectWeight)) == MH_OK &&
           MH_EnableHook(target) == MH_OK &&
           MH_CreateHook(reinterpret_cast<void*>(gClient + kGameplayRenderOption),
                         reinterpret_cast<void*>(gameplay_render_option_hook),
                         reinterpret_cast<void**>(&gOriginalGameplayRenderOption)) == MH_OK &&
           MH_EnableHook(reinterpret_cast<void*>(gClient + kGameplayRenderOption)) == MH_OK;
}
