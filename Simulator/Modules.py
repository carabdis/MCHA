import numpy as np
import heapq
import copy
import json
import os
import datetime

CounterReturn = 0
CounterAsk = 0

class Func:
    def __init__(self, DestList, CycleList):
        self.DestList = DestList
        self.CycleList = CycleList
    
    def SelDest(self, Type, ID):
        OutputGroup = self.DestList[Type]
        DestType, DestDetail = OutputGroup
        Possibility = np.random.rand()
        # Possibility = 0.2
        if DestType == 0: # Fixed Destination
            ### DestDetail: list [ tuple (Chip Address, Block Address, Core Address)]
            return copy.deepcopy(DestDetail), Possibility
        elif DestType == 1: # Random Destination
            ### DestDetail: tuple (list [ list [Accumulated Possibility Distribution] ],
            ###                    list [ tuple (Chip Address, Block Address, Core Address) ])
            Distribution, Destination = DestDetail
            for i in range(len(Distribution)):
                if Possibility < Distribution[i]:
                    return copy.deepcopy(Destination[i]), Possibility
        else: # Dest Based on ID
            return copy.deepcopy(DestDetail[ID % len(DestDetail)]), Possibility
    
    def CalcCycle(self, Type, ID, SharePoss):
        OutputGroup = self.CycleList[Type]
        CycleType, CycleDetail = OutputGroup
        if CycleType == 0: # Fixed Cycles
            ### CycleDetail: tuple (list  [Cycle Numbers];
            ###                     list [Sto=0 / Send=1 / Delete=2];
            ###                     list [Update bool];
            ###                     list [Send / Sto Message Length];
            ###                     list [Send / Sto Message Type]))
            return copy.deepcopy(CycleDetail)
        elif CycleType == 1: # Random Cycles
            ### CycleDetail: tuple (list [ list [Accumulated Possibility Distribution] ];
            ###                     list [ list [Sto / Send] ];
            ###                     list [ list [Update bool]]
            ###                     list [ list [Send / Sto Possible Cycle Numbers] ];
            ###                     list [ list [Send / Sto Possible Message Length] ];
            ###                     list [ list [Send / Sto Possible Message Type] ]))
            Distribution, PossCycle, PossSto, PossUpdate, PossLength, PossType = CycleDetail
            if SharePoss is None:
                Possibility = np.random.rand()
                # Possibility = 0.2
            else:
                Possibility = SharePoss
            for i in range(len(Distribution)):
                if Possibility < Distribution[i]:
                    return (copy.deepcopy(PossCycle[i]), copy.deepcopy(PossSto[i]), copy.deepcopy(PossUpdate[i]),
                            copy.deepcopy(PossLength[i]), copy.deepcopy(PossType[i]))
        elif CycleType == 2:
            return copy.deepcopy(CycleDetail[ID % len(CycleDetail)])
        else:
            Distribution, PossCycle, PossSto, PossUpdate, PossLength, PossType = CycleDetail[ID % len(CycleDetail)]
            if SharePoss is None:
                Possibility = np.random.rand()
                # Possibility = 0.2
            else:
                Possibility = SharePoss
            for i in range(len(Distribution)):
                if Possibility < Distribution[i]:
                    return (copy.deepcopy(PossCycle[i]), copy.deepcopy(PossSto[i]), copy.deepcopy(PossUpdate[i]),
                            copy.deepcopy(PossLength[i]), copy.deepcopy(PossType[i]))
    
    def Process(self, Type, ID):
        SendDestinations, SharePoss = self.SelDest(Type, ID)
        CostCycles, StoJudge, UpdateList, MessageLength, MessageType = self.CalcCycle(Type, ID, SharePoss)
        return CostCycles, (StoJudge, UpdateList, SendDestinations, MessageLength, MessageType)


class Core:
    def __init__(self, InitFunc:list, ProcFunc:list, MemFunc:list, MemorySize:int, CoreAddress:int, MemLimit:dict,
                 UpdateLimit:dict, InitMemID:list=[], InitMemNum:list=[], StateNum=1, TravelState=[None], NextState=[]):
        self.Address = CoreAddress
        self.InitFunc = InitFunc
        self.MemFunc = MemFunc
        self.ProcFunc = ProcFunc
        self.MemoryID = copy.deepcopy(InitMemID)              # [ tuple: (Type, ID)]
        self.MemoryNum = copy.deepcopy(InitMemNum)
        self.ShakeList = {}
        self.MemorySize = MemorySize
        self.MemoryCounter = sum(InitMemNum)
        self.MemTypeCounter = [{key:0 for key in MemLimit[i]} for i in range(StateNum)]
        for i in range(len(InitMemID)):
            temptype = InitMemID[i][0]
            if self.MemTypeCounter[0].get(temptype) is None:
                self.MemTypeCounter[0][temptype] = InitMemNum[0]
            else:
                self.MemTypeCounter[0][temptype] += InitMemNum[0]
        self.MemLimit = MemLimit
        self.UpdateLimit = UpdateLimit
        self.StateNum = StateNum
        self.UpdateNum = [{key:0 for key in UpdateLimit[i]} for i in range(StateNum)]
        self.MemTravel = 0
        self.State = 0
        self.TravelState = TravelState
        self.DoTravel = self.State in self.TravelState
        self.MemActType = []
        self.WaitProc = []
        if NextState == []:
            NextState = [i + 1 for i in range(StateNum)]
            NextState[-1] = 0
        self.NextState = NextState
        for j in self.MemLimit[self.State]:
            if self.MemTypeCounter[self.State][j] >= self.MemLimit[self.State][j]:
                self.MemActType.append((j, 0))
        self.DebugAddress = None
    
    def DoOrNot(self, Type):
        if self.UpdateLimit[self.State].get(Type) is not None:
            DoFunc = self.UpdateNum[self.State][Type] < self.UpdateLimit[self.State][Type]
        else:
            DoFunc = True
        return DoFunc and self.InitFunc[self.State].DestList.get(Type) is not None

    def Process(self, Input):
        """
        :param Input: Type, ID, MessageLength
        """
        global CounterAsk
        if len(self.MemActType) != 0:
            if Input != None:
                Details, InID = Input
                InType, _, _ = Details
                self.WaitProc.append((0, InType, InID))
            Type, ID = self.MemActType[0]
            CycleCost, FuncInfo = self.MemFunc[self.State].Process(Type, ID)
            self.MemActType.pop(0)
        elif Input != None:
            Details, ID = Input
            Type, Dest, _ = Details
            CycleCost, FuncInfo = self.ProcFunc[self.State].Process(Type, ID)
            self.DebugAddress = Dest
        elif len(self.WaitProc) != 0:
            if len(self.WaitProc[0]) == 3:
                ProcGenCost, Type, ID = self.WaitProc[0]
                CycleCost, FuncInfo = self.ProcFunc[self.State].Process(Type, ID)
                CycleCost[0] += ProcGenCost
            else:
                GroupInfo, FuncInfo = self.WaitProc[0]
                CycleCost, ID = GroupInfo
            self.WaitProc.pop(0)
        elif self.InitFunc[self.State] != None and Input == None and self.DoTravel:
            if self.MemTravel < len(self.MemoryID):
                Type, ID = self.MemoryID[self.MemTravel]
                while not self.DoOrNot(Type):
                    self.MemTravel += 1
                    Type, ID = self.MemoryID[self.MemTravel]
                CycleCost, FuncInfo = self.InitFunc[self.State].Process(Type, ID)
                self.MemTravel += 1
            else:
                return None, None, None
        else:
            return None, None, None
        StoJudge, Update, SendDestinations, MessageLegth, MessageType = FuncInfo
        SendList = []
        RemoveIndex = []
        DeleteList = [[], []]
        for i in range(len(StoJudge)):
            if Update[i]:
                if self.UpdateNum[self.State].get(Type) is None:
                    self.UpdateNum[self.State][Type] = 1
                else:
                    self.UpdateNum[self.State][Type] += 1
            if StoJudge[i] == 0:
                SendList.append(i)
            elif StoJudge[i] == 1:
                if MessageLegth[i] > 0:
                    self.MemoryID.append((MessageType[i], ID))
                    self.MemoryNum.append(MessageLegth[i])
                self.MemoryCounter += MessageLegth[i]
                if self.MemTypeCounter[self.State].get(MessageType[i]) is None:
                    self.MemTypeCounter[self.State][MessageType[i]] = MessageLegth[i]
                else:
                    self.MemTypeCounter[self.State][MessageType[i]] += MessageLegth[i]
                if self.MemoryCounter > self.MemorySize:
                    raise Exception("Memory Overflow in Core " + str(self.Address))
                if self.MemLimit[self.State].get(MessageType[i]) is not None and self.MemTypeCounter[self.State][MessageType[i]] >= self.MemLimit[self.State][MessageType[i]]:
                    self.MemActType.append((MessageType[i], ID))
                    if self.ShakeList.get(MessageType[i]) is not None:
                        UsingNum = min(self.MemTypeCounter[self.State][MessageType[i]], self.ShakeList[MessageType[i]])
                        self.MemTypeCounter[self.State][MessageType[i]] -= UsingNum
                        self.ShakeList[MessageType[i]] -= UsingNum
                    MessageType[i] = None
            elif StoJudge[i] == 2:
                if self.MemTypeCounter[self.State].get(MessageType[i]) is not None and self.MemTypeCounter[self.State][MessageType[i]] > 0:
                    RealLength = min(self.MemTypeCounter[self.State][MessageType[i]], MessageLegth[i])
                    DeleteList[0].append(MessageType[i])
                    DeleteList[1].append(RealLength)
                    self.MemoryCounter -= RealLength
                    self.MemTypeCounter[self.State][MessageType[i]] -= RealLength
                SendDestinations[i] = None
            elif StoJudge[i] == 4:
                if type(CycleCost[i]) is str:
                    self.WaitProc.append((([float(CycleCost[i])], ID), ([0], [Update[i]], [SendDestinations[i]], [MessageLegth[i]], [MessageType[i]])))
                else:
                    self.WaitProc.append((CycleCost[i], MessageType[i], ID))
                RemoveIndex.append(i)
            elif StoJudge[i] == 5:
                if self.MemLimit[self.State].get(MessageType[i]) is None:
                    self.MemLimit[self.State][MessageType[i]] = MessageLegth[i]
                else:
                    self.MemLimit[self.State][MessageType[i]] += MessageLegth[i]
                if self.MemTypeCounter[self.State].get(MessageType[i]) is not None and self.MemTypeCounter[self.State][MessageType[i]] >= self.MemLimit[self.State][MessageType[i]]:
                    self.MemActType.append((MessageType[i], ID))
                    if self.ShakeList.get(MessageType[i]) is not None:
                        UsingNum = min(self.MemTypeCounter[self.State][MessageType[i]], self.ShakeList[MessageType[i]])
                        self.MemTypeCounter[self.State][MessageType[i]] -= UsingNum
                        self.ShakeList[MessageType[i]] -= UsingNum
                    MessageType[i] = None
                else:
                    RemoveIndex.append(i)
            elif StoJudge[i] == 6:
                if self.ShakeList.get(MessageType[i]) is None:
                    self.ShakeList[MessageType[i]] = 1
                else:
                    self.ShakeList[MessageType[i]] += 1
                if self.MemTypeCounter[self.State].get(MessageType[i]) is None:
                    self.MemTypeCounter[self.State][MessageType[i]] = 1
                else:
                    self.MemTypeCounter[self.State][MessageType[i]] += 1
                if self.MemLimit[self.State].get(MessageType[i]) is not None and self.MemTypeCounter[self.State][MessageType[i]] >= self.MemLimit[self.State][MessageType[i]]:
                    self.MemActType.append((MessageType[i], ID))
                    if self.ShakeList.get(MessageType[i]) is not None:
                        UsingNum = min(self.MemTypeCounter[self.State][MessageType[i]], self.ShakeList[MessageType[i]])
                        self.MemTypeCounter[self.State][MessageType[i]] -= UsingNum
                        self.ShakeList[MessageType[i]] -= UsingNum
                    MessageType[i] = None
            else:
                MessageType[i] = None
        RemoveIndex.reverse()
        for ind in RemoveIndex:
            CycleCost.pop(ind)
            StoJudge.pop(ind)
            Update.pop(ind)
            SendDestinations.pop(ind)
            MessageType.pop(ind)
            MessageLegth.pop(ind)
        
        if len(DeleteList[0]) != 0:
            self.MemoryID.reverse()
            self.MemoryNum.reverse()
            TravelChange = 0
            for i in range(len(self.MemoryID) - 1, -1, -1):
                temptype, tempid = self.MemoryID[i]
                templength = self.MemoryNum[i]
                if temptype in DeleteList[0]:
                    place = DeleteList[0].index(temptype)
                    if DeleteList[1][place] < templength:
                        self.MemoryNum[i] = templength - DeleteList[1][place]
                        DeleteList[1].pop(place)
                        DeleteList[0].pop(place)
                    elif DeleteList[1][place] == templength:
                        self.MemoryID.pop(i)
                        self.MemoryNum.pop(i)
                        DeleteList[1].pop(place)
                        DeleteList[0].pop(place)
                        if len(self.MemoryID) - i <= self.MemTravel:
                            TravelChange += 1
                    else:
                        self.MemoryID.pop(i)
                        self.MemoryNum.pop(i)
                        if len(self.MemoryID) - i <= self.MemTravel:
                            TravelChange += 1
                        DeleteList[1][place] -= templength
            self.MemTravel -= TravelChange
            self.MemoryID.reverse()
            self.MemoryNum.reverse()
        PhaseChange = True
        for i in self.UpdateNum[self.State]:
            if self.UpdateLimit[self.State].get(i) is None:
                continue
            if self.UpdateNum[self.State][i] < self.UpdateLimit[self.State][i]:
                PhaseChange = False
                break
        if PhaseChange:
            PastState = self.State
            self.State = self.NextState[self.State]
            self.UpdateNum[self.State] = {key:0 for key in self.UpdateNum[self.State]}
            self.DoTravel = self.State in self.TravelState
            self.MemTravel = 0
            self.MemTypeCounter[self.State].update(self.MemTypeCounter[PastState])
            for j in self.MemLimit[self.State]:
                if self.MemTypeCounter[self.State][j] >= self.MemLimit[self.State][j]:
                    self.MemActType.append((j, int(ID)))
                    # if self.DebugAddress == (1, 0, 0, 0, 2) and j == 2 and int(ID) == 256:
                    #     print(self.MemActType, self.State, "######")
                    if len(CycleCost) == 0:
                        CycleCost.append(1)
                    else:
                        CycleCost.append(0)
                    SendDestinations.append(None)
                    MessageLegth.append(1)
                    MessageType.append(None)
            if len(CycleCost) == 0:
                CycleCost.append(1)
            else:
                CycleCost.append(0)
            SendDestinations.append(None)
            MessageLegth.append(1)
            MessageType.append(None)
        for index in range(len(StoJudge)):
            if index not in SendList:
                SendDestinations[index] = None
        if len(CycleCost) == 0 and (len(self.WaitProc) != 0 or len(self.MemActType) != 0 or (self.DoTravel and self.MemTravel < len(self.MemoryID))):
            CycleCost.append(1)
            SendDestinations.append(None)
            MessageLegth.append(1)
            MessageType.append(None)
        elif len(self.WaitProc) != 0 or len(self.MemActType) != 0 or (self.DoTravel and self.MemTravel < len(self.MemoryID)):
            CycleCost.append(0)
            SendDestinations.append(None)
            MessageLegth.append(1)
            MessageType.append(None)
        return CycleCost, (SendDestinations, MessageLegth, MessageType), [ID for _ in range(len(CycleCost))]


class FIFO:
    def __init__(self, Size):
        self.Size = Size
        self.Content = []
        self.Counter = 0
    
    def Top(self):
        if self.Counter == 0:
            return None
        else:
            return self.Content[-1]
    
    def Pop(self):
        Details, ID = self.Content[-1]
        Type, Dest, Length = Details
        self.Counter -= Length
        self.Content.pop()
        return

    def Push(self, Input):
        Details, ID = Input
        Type, Dest, Length = Details
        self.Content.insert(0, Input)
        self.Counter += Length
        return
    
    def Full(self):
        return self.Counter >= self.Size


class Controller:
    def __init__(self, CoreNum, BufferSize):
        EdgeNum = 4
        self.CoreSendFF = [FIFO(BufferSize) for _ in range(CoreNum)]
        self.CoreRecvFF = [FIFO(BufferSize) for _ in range(CoreNum)]
        self.EdgeSendFF = [FIFO(BufferSize) for _ in range(EdgeNum)]
        self.EdgeRecvFF = [FIFO(BufferSize) for _ in range(EdgeNum)]
        self.DRAMSendFF = FIFO(BufferSize * CoreNum)
        self.DRAMRecvFF = FIFO(BufferSize * CoreNum)
        self.CoreNum = CoreNum
        self.EdgeNum = EdgeNum
        self.WaitCounter = np.zeros((CoreNum + EdgeNum + 1, CoreNum + EdgeNum + 1), dtype=int)
        self.AskFlag = np.zeros((CoreNum + EdgeNum + 1, CoreNum + EdgeNum + 1), dtype=int)
        self.IdleStartSendCycle = [0 for _ in range(CoreNum + EdgeNum + 1)]
        self.IdleStartRecvCycle = [0 for _ in range(CoreNum + EdgeNum + 1)]
    
    def CSTop(self):
        return [FF.Top() for FF in self.CoreSendFF]
    
    def CRTop(self):
        return [FF.Top() for FF in self.CoreRecvFF]
    
    def ESTop(self):
        return [FF.Top() for FF in self.EdgeSendFF]
    
    def ERTop(self):
        return [FF.Top() for FF in self.EdgeRecvFF]
    
    def CSFull(self):
        return [FF.Full() for FF in self.CoreSendFF]
    
    def CRFull(self):
        return [FF.Full() for FF in self.CoreRecvFF]
    
    def ESFull(self):
        return [FF.Full() for FF in self.EdgeSendFF]
    
    def ERFull(self):
        return [FF.Full() for FF in self.EdgeRecvFF]
    
    def CSPush(self, Index, Info):
        self.CoreSendFF[Index].Push(Info)
        return
    
    def CRPop(self, Index):
        self.CoreRecvFF[Index].Pop()
        return
    
    def Process(self, PresentAddress, PresentCycle):
        PChipX, PChipY, PBlockX, PBlockY = PresentAddress
        SendInfo = self.CSTop() + [self.DRAMSendFF.Top()] + self.ESTop()
        RecvFull = self.CRFull() + [self.DRAMRecvFF.Full()] + self.ERFull()
        IncrementCycle = []
        CoreEventCycle = [[] for _ in range(self.CoreNum)]
        Log = np.zeros(len(SendInfo))
        for i in range(len(SendInfo)):
            Message = SendInfo[i]
            if Message is None or self.IdleStartSendCycle[i] > PresentCycle:
                self.WaitCounter[:, i] = 0
                self.AskFlag[:, i] = 0
                continue
            Details, _ = Message
            _, Dest, _ = Details
            ChipX, ChipY, BlockX, BlockY, CoreAddress = Dest
            if type(CoreAddress) == str:
                self.WaitCounter[self.CoreNum, i] += 1
                self.AskFlag[self.CoreNum, i] = 1
            elif PChipX < ChipX:
                self.WaitCounter[self.CoreNum + 1, i] += 1
                self.AskFlag[self.CoreNum + 1, i] = 1
            elif PChipX > ChipX:
                self.WaitCounter[self.CoreNum + 3, i] += 1
                self.AskFlag[self.CoreNum + 3, i] = 1
            elif PChipY < ChipY:
                self.WaitCounter[self.CoreNum + 4, i] += 1
                self.AskFlag[self.CoreNum + 4, i] = 1
            elif PChipY > ChipY:
                self.WaitCounter[self.CoreNum + 2, i] += 1
                self.AskFlag[self.CoreNum + 2, i] = 1
            elif PBlockX < BlockX:
                self.WaitCounter[self.CoreNum + 1, i] += 1
                self.AskFlag[self.CoreNum + 1, i] = 1
            elif PBlockX > BlockX:
                self.WaitCounter[self.CoreNum + 3, i] += 1
                self.AskFlag[self.CoreNum + 3, i] = 1
            elif PBlockY < BlockY:
                self.WaitCounter[self.CoreNum + 4, i] += 1
                self.AskFlag[self.CoreNum + 4, i] = 1
            elif PBlockY > BlockY:
                self.WaitCounter[self.CoreNum + 2, i] += 1
                self.AskFlag[self.CoreNum + 2, i] = 1
            else:
                self.WaitCounter[CoreAddress, i] += 1
                self.AskFlag[CoreAddress, i] = 1
        SelectValue = self.WaitCounter.max(axis=1)
        JudgeOp = self.AskFlag.sum(axis=1)
        for i in range(len(RecvFull)):
            if JudgeOp[i] == 0:
                continue
            if self.IdleStartRecvCycle[i] > PresentCycle:
                continue
            if self.IdleStartRecvCycle[i] == PresentCycle:
                TargetIndex = np.where(self.WaitCounter[i, :] == SelectValue[i])[0][0]
                if i < self.CoreNum:
                    self.CoreRecvFF[i].Push(SendInfo[TargetIndex])
                    if PresentCycle + 1 not in CoreEventCycle[i]:
                        CoreEventCycle[i].append(PresentCycle + 1)
                elif i == self.CoreNum:
                    self.DRAMRecvFF.Push(SendInfo[TargetIndex])
                else:
                    self.EdgeRecvFF[i - self.CoreNum - 1].Push(SendInfo[TargetIndex])
                if TargetIndex < self.CoreNum:
                    self.CoreSendFF[TargetIndex].Pop()
                    if PresentCycle + 1 not in CoreEventCycle[TargetIndex]:
                        CoreEventCycle[TargetIndex].append(PresentCycle + 1)
                elif TargetIndex == self.CoreNum:
                    self.DRAMSendFF.Pop()
                else:
                    self.EdgeSendFF[TargetIndex - self.CoreNum - 1].Pop()
                if PresentCycle + 1 not in IncrementCycle:
                    IncrementCycle.append(PresentCycle + 1)
                self.WaitCounter[i, TargetIndex] = 0
                self.AskFlag[i, TargetIndex] = 0
                continue
            if RecvFull[i]:
                if PresentCycle + 1 not in IncrementCycle:
                    IncrementCycle.append(PresentCycle + 1)
                continue
            TargetIndex = np.where(self.WaitCounter[i, :] == SelectValue[i])[0][0]
            Details, _ = SendInfo[TargetIndex]
            _, _, Length = Details
            IdleCycle = Length + PresentCycle
            self.IdleStartRecvCycle[i] = IdleCycle
            self.IdleStartSendCycle[TargetIndex] = IdleCycle
            # ------------------------ Log Label -----------------------
            Log[i] += Length
            Log[TargetIndex] += Length
            # ------------------------ Log Label -----------------------
            if IdleCycle not in IncrementCycle:
                IncrementCycle.append(IdleCycle)
        return IncrementCycle, Log, CoreEventCycle


class Block:
    def __init__(self, CoreNum, FunctionList, MemorySize, BlockAddress, MemLimitList, UpdateLimitList, BufferSize=8,
                 InitMemIDList = None, InitMemNumList = None, StateNum = 1, TravelState = [None], NextState = []):
        self.EdgeNum = 4
        self.Address = BlockAddress
        self.Event = [[0] for _ in range(CoreNum)]
        self.CoreIdleCycle = [[0] for _ in range(CoreNum)]
        self.PushEvent = [[] for _ in range(CoreNum)]
        self.CoreNum = CoreNum
        if InitMemIDList is None:
            InitMemIDList = [ [] for _ in range(CoreNum) ]
        if InitMemNumList is None:
            InitMemNumList = [ [] for _ in range(CoreNum) ]
        self.Cores = [Core(FunctionList[i][0], FunctionList[i][1], FunctionList[i][2], MemorySize, i, MemLimitList[i],
                           UpdateLimitList[i], InitMemIDList[i], InitMemNumList[i], StateNum[i], TravelState[i], NextState[i])
                      for i in range(CoreNum)]
        self.Controller = Controller(CoreNum, BufferSize)
        self.WaitingMessage = [[] for _ in range(CoreNum)]
    
    def SendMessages(self):
        return self.Controller.ERTop() + [self.Controller.DRAMRecvFF.Top()]

    def Process(self, PresentCycle):
        WorkChip = []
        Log = [np.zeros(self.CoreNum),
               np.zeros((self.CoreNum + self.EdgeNum + 1))]
        for core in range(self.CoreNum):
            if (len(self.Event[core]) != 0 and self.Event[core][0] == PresentCycle) or (len(self.PushEvent[core]) != 0 and self.PushEvent[core][0] == PresentCycle):
                WorkChip.append(core)
        IncrementCycle = []
        # In Block Operation
        # Core Processing
        CoreInfo = self.Controller.CRTop()
        CoreFull = self.Controller.CSFull()
        for index in WorkChip:
            # PushCycle = None
            if CoreFull[index] and len(self.PushEvent[index]) != 0 and self.PushEvent[index][0] == PresentCycle:
                self.PushEvent[index] = list(np.array(self.PushEvent[index]) + 1)
                continue
            if len(self.PushEvent[index]) != 0 and self.PushEvent[index][0] == PresentCycle:
                Detail, _ = self.WaitingMessage[index][0]
                _, _, Length = Detail
                self.Controller.CSPush(index, self.WaitingMessage[index][0])
                self.WaitingMessage[index].pop(0)
                self.PushEvent[index].pop(0)
                PushCycle = PresentCycle + Length
                if PushCycle not in IncrementCycle:
                    IncrementCycle.append(PushCycle)
                if len(self.Event[index]) != 0 and PushCycle >= self.Event[index][0]:
                    self.Event[index] = list(np.array(self.Event[index]) + PushCycle - self.Event[index][0])
                elif PushCycle not in self.Event[index]:
                    self.Event[index].append(PushCycle)
                # ---------------------- Log Label -----------------
                Log[1][index] += Length
                # ---------------------- Log Label -----------------
                continue
            elif len(self.PushEvent[index]) != 0:
                if len(self.Event[index]) != 0 and self.PushEvent[index][-1] >= self.Event[index][0]:
                    self.Event[index] = list(np.array(self.Event[index]) + self.PushEvent[index][-1] - self.Event[index][0])
                continue
            if len(self.Event[index]) != 0 and self.Event[index][0] != PresentCycle:
                continue
            if CoreInfo[index] != None and len(self.Event[index]) != 0:
                self.Controller.CRPop(index)
            CostCycles, MessageDetails, MessageID = self.Cores[index].Process(CoreInfo[index])
            if CostCycles == None:
                self.Event[index].pop(0)
                continue
            # ------------------------------ Log Label ------------------------------------
            if len(CostCycles) > 0:
                Log[0][index] += max(CostCycles)
            # ------------------------------ Log Label ------------------------------------
            next_cycle = PresentCycle
            Dest, Length, Type = MessageDetails
            for i in range(len(CostCycles)):
                next_cycle += CostCycles[i]
                if Dest[i] == None:
                    TryCycle = max(next_cycle, PresentCycle + 1)
                    if i == len(CostCycles) - 1:
                        IncrementCycle.append(TryCycle)
                    if Type[i] == None and TryCycle not in self.Event[index]:
                        self.Event[index].append(TryCycle)
                    continue
                if len(self.PushEvent[index]) != 0 and next_cycle <= self.PushEvent[index][-1]:
                    next_cycle = self.PushEvent[index][-1] + 1
                self.PushEvent[index].append(next_cycle)
                self.PushEvent[index].sort()
                AddIndex = self.PushEvent[index].index(next_cycle)
                self.WaitingMessage[index].insert(AddIndex, ((Type[i], Dest[i], Length[i]), MessageID[i]))
                IncrementCycle.append(next_cycle)
            self.Event[index].pop(0)
        # Controller Processing
        CtrlCycle, CtrlLog, CoreEvent = self.Controller.Process(self.Address, PresentCycle)
        for cycle in CtrlCycle:
            if cycle not in IncrementCycle:
                IncrementCycle.append(cycle)
        for i in range(self.CoreNum):
            for cycle in CoreEvent[i]:
                if cycle not in self.Event[i]:
                    self.Event[i].append(cycle)
            self.Event[i].sort()
        # ----------------------------- Log Label -----------------------------
        Log[1] += CtrlLog
        # ----------------------------- Log Label -----------------------------
        RealEvent = [len(self.Event[i]) for i in range(self.CoreNum) if len(self.PushEvent[i]) == 0] + [len(self.PushEvent[i]) for i in range(self.CoreNum)]
        if len(RealEvent) != 0 and max(RealEvent) != 0:
            Necessary = min([self.Event[i][0] for i in range(self.CoreNum) if len(self.Event[i]) != 0 and len(self.PushEvent[i]) == 0] + 
                            [self.PushEvent[i][0] for i in range(self.CoreNum) if len(self.PushEvent[i]) != 0])
            if Necessary not in IncrementCycle:
                IncrementCycle.append(Necessary)
        return IncrementCycle, Log


class DRAMControl:
    def __init__(self, ConnNum, MaxPop, DRAMLatency):
        self.ConnNum = ConnNum
        self.MaxPop = MaxPop
        self.WaitCounter = np.zeros(ConnNum)
        self.DRAMLatency = DRAMLatency
        self.SendDest = []
        self.Info = []
        self.BookList = []

    def DRAMMessage(self):
        Dest = []
        Info = []
        PopList = []
        ContinueRead = False
        if 0 < len(self.BookList) < self.MaxPop:
            PopList = []
            for i in range(len(self.BookList)):
                d, m, num = self.BookList[i]
                self.BookList[i] = (d, m, num - 1)
                if num - 1 == 0:
                    PopList.append(i)
                Dest.append(d)
                Info.append(m)
            if len(self.SendDest) > 0:
                Dest += self.SendDest[0]
                Info += self.Info[0]
            if len(Dest) > self.MaxPop:
                RestDest = Dest[self.MaxPop:]
                RestInfo = Info[self.MaxPop:]
            else:
                RestDest = []
                RestInfo = []
            if len(self.SendDest) > 1 and len(RestDest) > 0:
                self.SendDest[1] += RestDest
                self.Info[1] += RestInfo
                ContinueRead = True
            elif len(RestDest) > 0:
                self.SendDest.append(RestDest)
                self.Info.append(Info)
                ContinueRead = True
            if len(self.SendDest) > 0:
                self.SendDest.pop(0)
                self.Info.pop(0)
            if len(PopList) < len(self.BookList):
                ContinueRead = True
        elif len(self.BookList) >= self.MaxPop:
            PopList = []
            for i in range(len(self.MaxPop)):
                d, m, num = self.BookList[i]
                self.BookList[i] = (d, m, num - 1)
                if num - 1 == 0:
                    PopList.append(i)
                Dest.append(d)
                Info.append(m)
            ContinueRead = True
        elif len(self.SendDest) == 0:
            return [], [], False
        else:
            Dest += self.SendDest[0]
            Info += self.Info[0]
            if len(Dest) > self.MaxPop:
                RestDest = Dest[self.MaxPop:]
                RestInfo = Info[self.MaxPop:]
            else:
                RestDest = []
                RestInfo = []
            if len(self.SendDest) > 1 and len(RestDest) > 0:
                self.SendDest[1] += RestDest
                self.Info[1] += RestInfo
                ContinueRead = True
            elif len(RestDest) > 0:
                self.SendDest.append(RestDest)
                self.Info.append(RestDest)
                ContinueRead = True
            if len(self.SendDest) > 0:
                self.SendDest.pop(0)
                self.Info.pop(0)
        PopList.reverse()
        for item in PopList:
            self.BookList.pop(item)
        return Dest, Info, ContinueRead

    def Process(self, Info, Index):
        TotalSum = 0
        TempIndex = []
        TempInfo = []
        TempBookList = []
        for i in range(len(Info)):
            item = Info[i]
            Details, ID = item
            Type, Dest, Length = Details
            chipx, chipy, blockx, blocky, core = Dest
            Dest = (chipx, chipy, blockx, blocky, int(core))
            Details = (int(Type), Dest, Length)
            Message = (Details, int(ID))
            TotalSum += Length
            if type(Type) == str and type(ID) == str:
                TempBookList.append((Dest, Message, int(ID)))
            elif type(Type) == str:
                TempIndex.append(Dest)
                TempInfo.append(Message)
        if TotalSum < self.MaxPop:
            self.SendDest.append(TempIndex)
            self.Info.append(TempInfo)
            self.BookList += TempBookList
            return Index, Info
        TempIndex = []
        TempInfo = []
        TempBookList = []
        self.WaitCounter[Index] += 1
        tempList = zip(range(self.ConnNum), self.WaitCounter)
        Select = heapq.nlargest(self.MaxPop, tempList, key=lambda x:x[1])
        Index = [item[0] for item in Select]
        self.WaitCounter[Index] = 0
        for i in range(len(Index)):
            Details, ID = Info[Index[i]]
            Type, Dest, Length = Details
            chipx, chipy, blockx, blocky, core = Dest
            Dest = (chipx, chipy, blockx, blocky, int(core))
            Details = (int(Type), Dest, Length)
            Message = (Details, int(ID))
            TotalSum += Length
            if type(Type) == str and type(ID) == str:
                TempBookList.append(Dest, Message, int(ID))
            elif type(Type) == str:
                TempIndex.append(Dest)
                TempInfo.append(Message)
        self.SendDest.append(Dest)
        self.Info.append(TempInfo)
        self.BookList += TempBookList
        return Index, Info[Index]


class ExtConn:
    def __init__(self, ConnNum, BufferSize, IndexBias, IndexStep):
        self.ConnNum = ConnNum
        self.WaitCounter = np.zeros(ConnNum)
        self.SendFF = FIFO(BufferSize * ConnNum)
        self.RecvFF = FIFO(BufferSize * ConnNum)
        self.IndexBias = IndexBias
        self.IndexStep = IndexStep
    
    def RealPush(self, TargetInfo:list):
        self.SendFF.Push(TargetInfo)
        return

    def Push(self, Info:list, Index:list):
        if self.SendFF.Full():
            return None, None
        TempIndex = (np.array(Index) - self.IndexBias) / self.IndexStep
        self.WaitCounter[TempIndex.astype(int)] += 1
        Target = np.where(self.WaitCounter == self.WaitCounter.max())[0][0]
        self.WaitCounter[Target] = 0
        Target = int(Target * self.IndexStep + self.IndexBias)
        TargetInfo = Info[Index.index(Target)]
        return Target, TargetInfo
    
    def STop(self):
        return self.SendFF.Top()
    
    def RTop(self):
        return self.RecvFF.Top()
    
    def SFull(self):
        return self.SendFF.Full()
    
    def RFull(self):
        return self.RecvFF.Full()


class Chip:
    def __init__(self, ChipAddress, BlockNum, CoreNum, FunctionList, MemorySize, MemLimitList, UpdateLimitList, BufferSize=8, InitMemIDList = None,
                 InitMemNumList = None, DRAMLatency = 36, DRAMWidth = 256, StateNum = 1, TravelState = [None], NextState=[]):
        self.EdgeNum = 4
        self.CoreNum = CoreNum
        self.ChipX, self.ChipY = ChipAddress
        self.BlockX, self.BlockY = BlockNum
        self.Event = [[0] for _ in range(self.BlockX) for __ in range(self.BlockY)]
        self.CommIdleCycle = [[0 for ___ in range(self.EdgeNum + 1)] for _ in range(self.BlockX) for __ in range(self.BlockY)]
        self.ExtSendIdleCycle = [0 for _ in range(self.EdgeNum)]
        self.ExtRecvIdleCycle = [0 for _ in range(self.EdgeNum)]
        self.DRAMLatency = DRAMLatency
        self.DRAMPushEvent = []
        self.DRAMPopIndex = []
        self.DRAMRealPush = []
        self.DRAMPushWait = []
        self.DRAMIdleCycle = 0
        self.DRAMInfo = [[] for _ in range(self.BlockX) for __ in range(self.BlockY)]
        self.DRAMConn = DRAMControl(self.BlockX * self.BlockY, DRAMWidth, DRAMLatency)
        self.Blocks = [Block(CoreNum, FunctionList[int(j * self.BlockY + i)], MemorySize, (self.ChipX, self.ChipY, i, j),
                             MemLimitList[int(j * self.BlockY + i)], UpdateLimitList[int(j * self.BlockY + i)],
                             BufferSize, InitMemIDList[int(j * self.BlockY + i)], InitMemNumList[int(j * self.BlockY + i)],
                             StateNum[int(j * self.BlockY + i)], TravelState[int(j * self.BlockY + i)], NextState[int(j * self.BlockY + i)])
                       for j in range(self.BlockY) for i in range(self.BlockX)]
        self.ExtConn = [ExtConn(self.BlockY, BufferSize, self.BlockX - 1, self.BlockX),
                        ExtConn(self.BlockX, BufferSize, 0, 1),
                        ExtConn(self.BlockY, BufferSize, 0, self.BlockX),
                        ExtConn(self.BlockX, BufferSize, (self.BlockY - 1) * self.BlockX, 1)]
        self.WaitMessage = [[], [], [], []]
        self.Direct = [(1, 0), (0, -1), (-1, 0), (0, 1), None]

    def Process(self, PresentCycle):
        global CounterReturn
        WorkChip = []
        WorkFF = []
        ExtConnInfo = [[] for _ in range(self.EdgeNum)]
        ExtConnIndex = [[] for _ in range(self.EdgeNum)]
        BlockConnInfo = []
        Log = [np.zeros((self.BlockX, self.BlockY, self.CoreNum)),
               np.zeros((self.BlockX, self.BlockY, self.CoreNum + self.EdgeNum + 1)),
               np.zeros((self.BlockX, self.BlockY, self.EdgeNum + 1)),
               0]
        for blocky in range(self.BlockY):
            for blockx in range(self.BlockX):
                index = blocky * self.BlockX + blockx
                if len(self.Event[index]) != 0 and self.Event[index][0] == PresentCycle:
                    WorkChip.append(index)
                TempInfo = self.Blocks[index].SendMessages()
                WorkIndex = [i for i in range(len(TempInfo)) if TempInfo[i] is not None]
                if len(WorkIndex) != 0:
                    BlockConnInfo.append(TempInfo)
                    WorkFF.append((blockx, blocky, WorkIndex))
        IncrementCycle = []
        if WorkChip == []:
            pass
        else:
            # In Chip Operation
            # Block Function Processing
            for index in WorkChip:
                next_cycle_group, BlockLog = self.Blocks[index].Process(PresentCycle)
                # --------------------------- Log Label ---------------------------
                blockx = index % self.BlockX
                blocky = int(index / self.BlockX)
                Log[0][blockx, blocky, :] += BlockLog[0]
                Log[1][blockx, blocky, :] += BlockLog[1]
                # --------------------------- Log Label ---------------------------
                if next_cycle_group == None:
                    continue
                for next_cycle in next_cycle_group:
                    if next_cycle in self.Event[index]:
                        pass
                    else:
                        self.Event[index].append(next_cycle)
                    if next_cycle not in IncrementCycle:
                        IncrementCycle.append(next_cycle)
                self.Event[index].pop(0)
                self.Event[index].sort()
        if WorkFF == []:
            pass
        else:
            # Block Communication
            DRAMAccess = []
            DRAMIndex = []
            for i in range(len(WorkFF)):
                index_group = WorkFF[i]
                blockx, blocky, index_list = index_group
                blockIndex = int(blocky * self.BlockX + blockx)
                for index in index_list:
                    if self.CommIdleCycle[blockIndex][index] > PresentCycle:
                        continue
                    elif self.CommIdleCycle[blockIndex][index] == PresentCycle:
                        TBX = blockx + self.Direct[index][0]
                        TBY = blocky + self.Direct[index][1]
                        TBI = int(TBY * self.BlockX + TBX)
                        TI = (index + 2) % 4
                        self.Blocks[blockIndex].Controller.EdgeRecvFF[index].Pop()
                        if 0 <= TBX < self.BlockX and 0 <= TBY < self.BlockY:
                            self.Blocks[TBI].Controller.EdgeSendFF[TI].Push(BlockConnInfo[i][index])
                            if PresentCycle + 1 not in self.Event[TBI]:
                                self.Event[TBI].append(PresentCycle + 1)
                        if PresentCycle + 1 not in IncrementCycle:
                            IncrementCycle.append(PresentCycle + 1)
                    if self.Direct[index] == None:
                        DRAMAccess.append(BlockConnInfo[i][index])
                        DRAMIndex.append(blockIndex)
                    else:
                        TBX = blockx + self.Direct[index][0]
                        TBY = blocky + self.Direct[index][1]
                        TBI = int(TBY * self.BlockY + TBX)
                        TI = (index + 2) % 4
                        if TBX >= self.BlockX:
                            ExtConnInfo[0].append(BlockConnInfo[i][index])
                            ExtConnIndex[0].append(blockIndex)
                        elif TBY < 0:
                            ExtConnInfo[1].append(BlockConnInfo[i][index])
                            ExtConnIndex[1].append(blockIndex)
                        elif TBX < 0:
                            ExtConnInfo[2].append(BlockConnInfo[i][index])
                            ExtConnIndex[2].append(blockIndex)
                        elif TBY >= self.BlockY:
                            ExtConnInfo[3].append(BlockConnInfo[i][index])
                            ExtConnIndex[3].append(blockIndex)
                        elif self.Blocks[TBI].Controller.EdgeRecvFF[TI].Full():
                            pass
                        else:
                            Details, _ = BlockConnInfo[i][index]
                            _, _, Length = Details
                            NextCycle = PresentCycle + Length * 2 - 1
                            self.CommIdleCycle[blockIndex][index] = NextCycle
                            # ---------------------------- Log Label ---------------------------
                            Log[2][blockx, blocky, index] += Length * 2
                            Log[2][TBX, TBY, TI] += Length * 2
                            # ---------------------------- Log Label ---------------------------
                            if NextCycle not in IncrementCycle:
                                IncrementCycle.append(NextCycle)
            if len(DRAMAccess) != 0 and self.DRAMIdleCycle < PresentCycle:
                DRAMSelectAddress, Messages = self.DRAMConn.Process(DRAMAccess, DRAMIndex)
                self.DRAMPopIndex.append(DRAMSelectAddress)
                for i in range(len(DRAMSelectAddress)):
                    addr = DRAMSelectAddress[i]
                    Details, ID = Messages[i]
                    _, _, Length = Details
                    # ---------------------------- Log Label ---------------------------
                    blockx = addr % self.BlockX
                    blocky = int(addr / self.BlockX)
                    Log[2][blockx, blocky, self.EdgeNum] += Length * 2
                    Log[3] += Length * 2
                    # ---------------------------- Log Label ---------------------------
                self.DRAMIdleCycle = PresentCycle + Length * 2 - 1
                if self.DRAMIdleCycle not in IncrementCycle:
                    IncrementCycle.append(self.DRAMIdleCycle)
                if len(Messages) != 0:
                    DRAMCycle = PresentCycle + self.DRAMLatency
                    self.DRAMPushEvent.append(DRAMCycle)
                    if DRAMCycle not in IncrementCycle:
                        IncrementCycle.append(DRAMCycle)
            elif self.DRAMIdleCycle == PresentCycle:
                DRAMSelectAddress = self.DRAMPopIndex[0]
                for i in range(len(DRAMSelectAddress)):
                    addr = DRAMSelectAddress[i]
                    self.Blocks[addr].Controller.DRAMRecvFF.Pop()
                self.DRAMPopIndex.pop(0)

        if PresentCycle in self.DRAMPushEvent:
            Index, Info, ContinuePop = self.DRAMConn.DRAMMessage()
            if ContinuePop and len(self.DRAMPushEvent) > 0:
                self.DRAMPushEvent.append(self.DRAMPushEvent[-1] + 1)
            elif ContinuePop:
                self.DRAMPushEvent.append(PresentCycle + 1)
            for i in range(len(Index)):
                _, _, blockx, blocky, _ = Index[i]
                blockIndex = int(blocky * self.BlockX + blockx)
                self.DRAMInfo[blockIndex].append(Info[i])
            for blockx in range(self.BlockX):
                for blocky in range(self.BlockY):
                    blockIndex = int(blocky * self.BlockX + blockx)
                    if self.DRAMInfo[blockIndex] == []:
                        continue
                    if  self.Blocks[blockIndex].Controller.DRAMSendFF.Full():
                        self.DRAMPushEvent = [PresentCycle] + (np.array(self.DRAMPushEvent) + 1).tolist()
                        if PresentCycle + 1 not in IncrementCycle:
                            IncrementCycle.append(PresentCycle + 1)
                        continue
                    self.Blocks[blockIndex].Controller.DRAMSendFF.Push(self.DRAMInfo[blockIndex][0])
                    # ---------------------------- Log Label ---------------------------
                    Details, _ = self.DRAMInfo[blockIndex][0]
                    _, _, Length = Details
                    Log[2][blockx, blocky, self.EdgeNum] += Length * 2 - 1
                    # ---------------------------- Log Label ---------------------------
                    self.DRAMInfo[blockIndex].pop(0)
                    if PresentCycle + 1 not in self.Event[blockIndex]:
                        self.Event[blockIndex].append(PresentCycle + 1)
                    if PresentCycle + 1 not in IncrementCycle:
                        IncrementCycle.append(PresentCycle + 1)
            self.DRAMPushEvent.remove(PresentCycle)
        for i in range(self.EdgeNum):
            if ExtConnInfo[i] != [] and self.ExtSendIdleCycle[i] < PresentCycle:
                Target, Info = self.ExtConn[i].Push(ExtConnInfo[i], ExtConnIndex[i])
                if Target != None:
                    Details, _ = Info
                    _, _, Length = Details
                    PushCycle = PresentCycle + Length * 2 - 1
                    self.CommIdleCycle[Target][i] = PushCycle
                    self.ExtSendIdleCycle[i] = PushCycle
                    # ---------------------------- Log Label ---------------------------
                    blockx = Target % self.BlockX
                    blocky = int(Target / self.BlockX)
                    Log[2][blockx, blocky, i] += Length * 2
                    # ---------------------------- Log Label ---------------------------
                    self.WaitMessage[i].append((Target, Info))
                    if PushCycle not in IncrementCycle:
                        IncrementCycle.append(PushCycle)
            elif ExtConnInfo[i] != [] and self.ExtSendIdleCycle[i] == PresentCycle:
                Target, Info = self.WaitMessage[i][0]
                self.WaitMessage[i].pop(0)
                self.ExtConn[i].RealPush(Info)
                if PresentCycle + 1 not in IncrementCycle:
                    IncrementCycle.append(PresentCycle + 1)
            GetInfo = self.ExtConn[i].RecvFF.Top()
            if self.ExtRecvIdleCycle[i] > PresentCycle:
                continue
            elif self.ExtRecvIdleCycle[i] == PresentCycle and GetInfo != None:
                Details, _ = GetInfo
                _, Dest, Length = Details
                _, _, blockx, blocky, _ = Dest
                if i == 0 or i == 2:
                    blockIndex = int(blocky * self.ExtConn[i].IndexStep + self.ExtConn[i].IndexBias)
                else:
                    blockIndex = int(blockx * self.ExtConn[i].IndexStep + self.ExtConn[i].IndexBias)
                self.Blocks[blockIndex].Controller.EdgeSendFF[i].Push(GetInfo)
                self.ExtConn[i].RecvFF.Pop()
                if PresentCycle + 1 not in self.Event[blockIndex]:
                    self.Event[blockIndex].append(PresentCycle + 1)
                if PresentCycle + 1 not in IncrementCycle:
                    IncrementCycle.append(PresentCycle + 1)
                continue
            if GetInfo != None:
                Details, _ = GetInfo
                _, Dest, Length = Details
                _, _, blockx, blocky, _ = Dest
                if i == 0 or i == 2:
                    blockIndex = int(blocky * self.ExtConn[i].IndexStep + self.ExtConn[i].IndexBias)
                else:
                    blockIndex = int(blockx * self.ExtConn[i].IndexStep + self.ExtConn[i].IndexBias)
                if not self.Blocks[blockIndex].Controller.EdgeSendFF[i].Full():
                    PopCycle = PresentCycle + Length * 2 - 1
                    self.ExtRecvIdleCycle[i] = PopCycle
                    # ---------------------------- Log Label ---------------------------
                    bx = blockIndex % self.BlockX
                    by = int(blockIndex / self.BlockX)
                    Log[2][bx, by, i] += Length * 2
                    # ---------------------------- Log Label ---------------------------
                    if PopCycle not in IncrementCycle:
                        IncrementCycle.append(PopCycle)
        for index in range(int(self.BlockX * self.BlockY)):
            self.Event[index].sort()
        return IncrementCycle, Log


class Simulator:
    def __init__(self, ChipNum, BlockNum, CoreNum, FunctionList, MemorySize, MemLimitList, UpdateLimitList, BufferSize=8, InitMemIDList = None,
                 InitMemNumList = None, DRAMLatency = 36, DRAMWidth = 256, StateNum = 1, TravelState = [None], NextState = [], InputList:list = [],
                 ConnPort = (0, 0, 2)):
        self.EdgeNum = 4
        self.PresentCycle = 0
        self.ChipNumX, self.ChipNumY = ChipNum
        self.BlockNumX, self.BlockNumY = BlockNum
        self.Chips = [Chip((i, j), BlockNum, CoreNum, FunctionList[int(j * self.ChipNumX + i)], MemorySize, MemLimitList[int(j * self.ChipNumX + i)],
                           UpdateLimitList[int(j * self.ChipNumX + i)], BufferSize, InitMemIDList[int(j * self.ChipNumX + i)],
                           InitMemNumList[int(j * self.ChipNumX + i)], DRAMLatency, DRAMWidth, StateNum[int(j * self.ChipNumX + i)],
                           TravelState[int(j * self.ChipNumX + i)], NextState[int(j * self.ChipNumX + i)])
                           for j in range(self.ChipNumY) for i in range(self.ChipNumX)]
        self.Event = [[0] for _ in range(self.ChipNumY) for __ in range(self.ChipNumX)]
        self.ExtIdleCycle = [[0 for _ in range(4)] for _ in range(self.ChipNumY) for __ in range(self.ChipNumX)]
        self.Direct = [(1, 0), (0, -1), (-1, 0), (0, 1)]
        self.InputList = InputList
        self.InputIdleCycle = 0
        self.InputIndex = ConnPort[1] * self.ChipNumX + ConnPort[0]
        self.InX, self.InY, self.ConnPort = ConnPort
        self.log = {
            "CoreCompute":np.zeros((self.ChipNumX, self.ChipNumY, self.BlockNumX, self.BlockNumY, CoreNum)),
            "InBlockComm":np.zeros((self.ChipNumX, self.ChipNumY, self.BlockNumX, self.BlockNumY, CoreNum + self.EdgeNum + 1)),
            "InChipComm":np.zeros((self.ChipNumX, self.ChipNumY, self.BlockNumX, self.BlockNumY, self.EdgeNum + 1)),
            "ExtChipComm":np.zeros((self.ChipNumX, self.ChipNumY, self.EdgeNum + 1))
        }
        self.TimeLog = []

    def Process(self):
        if len(self.InputList) != 0 and (self.PresentCycle > self.InputIdleCycle or self.PresentCycle == 0):
            Message = self.InputList[0]
            if not self.Chips[self.InputIndex].ExtConn[self.ConnPort].RFull():
                Details, _ = Message
                _, _, Length = Details
                InputCycle = self.PresentCycle + Length * 4 - 1
                # -------------------------- Log Label ------------------------------
                self.log["ExtChipComm"][self.InX, self.InY, self.ConnPort] += Length * 4
                # -------------------------- Log Label ------------------------------
                self.InputIdleCycle = InputCycle
                if InputCycle not in self.Event[self.InputIndex]:
                    self.Event[self.InputIndex].append(InputCycle)
        elif len(self.InputList) != 0 and self.PresentCycle == self.InputIdleCycle:
            Message = self.InputList[0]
            self.Chips[self.InputIndex].ExtConn[self.ConnPort].RecvFF.Push(Message)
            self.InputList.pop(0)
            if len(self.InputList) != 0 and self.PresentCycle + 1 not in self.Event[self.InputIndex]:
                self.Event[self.InputIndex].append(self.PresentCycle + 1)

        for chipy in range(self.ChipNumY):
            for chipx in range(self.ChipNumX):
                chipIndex = int(chipy * self.ChipNumX + chipx)
                if len(self.Event[chipIndex]) == 0:
                    pass
                elif self.Event[chipIndex][0] == self.PresentCycle:
                    next_cycle_group, LogDetail = self.Chips[chipIndex].Process(self.PresentCycle)
                    for next_cycle in next_cycle_group:
                        if next_cycle in self.Event[chipIndex]:
                            pass
                        else:
                            self.Event[chipIndex].append(next_cycle)
                            self.Event[chipIndex].sort()
                    self.Event[chipIndex].pop(0)
                    self.Event[chipIndex].sort()
                    # -------------------------- Log Label ------------------------------
                    self.log["CoreCompute"][chipx, chipy, :, :, :] += LogDetail[0]
                    self.log["InBlockComm"][chipx, chipy, :, :, :] += LogDetail[1]
                    self.log["InChipComm"][chipx, chipy, :, :, :] += LogDetail[2]
                    self.log["ExtChipComm"][chipx, chipy, self.EdgeNum] += LogDetail[3]
                    # -------------------------- Log Label ------------------------------
                for i in range(self.EdgeNum):
                    Message = self.Chips[chipIndex].ExtConn[i].STop()
                    if Message is None:
                        continue
                    TargetX = chipx + self.Direct[i][0]
                    TargetY = chipy + self.Direct[i][1]
                    if TargetX >= self.ChipNumX or TargetX < 0 or TargetY >= self.ChipNumY or TargetY < 0:
                        raise Exception("Destination Out of Bounds")
                    if self.ExtIdleCycle[chipIndex][i] > self.PresentCycle:
                        continue
                    TargetIndex = int(TargetY * self.ChipNumX + TargetX)
                    if self.ExtIdleCycle[chipIndex][i] == self.PresentCycle:
                        self.Chips[chipIndex].ExtConn[i].SendFF.Pop()
                        self.Chips[TargetIndex].ExtConn[(i + 2) % 4].RecvFF.Push(Message)
                        if self.PresentCycle + 1 not in self.Event[TargetIndex]:
                            self.Event[TargetIndex].append(self.PresentCycle + 1)
                        continue
                    if self.Chips[TargetIndex].ExtConn[(i + 2) % 4].RFull():
                        if self.PresentCycle + 1 not in self.Event[chipIndex]:
                            self.Event[chipIndex].append(self.PresentCycle + 1)
                        continue
                    Details, _ = Message
                    _, _, Length = Details
                    PopCycle = self.PresentCycle + Length * 4 - 1
                    self.ExtIdleCycle[chipIndex][i] = PopCycle
                    self.log["ExtChipComm"][chipx, chipy, i] += Length * 4
                    self.log["ExtChipComm"][chipx, chipy, (i + 2) % 4] += Length * 4
        for i in range(len(self.Event)):
            self.Event[i].sort()
        PossNext = [self.Event[i][0] for i in range(len(self.Chips)) if len(self.Event[i]) != 0]
        if len(PossNext) == 0:
            NextCycle = None
        else:
            NextCycle = min(PossNext)
        if NextCycle != None and self.PresentCycle > NextCycle:
            raise Exception("Error cycle count")
        else:
            self.PresentCycle = NextCycle
        return self.log
    
    def ResetLog(self):
        for name in self.log:
            self.log[name] *= 0
        return
    
    def RealSto(self):
        StateDone = True
        for chip in self.Chips:
            for block in chip.Blocks:
                for core in block.Cores:
                    StateDone = (len(core.MemoryID) == 0) and StateDone
        return StateDone or self.PresentCycle is None

    def EmptyLog(self):
        MaxLog = max(self.log["CoreCompute"].max(), self.log["InBlockComm"].max(), self.log["InChipComm"].max(), self.log["ExtChipComm"].max())
        return MaxLog == 0

    def StepSim(self):
        PastCycle = 0
        folder_name = "./Data/SimLog/" + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        os.makedirs(folder_name, exist_ok=True)
        while not self.RealSto():
            LastCycle = self.PresentCycle
            if self.PresentCycle - PastCycle >= 1000:
                print("Present Processing Cycle:", self.PresentCycle)
                PastCycle = self.PresentCycle
                CopyLog = copy.deepcopy(self.log)
                CopyLog = {name:CopyLog[name].tolist() for name in CopyLog}
                with open(folder_name + f'/Log{self.PresentCycle}.json', "w", encoding="utf-8") as f:
                    json.dump(CopyLog, f, ensure_ascii=False, indent=4)
                if self.EmptyLog():
                    break
                self.ResetLog()
            self.Process()
        CopyLog = copy.deepcopy(self.log)
        CopyLog = {name:CopyLog[name].tolist() for name in CopyLog}
        with open(folder_name + f'/Log{LastCycle}.json', "w", encoding="utf-8") as f:
            json.dump(CopyLog, f, ensure_ascii=False, indent=4)
        print("Last Processing Cycle:", LastCycle)
        return folder_name


def main():
    return


if __name__ == "__main__":
    main()