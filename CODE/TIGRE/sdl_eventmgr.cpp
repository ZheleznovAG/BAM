#include "../compat.h"
#include "eventmgr.hpp"
#include "context.hpp"
#include "periodic.hpp"
#include "apievt.hpp"
#include <SDL2/SDL.h>
#include <cstring>

// Stub mouse pointer for code that expects it, but no DOS mouse implementation.
class Mouse; // forward declaration
Mouse* pMouse = nullptr;

EventMgr* pEventMgr = nullptr;

static uint16 g_bios_key_status = 0;
static coord gMouseX = 0;
static coord gMouseY = 0;

static Uint32 TimerCallback(Uint32 interval, void*)
{
    SDL_Event e;
    SDL_memset(&e, 0, sizeof(e));
    e.type = SDL_USEREVENT;
    SDL_PushEvent(&e);
    return interval;
}

static uint8 SDLScancodeToKey(SDL_Scancode sc)
{
    switch(sc)
    {
        case SDL_SCANCODE_UP: return K_UP;
        case SDL_SCANCODE_DOWN: return K_DOWN;
        case SDL_SCANCODE_LEFT: return K_LEFT;
        case SDL_SCANCODE_RIGHT: return K_RIGHT;
        case SDL_SCANCODE_RSHIFT: return K_RIGHT_SHIFT;
        case SDL_SCANCODE_LSHIFT: return K_LEFT_SHIFT;
        case SDL_SCANCODE_LALT:
        case SDL_SCANCODE_RALT: return K_ALT;
        case SDL_SCANCODE_LCTRL:
        case SDL_SCANCODE_RCTRL: return K_CTRL;
        case SDL_SCANCODE_CAPSLOCK: return K_CAPS;
        case SDL_SCANCODE_TAB: return K_TAB;
        case SDL_SCANCODE_RETURN: return K_ENTER;
        case SDL_SCANCODE_DELETE: return K_DEL;
        case SDL_SCANCODE_PAUSE: return K_BREAK;
        case SDL_SCANCODE_INSERT: return K_INSERT;
        case SDL_SCANCODE_BACKSPACE: return K_BACK_SPACE;
        case SDL_SCANCODE_SPACE: return K_SPACE;
        case SDL_SCANCODE_PAGEUP: return K_PAGE_UP;
        case SDL_SCANCODE_PAGEDOWN: return K_PAGE_DOWN;
        case SDL_SCANCODE_HOME: return K_HOME;
        case SDL_SCANCODE_END: return K_END;
        case SDL_SCANCODE_ESCAPE: return K_ESC;
        case SDL_SCANCODE_LEFTBRACKET: return K_LEFT_BRACKET;
        case SDL_SCANCODE_RIGHTBRACKET: return K_RIGHT_BRACKET;
        case SDL_SCANCODE_SEMICOLON: return K_SEMICOLON;
        case SDL_SCANCODE_APOSTROPHE: return K_QUOTE;
        case SDL_SCANCODE_GRAVE: return K_GRAVE;
        case SDL_SCANCODE_COMMA: return K_COMMA;
        case SDL_SCANCODE_PERIOD: return K_PERIOD;
        case SDL_SCANCODE_SLASH: return K_SLASH;
        case SDL_SCANCODE_BACKSLASH: return K_BACKSLASH;
        case SDL_SCANCODE_PRINTSCREEN: return K_PRINT_SCREEN;
        case SDL_SCANCODE_A: return K_A;
        case SDL_SCANCODE_B: return K_B;
        case SDL_SCANCODE_C: return K_C;
        case SDL_SCANCODE_D: return K_D;
        case SDL_SCANCODE_E: return K_E;
        case SDL_SCANCODE_F: return K_F;
        case SDL_SCANCODE_G: return K_G;
        case SDL_SCANCODE_H: return K_H;
        case SDL_SCANCODE_I: return K_I;
        case SDL_SCANCODE_J: return K_J;
        case SDL_SCANCODE_K: return K_K;
        case SDL_SCANCODE_L: return K_L;
        case SDL_SCANCODE_M: return K_M;
        case SDL_SCANCODE_N: return K_N;
        case SDL_SCANCODE_O: return K_O;
        case SDL_SCANCODE_P: return K_P;
        case SDL_SCANCODE_Q: return K_Q;
        case SDL_SCANCODE_R: return K_R;
        case SDL_SCANCODE_S: return K_S;
        case SDL_SCANCODE_T: return K_T;
        case SDL_SCANCODE_U: return K_U;
        case SDL_SCANCODE_V: return K_V;
        case SDL_SCANCODE_W: return K_W;
        case SDL_SCANCODE_X: return K_X;
        case SDL_SCANCODE_Y: return K_Y;
        case SDL_SCANCODE_Z: return K_Z;
        case SDL_SCANCODE_1: return K_1;
        case SDL_SCANCODE_2: return K_2;
        case SDL_SCANCODE_3: return K_3;
        case SDL_SCANCODE_4: return K_4;
        case SDL_SCANCODE_5: return K_5;
        case SDL_SCANCODE_6: return K_6;
        case SDL_SCANCODE_7: return K_7;
        case SDL_SCANCODE_8: return K_8;
        case SDL_SCANCODE_9: return K_9;
        case SDL_SCANCODE_0: return K_0;
        case SDL_SCANCODE_KP_1: return K_PAD_1;
        case SDL_SCANCODE_KP_2: return K_PAD_2;
        case SDL_SCANCODE_KP_3: return K_PAD_3;
        case SDL_SCANCODE_KP_4: return K_PAD_4;
        case SDL_SCANCODE_KP_5: return K_PAD_5;
        case SDL_SCANCODE_KP_6: return K_PAD_6;
        case SDL_SCANCODE_KP_7: return K_PAD_7;
        case SDL_SCANCODE_KP_8: return K_PAD_8;
        case SDL_SCANCODE_KP_9: return K_PAD_9;
        case SDL_SCANCODE_KP_0: return K_PAD_0;
        case SDL_SCANCODE_KP_PLUS: return K_PLUS;
        case SDL_SCANCODE_KP_MINUS: return K_MINUS;
        case SDL_SCANCODE_F1: return K_F1;
        case SDL_SCANCODE_F2: return K_F2;
        case SDL_SCANCODE_F3: return K_F3;
        case SDL_SCANCODE_F4: return K_F4;
        case SDL_SCANCODE_F5: return K_F5;
        case SDL_SCANCODE_F6: return K_F6;
        case SDL_SCANCODE_F7: return K_F7;
        case SDL_SCANCODE_F8: return K_F8;
        case SDL_SCANCODE_F9: return K_F9;
        case SDL_SCANCODE_F10: return K_F10;
        case SDL_SCANCODE_F11: return K_F11;
        case SDL_SCANCODE_F12: return K_F12;
        default: return 0;
    }
}

static uint16 SDLModToModifiers(SDL_Keymod m)
{
    uint16 mods = 0;
    if(m & KMOD_LSHIFT) mods |= MOD_L_SHIFT;
    if(m & KMOD_RSHIFT) mods |= MOD_R_SHIFT;
    if(m & KMOD_CTRL) mods |= MOD_CTRL;
    if(m & KMOD_ALT) mods |= MOD_ALT;
    if(m & KMOD_CAPS) mods |= MOD_CAPS;
    if(m & KMOD_NUM) mods |= MOD_NUM_LOCK;
    if(m & KMOD_SCROLL) mods |= MOD_SCROLL_LOCK;
    return mods;
}

EventMgr::EventMgr(uint nsize, uint esize)
    : feedEvents(true), pQEvents(nullptr), iEHead(0), iETail(0), eqSize(esize),
      pQNotices(nullptr), iNHead(0), iNTail(0), nqSize(nsize), inInterrupt(false),
      real_ptr_bios_key_status(&g_bios_key_status), autoUpdateTicks(true)
{
    pQEvents = new Message[eqSize];
    pQNotices = new Message[nqSize];
    for(uint i=0;i<eqSize;i++) InitEvent(&pQEvents[i]);
    for(uint i=0;i<nqSize;i++) InitNotice(&pQNotices[i]);
    memset(scanKeys,0,sizeof(scanKeys));
    if(!pEventMgr) pEventMgr = this;
    SDL_AddTimer(1000 / TICKS_PER_SEC, TimerCallback, nullptr);
}

EventMgr::~EventMgr()
{
    delete [] pQEvents;
    delete [] pQNotices;
    if(pEventMgr==this) pEventMgr = nullptr;
}

void EventMgr::HandleSDLEvent(const SDL_Event& ev)
{
    switch(ev.type)
    {
        case SDL_KEYDOWN:
        {
            uint8 sc = SDLScancodeToKey(ev.key.keysym.scancode);
            if(sc)
            {
                scanKeys[sc] = 1;
                g_bios_key_status = SDLModToModifiers(SDL_GetModState());
                PostEventXY(E_KEY_DOWN, sc, gMouseX, gMouseY);
            }
            break;
        }
        case SDL_KEYUP:
        {
            uint8 sc = SDLScancodeToKey(ev.key.keysym.scancode);
            if(sc)
            {
                scanKeys[sc] = 0;
                g_bios_key_status = SDLModToModifiers(SDL_GetModState());
                PostEventXY(E_KEY_UP, sc, gMouseX, gMouseY);
            }
            break;
        }
        case SDL_MOUSEMOTION:
            gMouseX = ev.motion.x;
            gMouseY = ev.motion.y;
            break;
        case SDL_MOUSEBUTTONDOWN:
            gMouseX = ev.button.x;
            gMouseY = ev.button.y;
            PostEventXY(E_MOUSE_DOWN, ev.button.button, gMouseX, gMouseY);
            break;
        case SDL_MOUSEBUTTONUP:
            gMouseX = ev.button.x;
            gMouseY = ev.button.y;
            PostEventXY(E_MOUSE_UP, ev.button.button, gMouseX, gMouseY);
            break;
        case SDL_USEREVENT:
            clock.Cycle();
            break;
        default:
            break;
    }
}

void EventMgr::PublishNext()
{
    if(autoUpdateTicks)
        UpdateTicks();

    SDL_Event ev;
    while(SDL_PollEvent(&ev))
        HandleSDLEvent(ev);

    AQueueUpdate();

    if(iETail != iEHead)
    {
        do
        {
            Message msg = pQEvents[iEHead];
            InitEvent(&pQEvents[iEHead]);
            AdvanceEQueue();
            if(msg.event.type != E_NULL && msg.type != MSG_ABORTED)
            {
                if(msg.event.type == E_KEY_DOWN && msg.event.value == K_DEL)
                {
                    if((msg.event.modifiers & MOD_CTRL) &&
                       (msg.event.modifiers & MOD_ALT))
                    {
                        if(pContextMgr) pContextMgr->Quit();
                        else exit(0);
                    }
                }
                if(pContextMgr && pContextMgr->InMask(&msg))
                    pContextMgr->HandleMsg(&msg);
            }
        } while(feedEvents && iEHead != iETail);
    }

    if(iNTail != iNHead)
    {
        do
        {
            Message msg = pQNotices[iNHead];
            InitNotice(&pQNotices[iNHead]);
            AdvanceNQueue();
            if(msg.type != MSG_NULL && msg.type != MSG_ABORTED)
            {
                if(msg.notice.type != N_NULL && msg.notice.gDest)
                {
                    Periodic* pPer = ADerefAs(Periodic, msg.notice.gDest);
                    pPer->HandleMsg(&msg);
                }
            }
        } while(iNHead != iNTail);
    }
}

void EventMgr::WaitForEvent(Message* pMsg)
{
    Message msg;
    msg.type = MSG_NULL;
    while(msg.type == MSG_NULL)
    {
        if(iEHead != iETail)
        {
            msg = pQEvents[iEHead];
            InitEvent(&pQEvents[iEHead]);
            AdvanceEQueue();
            if(msg.event.type == E_NULL || msg.type == MSG_ABORTED)
                msg.type = MSG_NULL;
        }
        else
        {
            SDL_Event ev;
            if(SDL_WaitEvent(&ev))
                HandleSDLEvent(ev);
        }
    }
    if(pMsg)
        *pMsg = msg;
}

void EventMgr::Where(coord* x, coord* y)
{
    if(x) *x = gMouseX;
    if(y) *y = gMouseY;
}

uint16 EventMgr::GetModifiers()
{
    g_bios_key_status = SDLModToModifiers(SDL_GetModState());
    return g_bios_key_status;
}

char EventMgr::ScanToASCII(Event e)
{
    static char asciiTable[]      = "_ 1234567890-=__qwertyuiop[]__asdfghjkl;'`_\\zxcvbnm,./ ";
    static char asciiShiftTable[] = "_ !@#$%^&*()_+__QWERTYUIOP{}__ASDFGHJKL:\"~_|ZXCVBNM<>? ";
    if(e.modifiers & MOD_SHIFT)
        return asciiShiftTable[e.value];
    return asciiTable[e.value];
}

bool EventMgr::PostEvent(evt_t type, int32 value)
{
    return PostEventXY(type, value, gMouseX, gMouseY) != nullptr;
}

Message* EventMgr::PostEventXY(evt_t type, int32 value, coord x, coord y)
{
    Message* pMsg = ETail();
    if(!pMsg) return nullptr;
    InitEvent(pMsg, type, value);
    pMsg->event.x = x;
    pMsg->event.y = y;
    return pMsg;
}

bool EventMgr::PostNotice(notice_t type, grip gDest, void* param, grip gSource)
{
    Message* pMsg = NTail();
    if(!pMsg) return false;
    InitNotice(pMsg, type);
    pMsg->notice.gDest = gDest;
    pMsg->notice.gSource = gSource;
    pMsg->notice.param = param;
    return true;
}

bool EventMgr::SendNotice(notice_t type, grip gDest, grip gSource, void* param)
{
    Message msg;
    InitNotice(&msg, type);
    msg.notice.gDest = gDest;
    msg.notice.gSource = gSource;
    msg.notice.param = param;
    Periodic* pPer = ADerefAs(Periodic, gDest);
    return pPer->HandleMsg(&msg);
}

uint EventMgr::FlushEvents(evt_t mask)
{
    uint ret = 0;
    for(uint i=0;i<eqSize;i++)
    {
        if(pQEvents[i].event.type & mask)
        {
            ret++;
            pQEvents[i].type = MSG_ABORTED;
            pQEvents[i].event.value = 0;
        }
    }
    return ret;
}

uint EventMgr::FlushNotices(grip gDest)
{
    uint ret = 0;
    for(uint i=0;i<nqSize;i++)
    {
        if(pQNotices[i].notice.gDest == gDest)
        {
            ret++;
            pQNotices[i].type = MSG_ABORTED;
            pQNotices[i].event.value = 0;
        }
    }
    return ret;
}

bool EventMgr::Save(uint16, FILE*)
{
    return true;
}

bool EventMgr::KeyIsDown(uchar scanCode)
{
    return scanKeys[scanCode] != 0;
}

void EventMgr::AutoUpdateTicks(bool updateIt)
{
    autoUpdateTicks = updateIt;
}

void EventMgr::AdvanceEQueue()
{
    if(++iEHead >= eqSize) iEHead = 0;
}

void EventMgr::AdvanceNQueue()
{
    if(++iNHead >= nqSize) iNHead = 0;
}

Message* EventMgr::ETail()
{
    uint i = iETail;
    if(++iETail >= eqSize) iETail = 0;
    if(iETail == iEHead)
    {
        iETail = i;
        return nullptr;
    }
    return &pQEvents[i];
}

Message* EventMgr::NTail()
{
    uint i = iNTail;
    if(++iNTail >= nqSize) iNTail = 0;
    if(iNTail == iNHead)
    {
        iNTail = i;
        return nullptr;
    }
    return &pQNotices[i];
}

void EventMgr::InitEvent(Message* pMsg, evt_t type, int32 value)
{
    memset(pMsg,0,sizeof(Message));
    pMsg->type = MSG_EVENT;
    pMsg->event.type = type;
    pMsg->event.value = value;
    pMsg->event.modifiers = GetModifiers();
    pMsg->event.ticks = ATicks();
}

void EventMgr::InitNotice(Message* pMsg, notice_t type)
{
    memset(pMsg,0,sizeof(Message));
    pMsg->type = MSG_NOTICE;
    pMsg->notice.type = type;
}

void EventMgr::EnableInterrupts() {}
