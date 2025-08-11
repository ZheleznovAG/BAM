#pragma once
#include <cstdio>
#include <cstring>
#include <thread>
#include <queue>
#include <chrono>
#include <SDL2/SDL.h>

// Simple compatibility layer replacing old DOS functions
inline std::queue<SDL_Keycode>& __compat_key_queue() {
    static std::queue<SDL_Keycode> q;
    return q;
}

inline int kbhit() {
    SDL_Event e;
    while (SDL_PollEvent(&e)) {
        if (e.type == SDL_KEYDOWN) {
            __compat_key_queue().push(e.key.keysym.sym);
        }
    }
    return !__compat_key_queue().empty();
}

inline int getch() {
    while (!kbhit()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    int ch = __compat_key_queue().front();
    __compat_key_queue().pop();
    return ch;
}

inline void delay(unsigned int ms) {
    std::this_thread::sleep_for(std::chrono::milliseconds(ms));
}
