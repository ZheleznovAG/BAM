#include "os.hpp"
#include "apievt.hpp"
#include "apigraph.hpp"
#include "types.hpp"

#include <SDL2/SDL.h>

extern "C" void _Panic(char* msg, char* fileName, int lineNum)
{
    (void)msg;
    (void)fileName;
    (void)lineNum;
}

void OS_ShutDownVideo(int origMode)
{
    (void)origMode;
}

void OS_InitMem() {}

size_t AAvailMem() { return 0; }
size_t ALargestBlock() { return 0; }

bool AIsOnStack(void*) { return false; }

char AScanToASCII(Event)
{
    return 0;
}

uchar* AGetBiosKey() { return nullptr; }

void AQueueUpdate() {}

uint16 AGetEventMods()
{
    return pEventMgr ? pEventMgr->GetModifiers() : 0;
}

ticks_t AGetTicks()
{
    return SDL_GetTicks();
}

void ASetKeyboardVector(bool setup)
{
    (void)setup;
}
