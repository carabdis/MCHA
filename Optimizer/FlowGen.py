import matplotlib.pyplot as plt
import numpy as np
from thop import profile
import torch.nn as nn
import torch
import math


def FindSearchPlace(View:tuple, ViewType:str):
    """
    :input View
        The parameter of the observation view
    :input ViewType
        The shape of the observation view, can be
        's'--- square type, the observation size is a square whose
               edge length is View (View x View)
        '+'--- Cross type, the observation size is a cross whose
               largest reaching distance is View
        'p'--- pyramid-like cross, the total number of the observed
               points defined as View * (View + 1)
    """
    if ViewType == 's':
        # View is tuple
        vx, vy = View
        SearchPlace = [(i - np.floor(vx / 2), j - np.floor(vy / 2)) for i in range(vx) for j in range(vy)]
    elif ViewType == '+':
        # View is int
        View = int(View[0])
        SearchPlace = [(i, 0) for i in range(View)] + [(0, i) for i in range(1, View)] + \
                      [(-i, 0) for i in range(1, View)] + [(0, -i) for i in range(1, View)]
    else:
        View = int(View[0])
        SearchPlace = [(0, i) for i in range(1, View)] + [(0, -i) for i in range(1, View)] + \
                      [(i, j) for i in range(1, View) for j in range(i - View + 1, View - i)] + \
                      [(-i, j) for i in range(1, View) for j in range(i - View + 1, View - i)]
    return SearchPlace


def GridWorld(Scale:tuple, Density:float, View:tuple, ViewType:str,
              RBFactor:int, CommEN:bool=False, RandTimes:int=10,):
    """
    Generate the processing speed of grid world target search, based on
    the density of the agents and the scale of the core.
    This function is a tool for data or map partition in the specific
    problem.
    :input Scale
        The size of the grid world
    :input Density
        The density of the agents in this gridworld, determine the
        number of agents simulated in this function
    :input View
        The parameter of the observation view
    :input ViewType
        The shape of the observation view, can be
        's'--- square type, the observation size is a square whose
               edge length is View (View x View)
        '+'--- Cross type, the observation size is a cross whose
               largest reaching distance is View
        'p'--- pyramid-like cross, the total number of the observed
               points defined as View * (View + 1)
    :input RBFactor
        The parameter define the RB-Tree searching and repairing cycles
    :input CommEN
        Define whether this environment need to communicate with others
    :input RandTimes
        Simulation times for average cost computation
    """
    ScaleX, ScaleY = Scale
    AverageComm = []
    AverageProc = []
    AverageBatch = []
    AgentNum = int(np.floor(ScaleX * ScaleY * Density))
    SearchCost = np.log2(AgentNum) * RBFactor
    SearchPlace = FindSearchPlace(View, ViewType)
    for _ in range(RandTimes):
        TotalSearchCost = 0
        TotalSendNum = 0
        TotalBatchSize = 0
        AgentX = np.random.randint(ScaleX, size=AgentNum)
        AgentY = np.random.randint(ScaleY, size=AgentNum)
        for i in range(AgentNum):
            for Address in SearchPlace:
                vx, vy = Address
                x = AgentX[i] + vx
                y = AgentY[i] + vy
                TotalSearchCost += 2
                if x < 0 or x >= ScaleX or y < 0 or y >= ScaleY:
                    if CommEN:
                        TotalSearchCost += 1
                        TotalSendNum += 1
                        x %= ScaleX
                        y %= ScaleY
                        TotalSearchCost += SearchCost
                        if x in AgentX and y in AgentY:
                            TotalSendNum += 1
                            TotalBatchSize += 1
                    continue
                TotalSearchCost += SearchCost
                if x in AgentX and y in AgentY:
                    TotalSendNum += 1
                    TotalBatchSize += 1
        AverageProc.append(TotalSearchCost)
        AverageBatch.append(TotalBatchSize)
        if CommEN:
            AverageComm.append(TotalSendNum)
    return np.average(AverageProc), np.average(AverageComm), np.average(AverageBatch), AgentNum


def MapWorld(NodeNum:int, ConnDegree:tuple, TransDirectNum:int, SearchFactor:int,
             CommEN:bool=False, RandTimes:int=100):
    """
    :input NodeNum:
        Number of nodes exists in the map
    :input ConnDegree:
        Number of connection degrees of the nodes
        ConnDegree = (Minimum Degree, Maximum Degree)
    :input TransDirectNum:
        Number of Edges that connects with other blocks
    :input SearchFactor:
        Indicating the factor that the RB-Tree Edge search requires
    :input CommEN:
        Whether communication between different processors is required
    :input RandTime:
        Simulation times for average performance
    """
    ConnL, ConnH = ConnDegree
    AverageSearchCost = []
    AverageCommCost = []
    AverageSendBatch = []
    for _ in range(RandTimes):
        TotalSearchCost = 0
        TotalCommCost = 0
        TotatlSendBatch = 0
        NodeList = np.random.randint(ConnL, ConnH, size=NodeNum)
        AdjM = np.zeros((NodeNum, NodeNum + TransDirectNum))
        for i in range(NodeList):
            PossConns = np.where(AdjM[i, :] == 0)[0]
            ExistEdgeNum = NodeNum + TransDirectNum - len(PossConns)
            if ExistEdgeNum < NodeList[i]:
                np.random.shuffle(PossConns)
                AddEdgeNum = NodeList[i] - ExistEdgeNum
                ExtraEdge = min(AddEdgeNum - len(PossConns), 0)
                for j in range(AddEdgeNum - ExtraEdge):
                    if PossConns[j] >= NodeNum:
                        AdjM[i, j] += 1
                    else:
                        AdjM[i, j] = 1
                        AdjM[j, i] = 1
                if ExtraEdge > 0:
                    target = np.random.randint(TransDirectNum, size=ExtraEdge)
                    for index in target:
                        AdjM[i, index] += 1
        TotatlSendBatch = np.sum(NodeList)
        TotalSearchCost = NodeNum * np.log2(np.sum(AdjM)) * SearchFactor
        if CommEN:
            TotalCommCost += np.sum(AdjM[:, NodeNum:])
            TotalSearchCost += np.sum(AdjM[:, NodeNum:]) * SearchFactor
            AverageCommCost.append(TotalCommCost)
        AverageSendBatch.append(TotatlSendBatch)
        AverageSearchCost.append(TotalSearchCost)
    return np.average(AverageSearchCost), np.average(AverageCommCost), np.average(AverageSendBatch), NodeNum


def NNLayer(InputFeature:tuple, Layer:nn.Module, DRAMLatency:int, BatchSize:int):
    """
    :input InputFeature:
        The size of the input of the Layer
    :input Layer:
        The neural network layer
    :input DRAMLatency:
        The latency cycle of the DRAM access for weight loading
    :input BatchSize:
        The size of the input batch
    :input SparsityRatio:
        The density of the parameter in the layer that requires computation
    """
    NewSize = tuple([BatchSize] + list(InputFeature))
    FakeIn = torch.randn(NewSize)
    macs, _ = profile(Layer, inputs=(FakeIn, ))
    MemoryReq = Layer.weight.numel()
    if Layer.bias is not None:
        MemoryReq += Layer.bias.numel()
    TotalCycleCost = np.ceil(MemoryReq / 2) + DRAMLatency + np.ceil(macs)
    Output = Layer(FakeIn)
    OutputNum = Output.numel()
    SendMessage = math.prod(InputFeature) * OutputNum
    OutFeature = list(Output.size())[1:]
    return TotalCycleCost, SendMessage, OutputNum, MemoryReq, OutFeature


def NNPartition(IntBandWidth:float, BatchSize:int, InputFeature:tuple, DRAMLatency:int,
                Model:nn.Module, MemorySize:int, ClockCycle:int):
    """
    :input IntBandWidth:
        The bandwidth in one chip between different cores
    :input BatchSize:
        The size of the batch
    :input InputFeature:
        The shape of the input messages of the neural netowrk
    :input DRAMLatency:
        The latency of the DRAM data access
    :input Model:
        The neural network model for decision making
    :input MemorySize:
        The size of the core memory ( # of packages, 32 bits per package )
    :input ClockCycle:
        The digital clock period of the system (ns)
    """
    # Neural Network Input Stationary Computation
    LayerNum = len([m for m in Model.children()])
    # Translate bandwidth unit to bytes / cycle
    IntBandWidth = IntBandWidth * ClockCycle * 1e-3 / 8
    CoreRatio = np.ones(LayerNum)
    TimeSeries = []
    MessageSeries = []
    StoSeries = []
    CommSeries = []
    for i, layer in enumerate(Model.children()):
        CompTime, LayerMessage, StoMessage, LayerPara, OutFeature = NNLayer(InputFeature, layer, DRAMLatency, BatchSize)
        if i != 0:
            BatchAcceptMessages = PreviousMessage + LayerPara
            MinBatchSendCost = np.ceil((BatchAcceptMessages + LayerMessage) / IntBandWidth) + CompTime
            MaxBatchFlow = LayerMessage / MinBatchSendCost
            BatchCore = CoreRatio[i]
            InitCore = CoreRatio[i - 1]
            FlowRatio = math.prod(OutFeature) / math.prod(InputFeature)
            if PreviousSto > MemorySize * BatchCore:
                BatchCore = np.ceil(PreviousSto / MemorySize)
                CoreRatio[i] = BatchCore
            if MaxBatchFlow * BatchCore > PreviousSendFlow * InitCore * FlowRatio:
                Target = np.floor(MaxBatchFlow * BatchCore / (PreviousSendFlow  * FlowRatio))
                CoreRatio[:i] = np.ceil(CoreRatio[:i] * Target / InitCore)
                InitCore = Target
            elif MaxBatchFlow * BatchCore < PreviousSendFlow * InitCore  * FlowRatio:
                BatchCore = np.ceil(PreviousSendFlow * InitCore * FlowRatio / MaxBatchFlow)
                CoreRatio[i] = BatchCore
        else:
            BatchAcceptMessages = LayerPara + math.prod(InputFeature) * BatchSize
            MinBatchSendCost = np.ceil((BatchAcceptMessages + LayerMessage) / IntBandWidth) + CompTime
            MaxBatchFlow = LayerMessage / MinBatchSendCost
            NormRatio = math.prod(OutFeature) / math.prod(InputFeature)
        InputFeature = tuple(OutFeature)
        PreviousMessage = LayerMessage
        PreviousSto = StoMessage
        PreviousSendFlow = MaxBatchFlow
        TimeSeries.append(MinBatchSendCost)
        MessageSeries.append(LayerMessage)
        StoSeries.append(StoMessage)
        CommSeries.append(LayerPara)
    return CoreRatio, TimeSeries, MessageSeries, StoSeries, CommSeries, NormRatio


def main():
    ClockCycle = 5 # ns
    CoreBandWidth = 32 / ClockCycle * 1e3 # Mbps
    BlockBandWidth = 32 / (2 * ClockCycle) * 1e3 # Mbps
    ChipBandWidth = 32 / (4 * ClockCycle) * 1e3 # Mbps
    DRAMBandWidth = 256 # Mbps
    # NNLayer((4,), nn.Linear(4, 7, True), 36, 10)
    return


if __name__ == "__main__":
    main()