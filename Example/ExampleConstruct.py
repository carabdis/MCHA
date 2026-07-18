import pickle
import numpy as np
import torch
from torch import nn
import math
import matplotlib.pyplot as plt
import pickle
from Simulator.config_generator import *
from Optimizer.FlowGen import GridWorld
from Optimizer.Genetic import Genetic
from Optimizer.MapGen import *
from Example.SpecDef import Dict2Gen


class ActionModel(nn.Module):
    def __init__(self, ObsDim, ActDim):
        super().__init__()
        self.layer1 = nn.Linear(ObsDim, 64, bias=False)
        self.layer2 = nn.Linear(64, 64, bias=False)
        self.layer3 = nn.Linear(64, ActDim, bias=False)
    
    def forward(self, x):
        x = self.layer1(x)
        x = nn.functional.relu(x)
        x = self.layer2(x)
        x = nn.functional.relu(x)
        x = self.layer3(x)
        x = nn.functional.relu(x)
        return x


def Example():
    ChipScale = (2, 2)
    BlockScale = (2, 2)
    CoreNum = 4
    ExtTransBit = 8
    IntTransBit = 32
    FFTransBit = 32
    DRAMParaNum = 64
    DRAMTransBit = 32
    ClockCycle = 5 # ns
    ExtBandWidth = ExtTransBit / (ClockCycle * 2 * 1e-3) # Mbps
    IntBandWidth = IntTransBit / (ClockCycle * 2 * 1e-3) # Mbps
    FFBandWidth = FFTransBit / (ClockCycle * 1e-3) # Mbps
    DRAMBandWidth = (DRAMParaNum * DRAMTransBit) / (ClockCycle * 1e-3 * 2) # Mbps
    DRAMLatency = 36 # Cycles
    BatchSize = 64
    MemorySize = 256
    InputFeature = (136,)
    ExampleModel = ActionModel(ObsDim=InputFeature[0], ActDim=10)
    config = {
        'Scale':(16, 16),
        'AgentBytes':4,
        'Density':0.3,
        'View':(8,),
        'ViewType':'p',
        'RBFactor':10,
        'CommEN':True,
        'RandTimes':10
    }
    SmallCoreRatio, SmallTimePara, IdealCoreRatio, IdealTimePara, Repeat, DRAMReloadTime, StoMessage = Genetic(
        ChipScale=ChipScale,
        BlockScale=BlockScale,
        CoreNum=CoreNum,
        IntBandWidth=IntBandWidth,
        BatchSize=BatchSize,
        DRAMBandWidth=DRAMBandWidth,
        DRAMLatency=DRAMLatency,
        Model=ExampleModel,
        Type='GridWorld',
        config=config,
        MemorySize=MemorySize,
        InputFeature=InputFeature,
        ClockCycle=ClockCycle
    )
    print("Target Cores for each pipeline layer", SmallCoreRatio)
    TotalBatchNum = np.ceil(math.prod(config['Scale']) * config['Density'])
    AgentNum = int(np.ceil(min(TotalBatchNum, BatchSize) / SmallCoreRatio[0]))
    # print(AgentNum)
    TotalCores = math.prod(BlockScale) * math.prod(ChipScale) * CoreNum
    AvailList = [i for i in range(TotalCores)]
    DeployList = []
    SmallCoreRatio = SmallCoreRatio.astype(int)
    FreePointer = 0
    for i in range(len(SmallCoreRatio)):
        np.random.shuffle(AvailList)
        DeployList.append(AvailList[:SmallCoreRatio[i]])
        AvailList = [item for item in AvailList if item not in DeployList[i]]
        while i != len(SmallCoreRatio) - 1 and len(AvailList) < SmallCoreRatio[i + 1]:
            AvailList += DeployList[FreePointer]
            FreePointer += 1
    # DeployList = [AvailList[:SmallCoreRatio[0]], AvailList[SmallCoreRatio[0]:]]
    DeployList = [[Translate(ChipScale, BlockScale, CoreNum, Index) for Index in Layer]
                  for Layer in DeployList]
    for layer in DeployList:
        layer.sort()
    Weight = np.array([ExtBandWidth, ExtBandWidth, IntBandWidth, IntBandWidth, FFBandWidth])
    MapComm = WorldCommMap(ChipScale, BlockScale, CoreNum, DeployList[0], Type='GridWorld')
    TargetList = solve_robust_routing(DeployList, AgentNum, BlockScale, Weight)
    LayerRoute = []
    for deploy in DeployList:
        LayerRoute.append(SystolicRoute(deploy, BlockScale, Weight))
    AvgScale = int(np.ceil(config['Scale'][0] / np.sqrt(SmallCoreRatio[0])))
    StoMessage = (np.array(StoMessage) / BatchSize).astype(int)
    StoMessage[0] = InputFeature[0]
    StoMessage = (StoMessage / 4).astype(int)
    # draw_compact_mesh(DeployList, ChipScale, BlockScale, CoreNum)
    # print(SmallCoreRatio, SmallTimePara, IdealCoreRatio, IdealTimePara, Repeat, DRAMReloadTime)
    FuncDict = MapFuncDictGen(config, DeployList, MapComm, TargetList, AvgScale, AgentNum, LayerRoute, StoMessage)
    Generator = Dict2Gen(FuncDict, ChipScale, BlockScale, CoreNum, AgentNum,
                         StoMessage, DeployList, TargetList, LayerRoute, MapComm)
    with open('Test.pkl', 'wb') as f:
        pickle.dump(Generator, f)
    Test = Generator.GenerateSim()
    Test.StepSim()
    return