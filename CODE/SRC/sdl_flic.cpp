#include "flicsmk.hpp"

#ifdef OS_SDL

TFlicSmacker::TFlicSmacker()
{
    smk = nullptr;
    soundVolume = 0;
    soundPan = 0;
    activatePalette = false;
    prevVideoMode = 0;
    fFlicDone = true;
    pDecBufCH = nullptr;
    pDecBuf = nullptr;
}

TFlicSmacker::~TFlicSmacker() = default;

int TFlicSmacker::Play(int cineNum, int extraBuf, int simSpeed, int startFrame, bool skipFrames)
{
    (void)cineNum;
    (void)extraBuf;
    (void)simSpeed;
    (void)startFrame;
    (void)skipFrames;
    return 0;
}

void TFlicSmacker::ChangeVolume(SmkScript*, Smack*, u32)
{
}

void TFlicSmacker::ChangePalette(SmkScript*, Smack*, u32)
{
}

void TFlicSmacker::Fader(int)
{
}

void TFlicSmacker::ChangeText(SmkTextScript*, int)
{
}

#endif // OS_SDL
