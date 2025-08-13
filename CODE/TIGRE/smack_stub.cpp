#include <cstdint>

extern "C" {

struct Smack;

Smack* SmackOpen(char*, std::uint32_t, std::uint32_t) { return nullptr; }
std::uint32_t SmackDoFrame(Smack*) { return 0; }
void SmackNextFrame(Smack*) {}
std::uint32_t SmackWait(Smack*) { return 0; }
void SmackClose(Smack*) {}
void SmackVolumePan(Smack*, std::uint32_t, std::uint32_t, std::uint32_t) {}
std::uint32_t SmackSoundOnOff(Smack*, std::uint32_t) { return 0; }
void SmackToBuffer(Smack*, std::uint32_t, std::uint32_t, std::uint32_t, std::uint32_t, void*, std::uint32_t) {}
std::uint32_t SmackToBufferRect(Smack*, std::uint32_t) { return 0; }
void SmackSimulate(std::uint32_t) {}
unsigned char SmackSoundUseSOS3(unsigned short, unsigned long) { return 0; }

}
