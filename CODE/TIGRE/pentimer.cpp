#include "../compat.h"
#include "pentimer.hpp"

uint32 ReadPentiumTimer()
{
    return SDL_GetTicks();
}
