#include "comm.hpp"
#include "mono.hpp"

#include <enet/enet.h>

int TNetwork::isKilled = 0;
int TNetwork::init = 0;
W32 TNetwork::wNETSocket = 0;
W32 TNetwork::wNETNodes = 0;

static ENetHost* gHost = nullptr;

TNetwork::TNetwork()
{
    init = 0;
    isKilled = 0;
}

TNetwork::~TNetwork()
{
    AtExitFn();
}

void TNetwork::AtExitFn()
{
    if (init && !isKilled)
    {
        enet_deinitialize();
        isKilled = 1;
    }
}

TComm::ERROR TNetwork::Init(long)
{
    ClearError();
    if (!init)
    {
        if (enet_initialize() != 0)
        {
            SetError(INIT_FAILED);
        }
        else
        {
            init = 1;
            atexit(AtExitFn);
        }
    }
    return GetError();
}

TComm::ERROR TNetwork::Connect()
{
    if (!init)
    {
        return SetError(INIT_FAILED);
    }
    ENetAddress address;
    address.host = ENET_HOST_ANY;
    address.port = 1234;
    gHost = enet_host_create(&address, 32, 2, 0, 0);
    if (!gHost)
    {
        return SetError(CONNECTION_FAILED);
    }
    return GetError();
}

TComm::ERROR TNetwork::Disconnect()
{
    if (gHost)
    {
        enet_host_destroy(gHost);
        gHost = nullptr;
    }
    return GetError();
}

TComm::ERROR TNetwork::SendPacket(sPacket*, bool)
{
    // Networking not fully implemented yet
    return GetError();
}

TComm::ERROR TNetwork::ReceivePacket(sPacket*)
{
    return SetError(PACKET_NOT_AVAILABLE);
}

BOOL TNetwork::IsPacketAvailable()
{
    return FALSE;
}

TComm::ERROR TNetwork::DiscardPacket(sPacketHeader*)
{
    return GetError();
}

WORD TNetwork::GetUserList(WORD*)
{
    return 0;
}
