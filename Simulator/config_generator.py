import numpy as np
import copy
from Simulator.Modules import Func, Simulator


def TranAddr(DestTuple:tuple, PresentTuple:tuple, AddrType:int,
             BlockX:int, BlockY:int, ChipX:int, ChipY:int):
    chipx, chipy, blockx, blocky, core = DestTuple
    if AddrType == 1:
        DestTuple = (chipx, chipy, blockx, blocky, core)
    else:
        pcx, pcy, pbx, pby, pco = PresentTuple
        T = type(core)
        fcx = chipx + pcx
        fcy = chipy + pcy
        fbx = blockx + pbx
        fby = blocky + pby
        if fbx >= BlockX:
            fbx -= BlockX
            fcx += 1
        elif fbx < 0:
            fbx += BlockX
            fcx -= 1
        if fby >= BlockY:
            fby -= BlockY
            fcy += 1
        elif fby < 0:
            fby += BlockY
            fcy -= 1
        if fcx < 0 or fcx >= ChipX or fcy < 0 or fcy >= ChipY:
            raise Exception("Destination ({} {} {} {})Out of Bounds".format(fcx, fcy, fbx, fby))
        DestTuple = (fcx, fcy, fbx, fby, T(int(core) + pco))
    return DestTuple


class Reflection:
    def __init__(self, config:dict, Scale:tuple):
        self.AddressType:list = config["AddressType"]    # 0: relative address;  1: absolute address
        self.DestType:list = config["DestType"]          # 0: determined dest;   1: possibility distribution
        self.CycleType:list = config["CycleType"]        # 0: determined dest;   1: possibility distribution
        self.OpSel:list = config["OpSel"]                # 0: Send;  1: Storage; 2: Delete
        self.DestTuple:list = config["DestTuple"]        # chipx, chipy, blockx, blocky, core
        self.CycleCost:list = config["CycleCost"]        # cycle cost of each output
        self.UpdateReq:list = config["UpdateReq"]        # Update signals
        self.Length:list = config["Length"]              # Output length
        self.OutType:list = config["OutType"]            # Output Type
        if self.DestType == 0:
            self.DestDist = None
        else:
            self.DestDist = config["DestDist"]
        if self.CycleType == 0 or self.CycleType == 2:
            self.CycleDist = None
        else:
            self.CycleDist = config["CycleDist"]
        self.ChipX, self.ChipY, self.BlockX, self.BlockY = Scale
    
    def DestListGenerate(self, PresentTuple:tuple):
        if self.DestType == 0:
            DestTuple = []
            for i in range(len(self.DestTuple)):
                TempTuple = TranAddr(self.DestTuple[i], PresentTuple, self.AddressType[i],
                                     self.BlockX, self.BlockY, self.ChipX, self.ChipY)
                DestTuple.append(TempTuple)
            return (self.DestType, DestTuple)
        elif self.DestType == 1:
            DestTuple = []
            for i in range(len(self.DestDist)):
                Group = []
                for j in range(len(self.DestTuple[i])):
                    TempTuple = TranAddr(self.DestTuple[i][j], PresentTuple, self.AddressType[i][j],
                                         self.BlockX, self.BlockY, self.ChipX, self.ChipY)
                    Group.append(TempTuple)
                DestTuple.append(Group)
            return (self.DestType, (self.DestDist, DestTuple))
        else:
            DestTuple = []
            for i in range(len(self.DestTuple)):
                Group = []
                for j in range(len(self.DestTuple[i])):
                    TempTuple = TranAddr(self.DestTuple[i][j], PresentTuple, self.AddressType[i][j],
                                         self.BlockX, self.BlockY, self.ChipX, self.ChipY)
                    Group.append(TempTuple)
                DestTuple.append(Group)
            return (self.DestType, DestTuple)

    def CycleListGenerate(self):
        if self.CycleType == 0:
            return (self.CycleType, (self.CycleCost, self.OpSel, self.UpdateReq, self.Length, self.OutType))
        elif self.CycleType == 1:
            return (self.CycleType, (self.CycleDist, self.CycleCost, self.OpSel, self.UpdateReq, self.Length, self.OutType))
        elif self.CycleType == 2:
            PresentList = []
            for IDkind in range(len(self.OpSel)):
                PresentList.append((self.CycleCost[IDkind], self.OpSel[IDkind], self.UpdateReq[IDkind],
                                    self.Length[IDkind], self.OutType[IDkind]))
            return (self.CycleType, PresentList)
        else:
            PresentList = []
            for IDkind in range(len(self.OpSel)):
                PresentList.append((self.CycleDist[IDkind], self.CycleCost[IDkind], self.OpSel[IDkind],
                                    self.UpdateReq[IDkind], self.Length[IDkind], self.OutType[IDkind]))
            return (self.CycleType, PresentList)


class FuncGenerator:
    def __init__(self, TypeNum:int, ReflectDict:dict, PresentPlace:tuple):
        self.TypeNum = TypeNum
        self.ReflectDict:dict = ReflectDict
        self.PresentTuple = PresentPlace
        self.ReflectDict = ReflectDict
        
    def DestDefine(self):
        DestDict = {}
        for name in self.ReflectDict:
            DestDict[name] = self.ReflectDict[name].DestListGenerate(self.PresentTuple)
        return DestDict

    def CycleDefine(self):
        CycleDict = {}
        for name in self.ReflectDict:
            CycleDict[name] = self.ReflectDict[name].CycleListGenerate()
        return CycleDict

    def GenerateFunc(self):
        DestDict = self.DestDefine()
        CycleDict = self.CycleDefine()
        if DestDict == [None] and CycleDict == [None]:
            return None
        else:
            return Func(DestDict, CycleDict)


class CoreDictGenerator:
    def __init__(self, InitFuncDict, ProcFuncDict, MemFuncDict, StateNum:int, MemLimit:dict,
                 UpdateLimit:dict, InitMemNum=[], InitMemID=[], TravelState=[], NextState=[]):
        self.InitFuncDict:list = InitFuncDict
        self.ProcFuncDict:list = ProcFuncDict
        self.MemFuncDict:list = MemFuncDict
        self.StateNum:int = StateNum
        self.MemLimit:dict = MemLimit
        self.UpdateLimit:dict = UpdateLimit
        self.InitMemNum:list = InitMemNum
        self.InitMemID:list = InitMemID
        self.TravelState:list = TravelState
        if NextState == []:
            NextState = [i + 1 for i in range(StateNum)]
            NextState[-1] = 0
        self.NextState:list = NextState
    

    def FuncListGen(self, FuncDict, PresentPlace, Scale):
        FuncList = []
        for StateFunc in FuncDict:
            if StateFunc == None or len(StateFunc) == 0:
                FuncList.append(None)
                continue
            TempDict = {}
            for TypeCounter in StateFunc:
                TempDict.update({TypeCounter:Reflection(StateFunc[TypeCounter], Scale)})
            TempGenerator = FuncGenerator(TypeCounter, TempDict, PresentPlace)
            FuncList.append(TempGenerator.GenerateFunc())
        return FuncList
    
    def CoreListGen(self, PresentPlace, Scale):
        InitFunc = self.FuncListGen(self.InitFuncDict, PresentPlace, Scale)
        ProcFunc = self.FuncListGen(self.ProcFuncDict, PresentPlace, Scale)
        MemFunc = self.FuncListGen(self.MemFuncDict, PresentPlace, Scale)
        FuncList = [InitFunc, ProcFunc, MemFunc]
        return FuncList, self.InitMemID, self.InitMemNum, self.MemLimit, self.UpdateLimit, self.StateNum, self.TravelState, self.NextState


class SimGenerator:
    def __init__(self, ChipX:int, ChipY:int, BlockX:int, BlockY:int, CoreNum:int, MemorySize:int, ReflectList:list,
                 CoreFuncList:list, # InitFunc, [{Corresponding Types: Funcs} Corresponding States]
                                    # ProcFunc, [{Corresponding Types: Funcs} Corresponding States]
                                    # MemFunc, [{Corresponding Types: Funcs} Corresponding States]
                                    # Update Limits [{Corresponding Types: Limits} Corresponding States]
                                    # Memory Trigger [{Corresponding Types: Limits} Corresponding States]
                                    # States that require memory scanning
                                    # State Update Process
                 CoreFuncIndex:dict,
                 InitMemID:dict,
                 InitMemNum:dict,
                 InputList:list=[],
                 ConnPort:tuple=(0, 0, 2)):
        self.ChipX = ChipX
        self.ChipY = ChipY
        self.BlockX = BlockX
        self.BlockY = BlockY
        self.CoreNum = CoreNum
        self.MemorySize = MemorySize
        self.ReflectList = ReflectList
        self.CoreFuncIndex = CoreFuncIndex
        self.CoreGenKind = []
        for coreFunc in CoreFuncList:
            InitRefGroup, ProcRefGroup, MemRefGroup, UpdateLimit, MemLimit, TravelState, NextState = coreFunc
            StateNum = len(InitRefGroup)
            InitDict = []
            ProcDict = []
            MemDict = []
            for state in range(StateNum):
                InitDict.append({i:self.ReflectList[InitRefGroup[state][i]] for i in InitRefGroup[state]})
                ProcDict.append({i:self.ReflectList[ProcRefGroup[state][i]] for i in ProcRefGroup[state]})
                MemDict.append({i:self.ReflectList[MemRefGroup[state][i]] for i in MemRefGroup[state]})
            self.CoreGenKind.append((InitDict, ProcDict, MemDict, StateNum,
                                     MemLimit, UpdateLimit, TravelState, NextState))
        self.InitMemID = InitMemID
        self.InitMemNum = InitMemNum
        self.InputList = InputList
        self.ConnPort = ConnPort
    
    def GenerateSim(self):
        ChipFun = []
        ChipInitMemID = []
        ChipInitMemNum = []
        ChipMemLimit = []
        ChipUpdateLimit = []
        ChipStateNum = []
        ChipTravelState = []
        ChipNextState = []
        for chipy in range(self.ChipY):
            for chipx in range(self.ChipX):
                BlockFun = []
                BlockInitMemID = []
                BlockInitMemNum = []
                BlockMemLimit = []
                BlockUpdateLimit = []
                BlockStateNum = []
                BlockTravelState = []
                BlockNextState = []
                for blocky in range(self.BlockY):
                    for blockx in range(self.BlockX):
                        CoreFun = []
                        CoreInitMemID = []
                        CoreInitMemNum = []
                        CoreMemLimit = []
                        CoreUpdateLimit = []
                        CoreStateNum = []
                        CoreTravelState = []
                        CoreNextState = []
                        for core in range(self.CoreNum):
                            PresentIndex = (chipx, chipy, blockx, blocky, core)
                            TargetCoreType = self.CoreFuncIndex.get(PresentIndex)
                            InitMemID = self.InitMemID.get(PresentIndex)
                            InitMemNum = self.InitMemNum.get(PresentIndex)
                            if InitMemID is None:
                                InitMemID = []
                                InitMemNum = []
                            if TargetCoreType is None:
                                TempGen = CoreDictGenerator(InitFuncDict=[None],
                                                            ProcFuncDict=[None],
                                                            MemFuncDict=[None],
                                                            StateNum=1,
                                                            MemLimit=[{}],
                                                            UpdateLimit=[{}],
                                                            InitMemID=InitMemID,
                                                            InitMemNum=InitMemNum)
                            else:
                                TempGen = CoreDictGenerator(InitFuncDict=self.CoreGenKind[TargetCoreType][0],
                                                            ProcFuncDict=self.CoreGenKind[TargetCoreType][1],
                                                            MemFuncDict=self.CoreGenKind[TargetCoreType][2],
                                                            StateNum=self.CoreGenKind[TargetCoreType][3],
                                                            MemLimit=self.CoreGenKind[TargetCoreType][4],
                                                            UpdateLimit=self.CoreGenKind[TargetCoreType][5],
                                                            TravelState=self.CoreGenKind[TargetCoreType][6],
                                                            NextState=self.CoreGenKind[TargetCoreType][7],
                                                            InitMemID=InitMemID,
                                                            InitMemNum=InitMemNum)
                            Element = TempGen.CoreListGen(PresentIndex, Scale=(self.ChipX, self.ChipY, self.BlockX, self.BlockY))
                            CoreFun.append(Element[0])
                            CoreInitMemID.append(Element[1])
                            CoreInitMemNum.append(Element[2])
                            CoreMemLimit.append(Element[3])
                            CoreUpdateLimit.append(Element[4])
                            CoreStateNum.append(Element[5])
                            CoreTravelState.append(Element[6])
                            CoreNextState.append(Element[7])
                        BlockFun.append(CoreFun)
                        BlockInitMemID.append(CoreInitMemID)
                        BlockInitMemNum.append(CoreInitMemNum)
                        BlockMemLimit.append(CoreMemLimit)
                        BlockUpdateLimit.append(CoreUpdateLimit)
                        BlockStateNum.append(CoreStateNum)
                        BlockTravelState.append(CoreTravelState)
                        BlockNextState.append(CoreNextState)
                ChipFun.append(BlockFun)
                ChipInitMemID.append(BlockInitMemID)
                ChipInitMemNum.append(BlockInitMemNum)
                ChipMemLimit.append(BlockMemLimit)
                ChipUpdateLimit.append(BlockUpdateLimit)
                ChipStateNum.append(BlockStateNum)
                ChipTravelState.append(BlockTravelState)
                ChipNextState.append(BlockNextState)
        return Simulator(ChipNum=(self.ChipX, self.ChipY),
                         BlockNum=(self.BlockX, self.BlockY),
                         CoreNum=self.CoreNum,
                         FunctionList=ChipFun,
                         MemorySize=self.MemorySize,
                         MemLimitList=ChipMemLimit,
                         UpdateLimitList=ChipUpdateLimit,
                         InitMemIDList=ChipInitMemID,
                         InitMemNumList=ChipInitMemNum,
                         StateNum=ChipStateNum,
                         TravelState=ChipTravelState,
                         NextState=ChipNextState,
                         InputList=self.InputList,
                         ConnPort=self.ConnPort)