#include <SDL.h>
#include <cassert>
#include <fstream>
#include <string>

int main() {
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        return 1;
    }
    SDL_Quit();

    std::string path = std::string(TEST_ASSET_DIR) + "/1.BNK";
    std::ifstream file(path, std::ios::binary);
    assert(file.good());
    return 0;
}
