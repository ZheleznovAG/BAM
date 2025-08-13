#pragma once

#include "types.hpp"
#include <stdio.h>

class TStreamBase;

class TSound {
public:
    TSound();
    ~TSound();

    void Play(int sndNum, int16 sVolume = 0, int panPos = 0,
              grip callBack = 0, int16 loopCnt = 1, bool streamIt = false);
    void SetVolume(int16 sVolume, int panPos = 0, bool updateMax = true);
    void Stop();
    int IsPlaying();
    void Pause();
    void Resume();
    bool Fade(uint16 direction, uint32 currentStep, uint32 totalSteps);
    void SetPanPosition(int panPos);
    TStreamBase* GetStreamer();
};

class TMusic {
public:
    TMusic();
    ~TMusic();

    void Play(uint16 sngNum, int16 mVolume = 0, grip callBack = 0);
    void Stop();
    int IsPlaying();
    void Pause();
    void Resume();
    void SetVolume(int16 sVolume, int panPos = 0, bool updateMax = true);
    bool Fade(uint16 direction, uint32 currentStep, uint32 totalSteps);
};

class SoundMgr {
public:
    SoundMgr();
    ~SoundMgr();

    void Init(char *configFileName = (char*)"sound.cfg");
    void Cycle();

    void Pause();
    void Resume();

    void SetMasterDigiVolume(int16 volume);
    int16 GetMasterDigiVolume();
    void SetMasterMidiVolume(int16 volume);
    int16 GetMasterMidiVolume();

    void ShutDown();

    bool Save(uint16 state, FILE *fp = nullptr);

    uint16 NumberDigiPlaying();
    uint16 NumberMidiPlaying();

    grip OldestDigiPlaying();
    grip NextOldestDigiPlaying();
    grip OldestMidiPlaying();

    bool Fade(uint16 direction, uint32 currentStep, uint32 totalSteps);
    void AutoFade(uint16 direction, uint32 totalSteps, uint32 stepDelay, grip callBack = 0);

    void SwapDigiLeftAndRight(bool swapThem);
    short GetPanPosition(int panPos);

    int hDigiDriverHandle;
};

extern SoundMgr* pSoundMgr;
void ShutDownSoundMgr();

extern "C" unsigned char SmackSoundUseSOS3(unsigned short, unsigned long);

