#include "dolly_sound_compat_generated.hpp"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iterator>
#include <vector>

using namespace dolly_sound_compat;
static void check(bool value) {
    if (!value) { std::fputs("sound compatibility test failed\n", stderr); std::exit(1); }
}

struct Fixture {
    std::vector<unsigned char> text;
    std::uint32_t text_rva = 0x20000, data_rva = 0x1000, data_size = 0x1000;
    std::size_t offsets[5]{};
    Fixture(bool exact = false) {
        text.resize(exact ? 0x200000 : 0x2000, 0xcc);
        if (exact) { text_rva = 0x1000; data_rva = kVoiceTable & ~0xfff; }
        for (std::size_t i = 0; i < 5; ++i) {
            const auto& s = kSignatures[i];
            offsets[i] = exact ? s.reviewed_rva - text_rva : 0x100 + i * 0x300;
            std::memcpy(text.data() + offsets[i], s.bytes, s.size);
            if (!exact) {
                for (std::size_t j = 0; j < s.size; ++j)
                    if (!s.mask[j]) text[offsets[i] + j] ^= 0xa5;
            }
        }
        for (const auto& ref : kTableReferences) {
            const auto at = offsets[ref.symbol] + ref.offset;
            const std::int32_t displacement = static_cast<std::int32_t>(
                std::int64_t(exact ? kVoiceTable : data_rva + 0x80) - (text_rva + at + ref.size));
            std::memcpy(text.data() + at + ref.displacement, &displacement, 4);
        }
    }
    bool run(Resolution& out, bool exact = false) {
        return resolve(text.data(), text.size(), text_rva, data_rva, data_size,
                       kSignatures, 5, kTableReferences, std::size(kTableReferences),
                       exact, kVoiceTable, out);
    }
};

int main(int argc, char** argv) {
    Resolution out{};
    Fixture exact(true);
    check(exact.run(out, true) && out.voice_table == kVoiceTable);
    check(exact.run(out));
    Fixture relocated;
    check(relocated.run(out) && out.voice_table == relocated.data_rva + 0x80);
    for (std::size_t i = 0; i < 5; ++i)
        check(out.functions[i] == relocated.text_rva + relocated.offsets[i]);
    check(!relocated.run(out, true) && out.voice_table == 0);
    for (std::size_t i = 0; i < 5; ++i) {
        Fixture changed;
        changed.text[changed.offsets[i]] ^= 1;
        check(!changed.run(out) && out.functions[0] == 0);
        Fixture duplicate;
        std::memcpy(duplicate.text.data() + 0x1800,
                    duplicate.text.data() + duplicate.offsets[i], kSignatures[i].size);
        check(!duplicate.run(out));
    }
    Fixture disagree;
    const auto ref = kTableReferences[0];
    const auto operand = disagree.offsets[ref.symbol] + ref.offset + ref.displacement;
    disagree.text[operand] ^= 8;
    check(!disagree.run(out));
    Fixture outside;
    outside.data_rva += 0x1000;
    check(!outside.run(out));
    Fixture unaligned;
    for (const auto& r : kTableReferences)
        unaligned.text[unaligned.offsets[r.symbol] + r.offset + r.displacement] ^= 1;
    check(!unaligned.run(out));
    Fixture truncated;
    truncated.text.resize(truncated.offsets[4] + kSignatures[4].size - 1);
    check(!truncated.run(out));
    exact.text[exact.offsets[4]] ^= 1;
    check(!exact.run(out, true));

    // Optional offline .text snapshot (four uint32 fields then section bytes).
    // No DLL is loaded or executed. Generated locally from the reviewed PE.
    if (argc == 2) {
        std::ifstream stream(argv[1], std::ios::binary);
        check(bool(stream));
        std::uint32_t header[4]{};
        stream.read(reinterpret_cast<char*>(header), sizeof(header));
        std::vector<unsigned char> text((std::istreambuf_iterator<char>(stream)), {});
        check(text.size() == header[1]);
        for (bool mode : {false, true}) {
            check(resolve(text.data(), text.size(), header[0], header[2], header[3],
                          kSignatures, 5, kTableReferences, std::size(kTableReferences),
                          mode, kVoiceTable, out));
            check(out.voice_table == kVoiceTable);
            for (std::size_t i = 0; i < 5; ++i)
                check(out.functions[i] == kSignatures[i].reviewed_rva);
        }
    }
    std::puts("sound compatibility tests passed");
}
