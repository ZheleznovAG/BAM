#include "../compat.h"
#include "api.hpp"
#include "apigraph.hpp"
#include "apimem.hpp"
#include "graphmgr.hpp"
#include "palette.hpp"
#include "modex.hpp"
#include <SDL2/SDL.h>
#include <cstring>

// Simple SDL based platform layer used for building on modern systems.

static Gun gCurrentPalette[256];
static int gScreenMode = MODEX_320X400;

void AInitializePlatform()
{
    SDL_Init(SDL_INIT_VIDEO);
}

int AInitGraphics(GraphicsMgr* pGM, uint mode)
{
    if(!ADetectVGA())
    {
        APanic("VGA card not found.");
    }

    pGM->vgaDriver = mode;

    if(!AInitVideo(pGM->vgaDriver, mode, pGM->videoBufferSeg,
                   pGM->maxX, pGM->maxY, pGM->vgaBankNoIncrement,
                   pGM->vidMode))
    {
        APanic("Can't init video.");
    }

    --pGM->maxX;
    --pGM->maxY;
    return mode;
}

int ADetectVGA()
{
    // SDL assumes a modern display is available.
    return 1;
}

bool AInitVideo(uint driver, uint mode, uint& vSeg,
                coord& vWide, coord& vHigh, uint& bankInc, uint& origMode)
{
    (void)driver;
    (void)vSeg;
    (void)bankInc;

    if(!origMode)
        origMode = gScreenMode;

    gScreenMode = mode;

    if(mode == MODEX_320X400)
    {
        SetXMode();
        vWide = SCREEN_WIDTH;
        vHigh = SCREEN_HEIGHT;
        return true;
    }
    return false;
}

int OS_GetScreenMode()
{
    return gScreenMode;
}

void OS_SetPalette(Gun* gunsArray, uint startGun, uint endGun)
{
    if(endGun >= 256) endGun = 255;
    for(uint i = startGun; i <= endGun; ++i)
    {
        gCurrentPalette[i] = gunsArray[i - startGun];
    }
}

void OS_GetPalette(Gun* gunsArray, uint startGun, uint endGun)
{
    if(endGun >= 256) endGun = 255;
    for(uint i = startGun; i <= endGun; ++i)
    {
        gunsArray[i - startGun] = gCurrentPalette[i];
    }
}

bitmap_t ACreateBitMap(coord w, coord h)
{
    return AMalloc(w * h);
}

void ADestroyBitMap(bitmap_t bm)
{
    if(bm)
        AFree(bm);
}

uchar* ADerefBitMap(bitmap_t bm)
{
    return ADerefAs(uchar, bm);
}

