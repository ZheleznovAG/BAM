#include "sdl_sound.hpp"

SoundMgr* pSoundMgr = nullptr;

SoundMgr::SoundMgr() : hDigiDriverHandle(-1) {
    pSoundMgr = this;
}

SoundMgr::~SoundMgr() {
    pSoundMgr = nullptr;
}

void SoundMgr::Init(char*) {}
void SoundMgr::Cycle() {}
void SoundMgr::Pause() {}
void SoundMgr::Resume() {}
void SoundMgr::SetMasterDigiVolume(int16) {}
int16 SoundMgr::GetMasterDigiVolume() { return 0; }
void SoundMgr::SetMasterMidiVolume(int16) {}
int16 SoundMgr::GetMasterMidiVolume() { return 0; }
void SoundMgr::ShutDown() {}
bool SoundMgr::Save(uint16, FILE*) { return false; }
uint16 SoundMgr::NumberDigiPlaying() { return 0; }
uint16 SoundMgr::NumberMidiPlaying() { return 0; }
grip SoundMgr::OldestDigiPlaying() { return 0; }
grip SoundMgr::NextOldestDigiPlaying() { return 0; }
grip SoundMgr::OldestMidiPlaying() { return 0; }
bool SoundMgr::Fade(uint16, uint32, uint32) { return false; }
void SoundMgr::AutoFade(uint16, uint32, uint32, grip) {}
void SoundMgr::SwapDigiLeftAndRight(bool) {}
short SoundMgr::GetPanPosition(int panPos) { return static_cast<short>(panPos); }

TSound::TSound() {}
TSound::~TSound() {}
void TSound::Play(int, int16, int, grip, int16, bool) {}
void TSound::SetVolume(int16, int, bool) {}
void TSound::Stop() {}
int TSound::IsPlaying() { return 0; }
void TSound::Pause() {}
void TSound::Resume() {}
bool TSound::Fade(uint16, uint32, uint32) { return false; }
void TSound::SetPanPosition(int) {}
TStreamBase* TSound::GetStreamer() { return nullptr; }

TMusic::TMusic() {}
TMusic::~TMusic() {}
void TMusic::Play(uint16, int16, grip) {}
void TMusic::Stop() {}
int TMusic::IsPlaying() { return 0; }
void TMusic::Pause() {}
void TMusic::Resume() {}
void TMusic::SetVolume(int16, int, bool) {}
bool TMusic::Fade(uint16, uint32, uint32) { return false; }

void ShutDownSoundMgr() {}

extern "C" unsigned char SmackSoundUseSOS3(unsigned short, unsigned long) { return 0; }

