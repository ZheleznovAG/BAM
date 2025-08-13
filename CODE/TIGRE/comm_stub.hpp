#pragma once

// Lightweight declarations for the old DOS communication layer.  These
// avoid pulling in the original HMI NetNow! and Greenleaf headers which are
// unavailable on modern platforms.  The real DOS headers are only included
// when building with OS_DOS; everyone else uses these minimal stubs.

#include <cstdint>
#include <cstdio>

// Basic type aliases used throughout the original interfaces
using uchar  = uint8_t;
using WORD   = uint16_t;
using W32    = uint32_t;
using uint16 = uint16_t;
using uint32 = uint32_t;
using int32  = int32_t;
using BOOL   = int;

// Forward declarations of engine base types
class Manager;
class Object;

// ---------------------------------------------------------------------------
// Packet structures (trimmed down versions of the originals)
// ---------------------------------------------------------------------------

struct sPacketHeader
{
    WORD  wSequence;
    WORD  wType;
    WORD  ID;
    WORD  len;
    WORD  destID;
    WORD  sendID;
    int32 magicNumber;
    int32 headerChecksum;
    int32 dataChecksum;
};

struct sPacketHeaderTiny
{
    uchar  wSequence;
    uchar  wType;
    uchar  ID;
    uchar  len;
    int32  magicNumber;
    uint16 headerChecksum;
    uint16 dataChecksum;
};

struct sPacket
{
    sPacketHeader header;
    WORD          gl_padding;   // space for legacy libraries
    void*         pData;
};

// ---------------------------------------------------------------------------
// TComm and friends
// ---------------------------------------------------------------------------

const int tcommMaxPlayers        = 2;
const int tcommDefaultTimeout    = 6 * 1000;      // ~6 seconds
const int tcommDefaultMaxSendSize = 10 * 1024;
const int tcommBadUserID         = -1;

class TComm : public Manager
{
public:
    enum ERROR
    {
        ALL_OK = 0,
        NULL_CLASS,
        INIT_FAILED,
        CONNECTION_FAILED,
        PACKET_FAILED,
        PACKET_NOT_AVAILABLE,
        UNKNOWN_PACKET,
        UNEXPECTED_PACKET,
        SEND_FAILED,
        BAD_CHECKSUM,
        TIMEOUT,
        NOT_A_MODEM,
        TIMEOUT_BUFFER_FULL,
        TIMEOUT_NO_ACK,
        PREMATURE_ACK,
        UNKNOWN_ERROR,
        ERROR_DATA_NAK,
        INPUT_QUEUE_FULL,
        BAD_PACKET_TYPE,
        WRITE_FAILED,
        TOTAL_ERROR_TYPES
    };

    TComm();
    virtual ~TComm();

    // Data Access
    ERROR GetError();
    ERROR SetError(ERROR err);
    void  ClearError();
    int   GetTimeout() const { return timeout; }
    void  SetTimeout(int t)  { timeout = t; }

    uint32 Checksum(void* pData, WORD len);
    uint16 Checksum16(void* pData, WORD len);

    // Information
    WORD        GetUserID() const { return wConsoleNode; }
    virtual WORD GetUserList(WORD* pList = nullptr) = 0;

protected:
    BOOL     packetAvail;
    sPacket  lastPacket;
    WORD     wConsoleNode;

private:
    ERROR _error;
    int   timeout;
};

class TNetwork : public TComm
{
public:
    TNetwork();
    virtual ~TNetwork();

    virtual ERROR Init(long optionalArg = 0);
    virtual ERROR Connect();
    virtual ERROR Disconnect();

    virtual ERROR SendPacket(sPacket* pPacket, bool fIsResend = false);
    virtual ERROR ReceivePacket(sPacket* pPacket);
    virtual BOOL  IsPacketAvailable();
    virtual ERROR DiscardPacket(sPacketHeader* pPacketHeader = nullptr);

    virtual WORD GetUserList(WORD* pList = nullptr);

    static void AtExitFn();
    static int  init, isKilled;
    static W32  wNETNodes;
    static W32  wNETSocket;
};

class TSerial : public TComm
{
public:
    TSerial();
    virtual ~TSerial();

    virtual ERROR Init(long optionalArg);
    virtual ERROR Connect();
    virtual ERROR Disconnect();
    virtual ERROR SetPort(int newPort);
    void         SetBaud(int newBaud);
    int          GetBaud() const { return _baud; }

    virtual ERROR SendPacket(sPacket* pPacket, bool fIsResend = false);
    virtual ERROR ReceivePacket(sPacket* pPacket);
    virtual BOOL  IsPacketAvailable();
    virtual ERROR DiscardPacket(sPacketHeader* pPacketHeader = nullptr);

    virtual WORD GetUserList(WORD* pList = nullptr);
    void         MonoHeader(sPacketHeaderTiny* pHeader);

protected:
    static void AtExitFn();
    void        _ClearVars();
    virtual void _Destruct();
    int         _CheckValid(sPacketHeaderTiny* pHeader);

    bool _WaitForTXBufferSpace();
    bool _CheckLineErrors();

    int _baud{0};
};

class TModem : public TSerial
{
public:
    TModem();
    virtual ~TModem();

    virtual ERROR Init(long optionalArg);
    virtual ERROR Disconnect();

    ERROR WaitForCall();
    ERROR Dial(char* szPhoneNumber);
    void  HangUp();
    ERROR Write(char* szWriteStr);

protected:
    long _Answer();
};

// ---------------------------------------------------------------------------
// TCommMgr
// ---------------------------------------------------------------------------

class TCommMgr : public Manager, public Object
{
public:
    TCommMgr();
    ~TCommMgr();

    char* GetBuffer() { return pBuffer; }
    int   GetBufferLen() { return bufferLen; }

    int Init(TComm* pComm, long optionalArg = 0);
    int Connect();
    int Disconnect();
    int SendData(int to, int type, int len, void* pData);
    int SendData(sPacket* pPacket, bool fWaitForAck = true);
    int ReceiveData(int* pFrom, int* pType, int* pLen, void* pData = nullptr);
    int ReceiveData(sPacket* pPacket);
    int DataAvailable(int* pFrom, int* pType, int* pLen);
    int DataAvailable(sPacket* pPacket = nullptr);
    int DiscardData();
    int DumpQueue();
    int GetError();
    int GetUserID();
    int GetUserList(unsigned* pList = nullptr);

    bool Save(uint16 state, FILE* fp = nullptr);
    void Silence(bool fNewMode);

    using pIntFnInt = int (*)(int);
    static pIntFnInt SetUserAbortFn(pIntFnInt pFn);

    TComm* pComm;          // communication object in use
    bool   fSilence;
    int    totalPacketsWaiting;
    int    EnQueueData(bool fDebug = false);

private:
    int  _SendData(sPacket* pPacket, bool fWaitForAck = true);
    int  _ReceiveData(sPacket* pPacket);
    int  ReceiveLargePacket();
    TComm::ERROR SendAckNak(sPacket* pPacket, bool fOkay);
    sPacket*     DeQueueData();

    bool AddToWaitingRoom(sPacket* pPacket);
    bool RemoveFromWaitingRoom(sPacket* pPacket);
    TComm::ERROR ResendWaiters();
    void RemoveEmpties();
    void RemoveOldReplies();

    char* pBuffer;
    int   bufferLen;
    int   dataAvail;
    int   head;
    int   tail;
};

extern char pErrorStrings[][30];
extern char pBlockIDStrings[][30];
extern TCommMgr* pCommMgr;

#endif // TIGRE_COMM_STUB_HPP

