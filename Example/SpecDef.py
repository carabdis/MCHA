import numpy as np
from collections import Counter
import math
import pandas as pd
from Simulator.config_generator import SimGenerator
from Optimizer.MapGen import GetParentList, SysPartition, FindConn


class CoreConfig:
    def __init__(self):
        self.PhaseNum = 0
        self.InitFunc = []
        self.MemFunc = []
        self.ProcFunc = []
        self.UpdateLim = []
        self.MemLim = []
        self.TravelState = []
        self.InitMemID = []
        self.InitMemNum = []
        self.Description = {}
        self.InTypeDict = {}
        self.TypeInDict = {}
        self.MemTypeDict = {}
        self.TypeMemDict = {}
    
    def AddPhase(self):
        self.PhaseNum += 1
        self.InitFunc.append({})
        self.MemFunc.append({})
        self.ProcFunc.append({})
        self.UpdateLim.append({})
        self.MemLim.append({})
        return
    
    def EnableTravel(self, Phase=None):
        if Phase is None and self.PhaseNum - 1 not in self.TravelState:
            self.TravelState.append(self.PhaseNum - 1)
        else:
            self.TravelState.append(Phase)
        return
    
    def MemInit(self, Mem):
        self.InitMemID += Mem
        self.InitMemNum += [1 for _ in Mem]
        # temp = Counter(item[0] for item in Mem)
        # self.InitMemNum = [temp.get(i, 0) for i in range(max(temp))]
        return

    def AddInitFunc(self, phase, Type:int, func:str):
        self.InitFunc[phase].update({Type:func})
        return
    
    def AddProcFunc(self, phase, Type:int, func:str):
        self.ProcFunc[phase].update({Type:func})
        return
    
    def AddMemFunc(self, phase, Type:int, func:str):
        self.MemFunc[phase].update({Type:func})
        return
    
    def UpdateIn(self, Type:int, Mean:str):
        self.InTypeDict.update({Type:Mean})
        self.TypeInDict.update({Mean:Type})
        return
    
    def UpdateMem(self, Type:int, Mean:str):
        self.MemTypeDict.update({Type:Mean})
        self.TypeMemDict.update({Mean:Type})
        return
    
    def InType(self):
        return max([key for key in self.InTypeDict])
    
    def MemType(self):
        return max([key for key in self.MemTypeDict])


def Dict2Gen(FuncDict:dict, ChipScale:tuple, BLockScale:tuple, CoreNum:tuple, AgentNum:int,
             StoMessage:list, DeployList:list, ReflectList:dict, LayerRoute:list, CommList:list):
    Cores = [[[[[CoreConfig() for _ in range(CoreNum)]
             for _ in range(BLockScale[1])]
             for _ in range(BLockScale[0])]
             for _ in range(ChipScale[1])]
             for _ in range(ChipScale[0])]
    FlowIDs = GetParentList(ReflectList, DeployList, AgentNum)
    Loader, PlusShake, MinusShake = SysPartition(LayerRoute, DeployList, FlowIDs)
    Ending = [[LayerRoute[layer][LayerRoute[layer].index(item) - 1] for item in Loader[layer]]
               for layer in range(len(DeployList))]
    RealShake = FindConn(ReflectList, FlowIDs, DeployList, AgentNum)
    RecvShake = {(i, j):0 for i in range(len(RealShake)) for j in range(len(RealShake[i]))}
    for layer in range(len(RealShake) - 1):
        for ind in range(len(RealShake[layer])):
            for shakeTarget in RealShake[layer][ind]:
                if shakeTarget in DeployList[(layer + 1)%len(DeployList)]:
                    index = DeployList[(layer + 1)%len(DeployList)].index(shakeTarget)
                    RecvShake[((layer + 1)%len(DeployList), index)] += 1
    for ind in range(len(RealShake[-1])):
        for shakeTarget in RealShake[-1][ind]:
            if shakeTarget in DeployList[0]:
                index = DeployList[0].index(shakeTarget)
                RecvShake[(0, index)] += 1
    for layer in range(len(DeployList)):
        File = open(f"LayerLog_{layer}.txt", "w")
        for i in range(len(LayerRoute[layer])):
            if layer != 0:
                print(DeployList[layer][LayerRoute[layer][i]],
                      PlusShake[layer][i],
                      LayerRoute[layer][i] in Loader[layer],
                      MinusShake[layer][i],
                      LayerRoute[layer][i] in Ending[layer],
                      FlowIDs.get((layer, LayerRoute[layer][i])),
                      file=File)
            else:
                print(DeployList[layer][i], file=File)
        File.close()
    for layer in range(len(DeployList)):
        for node_index in range(len(DeployList[layer])):
            cx, cy, bx, by, co = DeployList[layer][node_index]
            target:CoreConfig = Cores[cx][cy][bx][by][co]
            if layer == 0:
                # Present Phase 0
                target.AddPhase()
                target.EnableTravel()
                target.MemInit([(0, i) for i in range(AgentNum)])
                target.Description[0] = "Send Address, Load Map / Env data to initial cores"
                target.AddInitFunc(target.PhaseNum - 1, Type=0, func='ParaAsk')
                target.AddProcFunc(target.PhaseNum - 1, Type=0, func='ParaLoad')
                target.UpdateLim[0].update({0:AgentNum})
                target.UpdateMem(0, "Address Messages")
                target.UpdateMem(1, "Map Messages")
                target.UpdateIn(0, "Map Messages")
                # Present Phase 1
                target.AddPhase()
                target.Description[1] = "Load Only"
                target.AddProcFunc(target.PhaseNum - 1, Type=0, func='ParaLoad')
                target.AddMemFunc(target.PhaseNum - 1, Type=1, func=f'ChangeSig_{node_index}')
                target.MemLim[1].update({1:AgentNum})
                target.AddProcFunc(target.PhaseNum - 1, Type=2, func='ShakeR')
                target.UpdateLim[1].update({1:1})
                target.UpdateMem(2, "Virtual Phase Change Trigger")
                target.UpdateMem(3, "Virtual End Signature")
                # Present Phase 2
                target.AddPhase()
                target.Description[3] = "Wait Neighbours"
                Neighbour = list(set([ne for ne in CommList[node_index] if ne is not None]))
                target.AddProcFunc(target.PhaseNum - 1, Type=2, func='ShakeR')
                Bias = 3
                ReDirect = [1, 0, 3, 2, 7, 6, 5, 4]
                for direct in range(8):
                    if CommList[node_index][ReDirect[direct]] is not None:
                        target.AddProcFunc(target.PhaseNum - 1, Type=direct + Bias,
                                        func=f'Return{node_index}_d{ReDirect[direct]}')
                        target.UpdateIn(direct + Bias, f'Messages from direction {direct}')
                target.MemLim[2].update({2:len(Neighbour) + 1})
                target.AddMemFunc(target.PhaseNum - 1, Type=2, func='ChangTrig')
                target.MemLim[2].update({3:1})
                target.AddMemFunc(target.PhaseNum - 1, Type=3, func='PhaseChange')
                target.UpdateLim[2].update({3:1})
                # Present Phase 3
                target.AddPhase()
                target.EnableTravel()
                target.Description[3] = "Map Message Communication"
                target.AddInitFunc(target.PhaseNum - 1, Type=1, func=f'Comm{node_index}')
                target.AddInitFunc(target.PhaseNum - 1, Type=3, func=f'ShakeS_l0_comm_{node_index}')
                Bias = 3
                ReDirect = [1, 0, 3, 2, 7, 6, 5, 4]
                for direct in range(8):
                    if CommList[node_index][ReDirect[direct]] is not None:
                        target.AddProcFunc(target.PhaseNum - 1, Type=direct + Bias,
                                        func=f'Return{node_index}_d{ReDirect[direct]}')
                        target.UpdateIn(direct + Bias, f'Messages from direction {direct}')
                target.AddProcFunc(target.PhaseNum - 1, Type=11,
                                   func=f'AcceptReturn_l0_n{node_index}')
                target.UpdateMem(11, "Accept return messages")
                target.AddMemFunc(target.PhaseNum - 1, Type=11, func='SelfShake')
                target.MemLim[3].update({2:len(Neighbour)})
                target.AddProcFunc(target.PhaseNum - 1, Type=2, func='ShakeR')
                target.AddMemFunc(target.PhaseNum - 1, Type=2, func='SelfShake')
                target.MemLim[3].update({3:3})
                target.AddMemFunc(target.PhaseNum - 1, Type=3, func=f'Jump_n{node_index}')
                target.UpdateLim[3].update({3:2})
                # End Level 1 Phase
            else:
                InitPhase = target.PhaseNum - 1
                PassFlow = 0
                # Present Phase InitPhase + 1
                target.AddPhase()
                if FlowIDs.get((layer, node_index)) is not None:
                    for flow in FlowIDs[(layer, node_index)]:
                        s, a = flow
                        FlowType = s * AgentNum + a + 6
                        target.AddProcFunc(phase=target.PhaseNum - 1, Type=FlowType,
                                        func=f'IniFlow_f{s}_a{a}')
                        target.UpdateMem(FlowType, f'Flow {s} Agent {a} Data')
                        if layer != 1:
                            target.MemLim[target.PhaseNum - 1].update({FlowType:StoMessage[layer - 1] + 1})
                            target.AddMemFunc(phase=target.PhaseNum - 1, Type=FlowType, func=f'StoFlow_f{FlowType - 6}')
                    if layer == 1:
                        PassFlow = RecvShake[(layer, node_index)]
                    else:
                        # PassFlow = len(FlowIDs[(layer, node_index)]) * StoMessage[layer - 2]
                        PassFlow = RecvShake[(layer, node_index)]
                    FlowType = [flow[0] * AgentNum + flow[1] + 6 for flow in FlowIDs[(layer, node_index)]]
                else:
                    PassFlow = 0
                    FlowType = []
                SysPlace = LayerRoute[layer].index(node_index)
                target.MemLim[target.PhaseNum - 1].update({4:PassFlow + PlusShake[layer][SysPlace]})
                target.MemLim[target.PhaseNum - 1].update({5:PassFlow + MinusShake[layer][SysPlace]})
                target.UpdateLim[target.PhaseNum - 1].update({2:PassFlow + 1})
                if PlusShake[layer][SysPlace] > 0 or FlowIDs.get((layer, node_index)) is not None:
                    target.AddMemFunc(phase=target.PhaseNum - 1, Type=4, func=f'PlusTrans_l{layer}_n{node_index}')
                else:
                    target.AddMemFunc(phase=target.PhaseNum - 1, Type=4, func=f'PhaseChange')
                    PassFlow -= 1
                if MinusShake[layer][SysPlace] > 0 or FlowIDs.get((layer, node_index)) is not None:
                    target.AddMemFunc(phase=target.PhaseNum - 1, Type=5, func=f'MinusTrans_l{layer}_n{node_index}')
                else:
                    target.AddMemFunc(phase=target.PhaseNum - 1, Type=5, func=f'PhaseChange')
                    PassFlow -= 1
                target.MemLim[target.PhaseNum - 1].update({2:PassFlow + 2})
                target.AddProcFunc(phase=target.PhaseNum - 1, Type=2, func='ShakeN')
                target.AddProcFunc(phase=target.PhaseNum - 1, Type=4, func='ShakeP')
                target.AddProcFunc(phase=target.PhaseNum - 1, Type=5, func='ShakeM')
                target.AddMemFunc(phase=target.PhaseNum - 1, Type=2, func=f'PhaseChange')
                # Present Phase InitPhase + 2
                target.AddPhase()
                if node_index in Loader[layer]:
                    target.EnableTravel()
                    target.MemInit([(0, str(int(StoMessage[layer - 1] * StoMessage[layer])))])
                    target.AddInitFunc(phase=target.PhaseNum - 1, Type=0, func='ParaAsk')
                    target.UpdateLim[target.PhaseNum - 1].update({0:1})
                    target.AddPhase()
                # Present Phase InitPhase + 3
                target.AddProcFunc(phase=target.PhaseNum - 1, Type=0,
                                   func=f'InitMac_l{layer}_n{node_index}')
                target.UpdateLim[target.PhaseNum - 1].update({0:StoMessage[layer - 1] * StoMessage[layer]})
                if len(FlowType) > 0:
                    target.MemLim[target.PhaseNum - 1].update({max(FlowType) + 1:StoMessage[layer - 1] * StoMessage[layer]})
                    target.AddMemFunc(phase=target.PhaseNum - 1, Type=max(FlowType) + 1, func='FlowCount')
                    target.UpdateLim[target.PhaseNum - 1].update({max(FlowType) + 1:1})
                    for flow in FlowType:
                        target.MemLim[target.PhaseNum - 1].update({flow:1})
                        target.AddMemFunc(phase=target.PhaseNum - 1, Type=flow,
                                        func=f'FollowMac_l{layer}_n{node_index}_f{flow - 6}')
                    target.AddPhase()
                    target.EnableTravel()
                    for flow in FlowType:
                        target.AddInitFunc(phase=target.PhaseNum - 1, Type=flow, func=f'RemoveElement_f{flow - 6}')
                    target.AddInitFunc(phase=target.PhaseNum - 1, Type=999, func=f'RemoveElement_l{layer}_n{node_index}_f{999}')
                    target.UpdateLim[target.PhaseNum - 1].update({999:1})
                else:
                    target.MemLim[target.PhaseNum - 1].update({4:StoMessage[layer]})
                    target.AddMemFunc(phase=target.PhaseNum - 1, Type=4, func='Clean')
    for node_index in range(len(DeployList[0])):
        cx, cy, bx, by, co = DeployList[0][node_index]
        target:CoreConfig = Cores[cx][cy][bx][by][co]
        # Present Phase InitPhase
        target.AddPhase()
        target.UpdateLim[target.PhaseNum - 1].update({999:999})
        for i in range(AgentNum):
            target.AddProcFunc(phase=target.PhaseNum - 1, Type=node_index * AgentNum + i + 6, func='RecvData')
            target.MemLim[target.PhaseNum - 1].update({node_index * AgentNum + i + 6:StoMessage[-1]})
            target.AddMemFunc(phase=target.PhaseNum - 1, Type=node_index * AgentNum + i + 6, func=f'RemoveElement_f{node_index * AgentNum + i}')
        target.MemLim[target.PhaseNum - 1].update({2:RecvShake[(0, node_index)]})
        target.AddMemFunc(phase=target.PhaseNum - 1, Type=2, func=f'Act_n{node_index}')
        target.AddProcFunc(phase=target.PhaseNum - 1, Type=2, func='ShakeR')
    ChipX, ChipY = ChipScale
    BlockX, BlockY = BLockScale
    InitMemID = {}
    InitMemNum = {}
    CoreFuncList = []
    CoreFuncIndex = {}
    for cx in range(ChipX):
        for cy in range(ChipY):
            for bx in range(BlockX):
                for by in range(BlockY):
                    for core in range(CoreNum):
                        InitMemID[(cx, cy, bx, by, core)] = Cores[cx][cy][bx][by][core].InitMemID
                        InitMemNum[(cx, cy, bx, by, core)] = Cores[cx][cy][bx][by][core].InitMemNum
                        CoreDef = (
                            Cores[cx][cy][bx][by][core].InitFunc,
                            Cores[cx][cy][bx][by][core].ProcFunc,
                            Cores[cx][cy][bx][by][core].MemFunc,
                            Cores[cx][cy][bx][by][core].UpdateLim,
                            Cores[cx][cy][bx][by][core].MemLim,
                            Cores[cx][cy][bx][by][core].TravelState,
                            [i + 1 for i in range(len(Cores[cx][cy][bx][by][core].InitFunc) - 1)] + 
                            [len(Cores[cx][cy][bx][by][core].InitFunc) - 1],
                        )
                        CoreFuncIndex[(cx, cy, bx, by, core)] = len(CoreFuncList)
                        CoreFuncList.append(CoreDef)
    InputList = []
    return SimGenerator(ChipX=ChipX, ChipY=ChipY, BlockX=BlockX, BlockY=BlockY, CoreNum=CoreNum,
                        MemorySize=256, ReflectList=FuncDict, CoreFuncList=CoreFuncList,
                        CoreFuncIndex=CoreFuncIndex, InitMemID=InitMemID, InitMemNum=InitMemNum,
                        InputList=InputList)


def main():
    return


if __name__ == "__main__":
    main()