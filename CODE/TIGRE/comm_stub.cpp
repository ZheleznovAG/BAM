#include "comm_stub.hpp"

// Minimal stub implementations for the old DOS communication layer.
// These allow the game to build on modern platforms without providing
// the original networking or serial functionality.

char pErrorStrings[][30] = {""};
char pBlockIDStrings[][30] = {""};
TCommMgr *pCommMgr = nullptr;

// ---------------- TComm ----------------
TComm::TComm() : packetAvail(FALSE), wConsoleNode(0), _error(ALL_OK), timeout(tcommDefaultTimeout) {}
TComm::~TComm() {}
TComm::ERROR TComm::GetError() { return _error; }
TComm::ERROR TComm::SetError(ERROR err) { _error = err; return _error; }
void TComm::ClearError() { _error = ALL_OK; }
uint32 TComm::Checksum(void*, WORD) { return 0; }
uint16 TComm::Checksum16(void*, WORD) { return 0; }

// ---------------- TNetwork ----------------
TNetwork::TNetwork() {}
TNetwork::~TNetwork() {}
TComm::ERROR TNetwork::Init(long) { return ALL_OK; }
TComm::ERROR TNetwork::Connect() { return ALL_OK; }
TComm::ERROR TNetwork::Disconnect() { return ALL_OK; }
TComm::ERROR TNetwork::SendPacket(sPacket*, bool) { return ALL_OK; }
TComm::ERROR TNetwork::ReceivePacket(sPacket*) { return ALL_OK; }
BOOL TNetwork::IsPacketAvailable() { return FALSE; }
TComm::ERROR TNetwork::DiscardPacket(sPacketHeader*) { return ALL_OK; }
WORD TNetwork::GetUserList(WORD*) { return 0; }
void TNetwork::AtExitFn() {}
int TNetwork::init = 0;
int TNetwork::isKilled = 0;
W32 TNetwork::wNETNodes = 0;
W32 TNetwork::wNETSocket = 0;

// ---------------- TSerial ----------------
TSerial::TSerial() {}
TSerial::~TSerial() {}
TComm::ERROR TSerial::Init(long) { return ALL_OK; }
TComm::ERROR TSerial::Connect() { return ALL_OK; }
TComm::ERROR TSerial::Disconnect() { return ALL_OK; }
TComm::ERROR TSerial::SetPort(int) { return ALL_OK; }
void TSerial::SetBaud(int) {}
TComm::ERROR TSerial::SendPacket(sPacket*, bool) { return ALL_OK; }
TComm::ERROR TSerial::ReceivePacket(sPacket*) { return ALL_OK; }
BOOL TSerial::IsPacketAvailable() { return FALSE; }
TComm::ERROR TSerial::DiscardPacket(sPacketHeader*) { return ALL_OK; }
WORD TSerial::GetUserList(WORD*) { return 0; }
void TSerial::MonoHeader(sPacketHeaderTiny*) {}
void TSerial::AtExitFn() {}
void TSerial::_ClearVars() {}
void TSerial::_Destruct() {}
int TSerial::_CheckValid(sPacketHeaderTiny*) { return 0; }
bool TSerial::_WaitForTXBufferSpace() { return false; }
bool TSerial::_CheckLineErrors() { return false; }

// ---------------- TModem ----------------
TModem::TModem() {}
TModem::~TModem() {}
TComm::ERROR TModem::Init(long) { return ALL_OK; }
TComm::ERROR TModem::Disconnect() { return ALL_OK; }
TComm::ERROR TModem::WaitForCall() { return ALL_OK; }
TComm::ERROR TModem::Dial(char*) { return ALL_OK; }
void TModem::HangUp() {}
TComm::ERROR TModem::Write(char*) { return ALL_OK; }
long TModem::_Answer() { return 0; }

// ---------------- TCommMgr ----------------
TCommMgr::TCommMgr() : pComm(nullptr), fSilence(false), totalPacketsWaiting(0), pBuffer(nullptr), bufferLen(0), dataAvail(0), head(0), tail(0) {}
TCommMgr::~TCommMgr() {}
int TCommMgr::Init(TComm* comm, long) { pComm = comm; return 0; }
int TCommMgr::Connect() { return 0; }
int TCommMgr::Disconnect() { return 0; }
int TCommMgr::SendData(int, int, int, void*) { return 0; }
int TCommMgr::SendData(sPacket*, bool) { return 0; }
int TCommMgr::ReceiveData(int*, int*, int*, void*) { return 0; }
int TCommMgr::ReceiveData(sPacket*) { return 0; }
int TCommMgr::DataAvailable(int*, int*, int*) { return 0; }
int TCommMgr::DataAvailable(sPacket*) { return 0; }
int TCommMgr::DiscardData() { return 0; }
int TCommMgr::DumpQueue() { return 0; }
int TCommMgr::GetError() { return 0; }
int TCommMgr::GetUserID() { return 0; }
int TCommMgr::GetUserList(unsigned*) { return 0; }
bool TCommMgr::Save(uint16, FILE*) { return true; }
void TCommMgr::Silence(bool fNewMode) { fSilence = fNewMode; }
pIntFnInt TCommMgr::SetUserAbortFn(pIntFnInt pFn) { return pFn; }
int TCommMgr::EnQueueData(bool) { return 0; }
int TCommMgr::_SendData(sPacket*, bool) { return 0; }
int TCommMgr::_ReceiveData(sPacket*) { return 0; }
int TCommMgr::ReceiveLargePacket() { return 0; }
TComm::ERROR TCommMgr::SendAckNak(sPacket*, bool) { return TComm::ALL_OK; }
sPacket* TCommMgr::DeQueueData() { return nullptr; }
bool TCommMgr::AddToWaitingRoom(sPacket*) { return false; }
bool TCommMgr::RemoveFromWaitingRoom(sPacket*) { return false; }
TComm::ERROR TCommMgr::ResendWaiters() { return TComm::ALL_OK; }
void TCommMgr::RemoveEmpties() {}
void TCommMgr::RemoveOldReplies() {}
