#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct SDL_Window {} SDL_Window;
typedef struct SDL_Renderer {} SDL_Renderer;
typedef struct SDL_Texture {} SDL_Texture;

typedef uint32_t Uint32;
typedef uint8_t Uint8;
typedef int SDL_Keycode;
typedef struct {
    int type;
    struct { struct { SDL_Keycode sym; } keysym; } key;
} SDL_Event;

#define SDL_INIT_VIDEO 0
#define SDL_PIXELFORMAT_INDEX8 0
#define SDL_RENDERER_PRESENTVSYNC 0
#define SDL_TEXTUREACCESS_STREAMING 0
#define SDL_WINDOWPOS_CENTERED 0
#define SDL_KEYDOWN 0
#define SDL_TRUE 1
#define SDL_FALSE 0

static inline int SDL_Init(Uint32 flags) { (void)flags; return 0; }
static inline SDL_Window* SDL_CreateWindow(const char*, int, int, int, int, Uint32) { return 0; }
static inline SDL_Renderer* SDL_CreateRenderer(SDL_Window*, int, Uint32) { return 0; }
static inline SDL_Texture* SDL_CreateTexture(SDL_Renderer*, Uint32, int, int, int) { return 0; }
static inline int SDL_UpdateTexture(SDL_Texture*, const void*, const void*, int) { return 0; }
static inline int SDL_RenderClear(SDL_Renderer*) { return 0; }
static inline int SDL_RenderCopy(SDL_Renderer*, SDL_Texture*, const void*, const void*) { return 0; }
static inline void SDL_RenderPresent(SDL_Renderer*) {}
static inline int SDL_PollEvent(SDL_Event*) { return 0; }
static inline void SDL_Delay(Uint32) {}
static inline Uint32 SDL_GetTicks(void) { return 0; }
static inline Uint32 SDL_GetMouseState(int* x, int* y) { if(x) *x = 0; if(y) *y = 0; return 0; }
static inline int SDL_ShowCursor(int toggle) { return toggle; }
static inline int SDL_WarpMouseGlobal(int x, int y) { (void)x; (void)y; return 0; }

#ifdef __cplusplus
}
#endif
