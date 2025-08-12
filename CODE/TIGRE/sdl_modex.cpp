#include "../compat.h"
#include "modex.hpp"
#include "apigraph.hpp"
#include "types.hpp"
#include <SDL2/SDL.h>
#include <vector>
#include <cstring>

using namespace std;

static SDL_Window* gWindow = nullptr;
static SDL_Renderer* gRenderer = nullptr;
static SDL_Texture* gTexture = nullptr;
static vector<uint8> gPages;

extern "C" {
    uchar* pVGAMem = nullptr;
    uchar* pVGAMemPage0 = nullptr;
    uchar* pVGAMemPage1 = nullptr;
    uint16 curDrawPage = 0;
}

static void ensureInit()
{
    if(!gWindow)
    {
        SDL_Init(SDL_INIT_VIDEO);
        gWindow = SDL_CreateWindow("BAM",
            SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
            SCREEN_WIDTH, SCREEN_HEIGHT, 0);
        gRenderer = SDL_CreateRenderer(gWindow, -1, SDL_RENDERER_PRESENTVSYNC);
        gTexture = SDL_CreateTexture(gRenderer, SDL_PIXELFORMAT_INDEX8,
            SDL_TEXTUREACCESS_STREAMING, SCREEN_WIDTH, SCREEN_HEIGHT);
        gPages.resize(2 * SCREEN_WIDTH * SCREEN_HEIGHT);
        pVGAMemPage0 = gPages.data();
        pVGAMemPage1 = gPages.data() + SCREEN_WIDTH * SCREEN_HEIGHT;
        curDrawPage = 0;
        pVGAMem = pVGAMemPage0;
    }
}

void SetXMode(void)
{
    ensureInit();
}

void XModeFlipPage(void)
{
    ensureInit();
    uchar* current = (curDrawPage == 0) ? pVGAMemPage0 : pVGAMemPage1;
    SDL_UpdateTexture(gTexture, nullptr, current, SCREEN_WIDTH);
    SDL_RenderClear(gRenderer);
    SDL_RenderCopy(gRenderer, gTexture, nullptr, nullptr);
    SDL_RenderPresent(gRenderer);

    curDrawPage ^= 1;
    pVGAMem = (curDrawPage == 0) ? pVGAMemPage0 : pVGAMemPage1;
}

void FillScreen(int penNum)
{
    ensureInit();
    memset(pVGAMem, penNum & 0xFF, SCREEN_WIDTH * SCREEN_HEIGHT);
}

void SyncWithVBL(void)
{
    SDL_Delay(16);
}

void ABlit(uint driver, uchar* pData, coord x, coord y,
           uint bufWidth, uint bufHeight, uint bufSpan, uint vSeg)
{
    (void)driver; (void)vSeg;
    ensureInit();
    for(uint row = 0; row < bufHeight; ++row)
    {
        memcpy(pVGAMem + (y + row) * SCREEN_WIDTH + x,
               pData + row * bufSpan,
               bufWidth);
    }
}

void ARBlit(uint driver, uchar* pData, coord x, coord y,
           uint bufWidth, uint bufHeight, uint vSeg)
{
    (void)driver; (void)vSeg;
    ensureInit();
    uchar* source = (curDrawPage == 0) ? pVGAMemPage0 : pVGAMemPage1;
    for(uint row = 0; row < bufHeight; ++row)
    {
        memcpy(pData + row * bufWidth,
               source + (y + row) * SCREEN_WIDTH + x,
               bufWidth);
    }
}

