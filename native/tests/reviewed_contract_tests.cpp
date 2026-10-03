#include "dolly_runtime_generated.hpp"
#include <cstddef>
#include <cstdint>
#include <cstring>
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
namespace {
#include "dolly_follow_anchor_generated.hpp"
}

int main() {
    using namespace dolly::reviewed;
    // Old correction profiles must never acquire the newer pawn member simply
    // because the current Python observer monitor was updated.
    static_assert(FollowTarget::OBSERVER_SERVICES_OFFSET == 0xe98);
    static_assert(sizeof(kFollowAnchorProfiles) / sizeof(*kFollowAnchorProfiles) == 3);
    for (const auto& profile : kFollowAnchorProfiles) {
        assert(profile.observer_services_offset == 0xe40);
        assert(std::strcmp(profile.hash, ReplayCamera::CLIENT_SHA256));
        bool composition = false, blend = false;
        for (std::size_t i = 0; i < profile.count; ++i) {
            const auto& span = profile.spans[i];
            assert(span.rva + span.size <= profile.image_size);
            composition |= span.rva == profile.composition;
            blend |= span.rva == profile.blend;
        }
        assert(composition && blend);
    }
    // A network vector contains metadata between its float components. Verify
    // the shared decoder indices against a fixed layout fixture.
    unsigned char raw[36]{};
    const float expected[] = {12.f, -34.f, 56.f};
    for (unsigned i = 0; i < 3; ++i)
        std::memcpy(raw + 16 + i * 8, expected + i, 4);
    for (unsigned i = 0; i < 3; ++i) {
        float observed = 0;
        std::memcpy(&observed, raw + kViewOffsetComponents[i], 4);
        assert(observed == expected[i]);
    }
    static_assert(static_cast<unsigned>(AttachFieldIndex::scene_node) == 0);
    static_assert(static_cast<unsigned>(AttachFieldIndex::eye_angles) == 5);
    static_assert(static_cast<unsigned>(AttachFieldIndex::scene_sibling) == 7);
}
