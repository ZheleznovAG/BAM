#include "../compat.h"
#include "mouse.hpp"
#include "tigre.hpp"
#include <SDL2/SDL.h>

Mouse* pMouse = nullptr;

Mouse::Mouse()
{
    status = MST_NO_RES;
    mickeysLeftX = mickeysLeftY = 0;
    lastX = lastY = 0;
    hideCount = 1; // start hidden
    screenLimits.Set(0,0,0,0);
    mouseLimits.Set(0,0,0,0);
    rClickDrag.Set(-1,-1,-1,-1);
    rCurrentFence.Set(-1,-1,-1,-1);
    fDragMode = false;
    if(!pMouse) pMouse = this;
}

Mouse::~Mouse()
{
    if(pMouse == this) pMouse = nullptr;
}

void Mouse::Init(coord x1, coord y1, coord x2, coord y2)
{
    screenLimits.Set(x1,y1,x2,y2);
    rClickDrag.Set(-1,-1,-1,-1);
    fDragMode = false;
    coord newX = (x1 + x2) / 2;
    coord newY = (y1 + y2) / 2;
    SetX(newX);
    SetY(newY);
    lastX = newX;
    lastY = newY;
    SetLimits(&screenLimits);
    status &= ~MST_NO_RES;
    if(!hideCount) ShowPointer();
}

void Mouse::SetLimits(Rectangle* rect)
{
    if(rect) mouseLimits = *rect;
    CheckBounds();
}

bool Mouse::CheckBounds()
{
    bool changed = false;
    if(x < mouseLimits.x1) { x = mouseLimits.x1; changed = true; }
    if(x > mouseLimits.x2) { x = mouseLimits.x2; changed = true; }
    if(y < mouseLimits.y1) { y = mouseLimits.y1; changed = true; }
    if(y > mouseLimits.y2) { y = mouseLimits.y2; changed = true; }
    return changed;
}

void Mouse::Show()
{
    if(hideCount && --hideCount == 0)
        ShowPointer();
}

void Mouse::Hide()
{
    if(hideCount++ == 0)
        HidePointer();
}

void Mouse::GetPos(Message* pMsg)
{
    if(pMsg)
    {
        pMsg->event.x = GetX();
        pMsg->event.y = GetY();
    }
}

void Mouse::SetPos(coord setX, coord setY)
{
    SetX(setX);
    SetY(setY);
}

int Mouse::ForceShow(int16 newHideCount)
{
    int old = hideCount;
    hideCount = newHideCount;
    if(hideCount == 0) ShowPointer();
    else HidePointer();
    return old;
}

void Mouse::SetDraggableRect(int x1, int y1, int x2, int y2)
{
    rClickDrag.Set(x1, y1, x2, y2);
}

int Mouse::GetFenceStartX(void)
{
    return rCurrentFence.x1;
}

int Mouse::GetFenceStartY(void)
{
    return rCurrentFence.y1;
}

void Mouse::SetFence(int X1, int Y1, int X2, int Y2)
{
    rCurrentFence.Set(X1,Y1,X2,Y2);
}

void Mouse::DrawFence(void)
{
}

void Mouse::EraseFence(void)
{
}

void Mouse::ClearMickeys()
{
    mickeysLeftX = mickeysLeftY = 0;
}

class SDLMouse : public Mouse
{
public:
    SDLMouse()
        : resType((res_t)0), resNum(0), cel(1), scale(256)
    {
        if(!pMouse) pMouse = this;
    }

    ~SDLMouse() override
    {
        if(pMouse == this) pMouse = nullptr;
    }

    void EnableDragging(bool fNewState) override { fDragMode = fNewState; }

    coord GetX() override { SDL_GetMouseState(&x, &y); return x; }
    coord GetY() override { SDL_GetMouseState(&x, &y); return y; }

    void SetX(coord setX) override
    {
        x = setX;
        SDL_WarpMouseGlobal(x, y);
    }

    void SetY(coord setY) override
    {
        y = setY;
        SDL_WarpMouseGlobal(x, y);
    }

    int GetCel() override { return cel; }
    res_t GetResType() override { return resType; }
    uint GetResNum() override { return resNum; }

    void MovePointer() override {}
    void UpdatePointer() override {}

    void SetRes(res_t type, uint num, uint iCel = 1, uint iScale = 256) override
    {
        resType = type;
        resNum = num;
        cel = iCel;
        scale = iScale;
    }

    void SetFenceRes(res_t, uint, uint, res_t, uint, uint) override {}

    void HideFence(void) override {}

    void SetPri(int32) override {}
    void SetScale(uint newScale) override { scale = newScale; }

    void Pause(bool) override {}
    bool Protect(bool, Rectangle*) override { return true; }
    bool Save(uint16, FILE*) override { return true; }

protected:
    void ShowPointer() override { SDL_ShowCursor(SDL_TRUE); }
    void HidePointer() override { SDL_ShowCursor(SDL_FALSE); }

private:
    res_t resType;
    uint resNum;
    int cel;
    uint scale;
};

static SDLMouse gSDLMouse;

