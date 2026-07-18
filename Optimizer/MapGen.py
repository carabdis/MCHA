import numpy as np
import math
from itertools import accumulate
import pandas as pd
from Optimizer.FlowGen import FindSearchPlace


def Fact(n:int):
    """
    :input n:
        The number that needs to find the factors of it
    """
    factors = set()
    for i in range(1, int(n**0.5) + 1):
        if n % i == 0:
            factors.add(i)
            factors.add(n // i)
    return sorted(list(factors))


def Translate(ChipScale, BlockScale, CoreNum, Index):
    ChipX, ChipY = ChipScale
    BlockX, BlockY = BlockScale
    ChipCoreNum = BlockX * BlockY * CoreNum
    co = int(Index % CoreNum)
    Index -= co
    Index /= CoreNum
    Blocks = Index % (math.prod(BlockScale))
    bx = int(Blocks % BlockX)
    by = int(Blocks / BlockX)
    Index -= Blocks
    Index /= (math.prod(BlockScale))
    cx = int(Index % ChipX)
    cy = int(Index / ChipX)
    return cx, cy, bx, by, co


def FindComm(Map:np.ndarray, StartPoint:tuple, Direction:tuple, Limits:tuple, Operators:tuple):
    SX, SY = StartPoint
    DX, DY = Direction
    TX, TY = SX + DX, SY + DY
    LimX, LimY = Limits
    OpX, OpY = Operators
    # while eval('TX' + OpX + 'LimX') and eval('TY' + OpY + 'LimY') and Map[TX, TY] < 0:
    #     TX += DX
    #     TY += DY
    if eval('TX' + OpX + 'LimX') and eval('TY' + OpY + 'LimY') and Map[TX, TY] >= 0:
        return Map[TX, TY]
    else:
        return None


def WorldCommMap(ChipScale:tuple, BlockScale:tuple, CoreNum:int, Coordinates:list, Type:str):
    """
    :input ChipScale:
        The number of chips (ChipX, ChipY)
    :input BlockScale:
        The number of blocks in one chip (BlockX, BlockY)
    :input CoreNum:
        The number of cores in one block
    :input Coordinates:
        The coordinates for the deployed cores
    :input Type:
        The type of the map
    """
    ChipX, ChipY = ChipScale
    BlockX, BlockY = BlockScale
    Map = np.ones((int(ChipX * BlockX * CoreNum), int(ChipY * BlockY))) * -1
    MaxX = 0
    MaxY = 0
    MinX = int(ChipX * BlockX * CoreNum)
    MinY = int(ChipY * BlockY)
    for i in range(len(Coordinates)):
        cx, cy, bx, by, co = Coordinates[i]
        X = int(cx * BlockX * CoreNum + bx * CoreNum + co)
        Y = int(cy * BlockY + by)
        Map[X, Y] = i
        MinX = min(X, MinX)
        MinY = min(Y, MinY)
        MaxX = max(X, MaxX)
        MaxY = max(Y, MaxY)
    CommTargetList = []
    for cx, cy, bx, by, co in Coordinates:
        SX, SY = int(cx * BlockX * CoreNum + bx * CoreNum + co), int(cy * BlockY + by)
        TempList = []
        # Find Right Comm
        TempList.append(FindComm(Map, (SX, SY), (1, 0), (MaxX, MaxY), ("<=", "<=")))
        # Find Left Comm
        TempList.append(FindComm(Map, (SX, SY), (-1, 0), (MinX, MaxY), (">=", "<=")))
        # Find Top Comm
        TempList.append(FindComm(Map, (SX, SY), (0, 1), (MaxX, MaxY), ("<=", "<=")))
        # Find Bottom Comm
        TempList.append(FindComm(Map, (SX, SY), (0, -1), (MaxX, MinY), ("<=", ">=")))
        if Type == 'GridWorld':
            # Find Right-top Comm
            TempList.append(FindComm(Map, (SX, SY), (1, 1), (MaxX, MaxY), ("<=", "<=")))
            # Fing Right-bottom Comm
            TempList.append(FindComm(Map, (SX, SY), (1, -1), (MaxX, MinY), ("<=", ">=")))
            # Find Left-top Comm
            TempList.append(FindComm(Map, (SX, SY), (-1, 1), (MinX, MaxY), (">=", "<=")))
            # Find Left-bottom Comm
            TempList.append(FindComm(Map, (SX, SY), (-1, -1), (MinX, MinY), (">=", ">=")))
        CommTargetList.append(TempList)
    return CommTargetList


def FlowCost(Dist:np.ndarray, BlockScale:tuple):
    """
    :input Dist:
        The Manhattan Distance of the flow
    :input BlockScale:
        The number of blocks in one chip
    """
    BlockX, BlockY = BlockScale
    Dist[:, :, 2] = np.abs(BlockX * Dist[:, :, 0] - Dist[:, :, 2])
    Dist[:, :, 3] = np.abs(BlockY * Dist[:, :, 1] - Dist[:, :, 3])
    Dist[:, :, 4] = 1
    return np.abs(Dist)

def solve_robust_routing(DeployList:list, AgentNum:int, BlockScale:tuple, weights:np.ndarray):
    A_coords = DeployList[0]
    m_counts = np.full(len(A_coords), AgentNum)
    stages_coords = [np.array(item) for item in DeployList[1:]]
    num_stages = len(stages_coords)
    bounds = [
        (np.floor(AgentNum * len(DeployList[0]) / len(DeployList[layer])),
         np.ceil(AgentNum * len(DeployList[0]) / len(DeployList[layer])))
    for layer in range(1, len(DeployList))]

    W = np.array(weights)
    
    all_flows = []
    for a_idx, m in enumerate(m_counts):
        for f_id in range(m):
            all_flows.append({'a_idx': a_idx, 'f_id': f_id, 'path': [list(A_coords[a_idx])]})
    
    total_flow_count = len(all_flows)

    for s_idx in range(num_stages):
        low_b, upp_b = bounds[s_idx]
        nodes = stages_coords[s_idx]
        num_nodes = len(nodes)
        
        node_usage = np.zeros(num_nodes)
        flow_assigned = [False] * total_flow_count
        
        for n_idx in range(num_nodes):
            required = int(low_b)
            while node_usage[n_idx] < required:
                best_f_idx = -1
                min_d = float('inf')
                
                for f_idx in range(total_flow_count):
                    if not flow_assigned[f_idx]:
                        prev_pos = np.array(all_flows[f_idx]['path'][-1])
                        diff = np.reshape(np.abs(prev_pos - nodes[n_idx]), (1, -1, 5))
                        cost = FlowCost(diff, BlockScale).reshape((-1, 5))
                        dist = np.sum(weights * cost, axis=1)
                        if dist < min_d:
                            min_d = dist
                            best_f_idx = f_idx
                
                if best_f_idx != -1:
                    all_flows[best_f_idx]['path'].append(list(nodes[n_idx]))
                    node_usage[n_idx] += 1
                    flow_assigned[best_f_idx] = True
                else:
                    break

        for f_idx in range(total_flow_count):
            if not flow_assigned[f_idx]:
                prev_pos = np.array(all_flows[f_idx]['path'][-1])
                
                best_n = -1
                min_d = float('inf')
                
                for n_idx in range(num_nodes):
                    if node_usage[n_idx] < upp_b:
                        diff = np.reshape(np.abs(prev_pos - nodes[n_idx]), (1, -1, 5))
                        cost = FlowCost(diff, BlockScale).reshape((-1, 5))
                        dist = np.sum(weights * cost, axis=1)
                        if dist < min_d:
                            min_d = dist
                            best_n = n_idx
                
                if best_n == -1:
                    best_n = np.argmin([np.sum(W * np.abs(prev_pos - n)) for n in nodes])
                
                all_flows[f_idx]['path'].append(list(nodes[best_n]))
                node_usage[best_n] += 1
                flow_assigned[f_idx] = True

    for f_idx in range(total_flow_count):
        a_idx = all_flows[f_idx]['a_idx']
        all_flows[f_idx]['path'].append(list(A_coords[a_idx]))

    results = {}
    for f in all_flows:
        results[(f['a_idx'], f['f_id'])] = f['path']
        
    return results


def MapCommDict(DestCores:list, CommPool:np.ndarray, Counts:list, SearchCycle:int, DeployList:list):
    Dest = []
    RealCommPool = np.zeros((CommPool.shape[0], 8), dtype=int)
    CommPool = np.array(CommPool, dtype=int)
    for j in range(len(DestCores)):
        if DestCores[j] is not None:
            Dest.append(DeployList[int(DestCores[j])])
            RealCommPool[:, j] += CommPool[:, j]
    Dest = list(set(Dest))
    Dist = [count / sum(Counts) for count in Counts]
    Dist = list(accumulate(Dist))
    OpList = []
    CommDest = []
    CycleCost = []
    MessLength = []
    MessType = []
    for i in range(len(RealCommPool)):
        Ops = [4] * CommPool[i][8] + [5] + [4] * sum(RealCommPool[i])
        Send = [(0, 0, 0, 0, 0)] * CommPool[i][8] + [(0, 0, 0, 0, 0)]
        Cost = [SearchCycle] * CommPool[i][8] + [0] + [str(SearchCycle)] * sum(RealCommPool[i])
        Length = [1] * CommPool[i][8] + [CommPool[i][8] + sum(RealCommPool[i]) + 1] + [1] * sum(RealCommPool[i])
        Type = [11] * CommPool[i][8] + [11]
        for j in range(len(RealCommPool[i])):
            if DestCores[j] is not None:
                Send += [DeployList[int(DestCores[j])]] * RealCommPool[i][j]
                Type += [j + 3] * RealCommPool[i][j]
        OpList.append(Ops)
        CommDest.append(Send)
        CycleCost.append(Cost)
        MessLength.append(Length)
        MessType.append(Type)
    return Dest, OpList, CommDest, CycleCost, MessLength, MessType, Dist


def SystolicRoute(group_coords, BlockScale, Weight):
    n = len(group_coords)
    if n <= 1: return list(range(n))
    
    coords = np.array(group_coords)
    
    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            diff = np.reshape(coords[i] - coords[j], (1, 1, 5))
            Cost = np.sum(Weight * FlowCost(diff, BlockScale))
            dist_matrix[i, j] = dist_matrix[j, i] = Cost

    best_route = []
    min_dist = float('inf')
    for start_node in range(n):
        unvisited = list(range(n))
        unvisited.remove(start_node)
        route = [start_node]
        curr = start_node
        while unvisited:
            next_node = min(unvisited, key=lambda x: dist_matrix[curr, x])
            unvisited.remove(next_node)
            route.append(next_node)
            curr = next_node
        
        d_total = sum(dist_matrix[route[k], route[k+1]] for k in range(n-1))
        if d_total < min_dist:
            min_dist = d_total
            best_route = route
            
    return best_route


def GetParentList(ReflectList:list, DeployList:list, AgentNum:int):
    FlowID = {}
    # UsedList = [np.zeros(len(item)) for item in DeployList]
    for i in range(len(DeployList[0])):
        for j in range(AgentNum):
            path = ReflectList[(i, j)]
            for layer in range(len(path) - 1):
                Coords = tuple(path[layer])
                Index = DeployList[layer].index(Coords)
                # UsedList[layer][Index] = 1
                if FlowID.get((layer, Index)) is None:
                    FlowID[(layer, Index)] = [(i, j)]
                else:
                    FlowID[(layer, Index)] += [(i, j)]
    # Workers = [np.sum(item) for item in UsedList]
    # print(Workers, [len(item) for item in DeployList])
    return FlowID


def SysPartition(LayerRoute:list, DeployList:list, FlowIDs:dict):
    Route = []
    PlusShake = []
    MinusShake = []
    for layer in range(len(DeployList)):
        TempRoute = [DeployList[layer][item] for item in LayerRoute[layer]]
        StartIndex = []
        RouteStr = ''
        for i in range(len(TempRoute)):
            if i != 0:
                cx, cy, bx, by, _ = TempRoute[i]
                if cx == pcx and cy == pcy:
                    RouteStr += 'c'
                    continue
                else:
                    RouteStr += ';c'
                    pcx = cx
                    pcy = cy
                    StartIndex.append(LayerRoute[layer][i])
            else:
                pcx, pcy, _, _, _ = TempRoute[i]
                StartIndex.append(LayerRoute[layer][i])
                RouteStr += 'c'
        RouteStr = RouteStr.split(';')
        RouteDirect = [list(item) for item in RouteStr]
        PassCore = 0
        Plus = np.zeros(len(TempRoute))
        Minus = np.zeros(len(TempRoute))
        PlusAcc = 0
        MinusAcc = 0
        PlusBias = len(RouteDirect[0])
        MinusBias = len(RouteDirect[-1])
        p = 1
        m = -2
        while PassCore < len(TempRoute):
            Plus[PassCore] = PlusAcc
            if FlowIDs.get((layer, LayerRoute[layer][PassCore])) is not None:
                PlusAcc = 1
            Minus[len(TempRoute) - PassCore - 1] = MinusAcc
            if FlowIDs.get((layer, LayerRoute[layer][len(TempRoute) - PassCore - 1])) is not None:
                MinusAcc = 1
            PassCore += 1
            if PassCore >= PlusBias and p < len(RouteDirect):
                PlusAcc = 0
                PlusBias += len(RouteDirect[p])
                p += 1
            if PassCore >= MinusBias and m >= -len(RouteDirect):
                MinusAcc = 0
                MinusBias += len(RouteDirect[m])
                m -= 1
        PlusShake.append(Plus)
        MinusShake.append(Minus)
        Route.append(StartIndex)
    return Route, PlusShake, MinusShake


def FindConn(TargetList:dict, FlowIDs:dict, DeployList:list, AgentNum:int):
    Connector = [[[] for _ in deploy] for deploy in DeployList]
    for layer in range(len(DeployList)):
        for ind in range(len(DeployList[layer])):
            if FlowIDs.get((layer, ind)) is None:
                pass
            else:
                TempConn = []
                for ID in FlowIDs[(layer, ind)]:
                    if layer != 0:
                        TempConn.append(tuple(TargetList[ID][layer - 1]))
                    if layer != len(DeployList) - 1:
                        TempConn.append(tuple(TargetList[ID][layer + 1]))
                TempConn = list(set(TempConn))
                Connector[layer][ind] = TempConn
    ShakeList = [[[] for _ in DeployList[i]] for i in range(len(DeployList))]
    for layer in range(len(DeployList)):
        for ind in range(len(DeployList[layer])):
            Coor = DeployList[layer][ind]
            ShakeLayer = (layer + 1) % len(DeployList)
            for nextInd in range(len(DeployList[ShakeLayer])):
                if Coor in Connector[ShakeLayer][nextInd]:
                    ShakeList[layer][ind].append(DeployList[ShakeLayer][nextInd])
    for ind in range(len(DeployList[-1])):
        Coor = DeployList[-1][ind]
        for ID in FlowIDs[(len(DeployList) - 1, ind)]:
            s, a = ID
            if DeployList[0][s] in DeployList[-2]:
                Index = DeployList[-2].index(DeployList[0][s])
                if Coor not in ShakeList[-2][Index]:
                    ShakeList[-2][Index].append(Coor)
    return ShakeList


def MapFuncDictGen(config:dict, DeployList:list, CommList:list, TargetList:dict, AvgScale:int,
                   AgentNum:int, LayerRoute:list, StoMessage:list):
    FinalDict = {}
    # Send Address to DRAM for memory loading
    FinalDict['ParaAsk'] = {
        "AddressType":[0, 0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[0, 2],          # 0: Send, 1: Store, 2: Delete, 3: Do Nothing
        "DestTuple":[(0, 0, 0, 0, "0"),
                     (0, 0, 0, 0, 0)],
        "CycleCost":[1, 1],
        "UpdateReq":[False, True],
        "Length":[1, 1],
        "OutType":["0", 0],
        "DestDist":None,
        "CycleDist":None
    }
    # Receive messages from DRAM and store
    AgentBytes = config['AgentBytes']
    FinalDict['ParaLoad'] = {
        "AddressType":[0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[1],          # 0: Send, 1: Store, 2: Delete, 3: Do Nothing
        "DestTuple":[(0, 0, 0, 0, 0)],
        "CycleCost":[1],
        "UpdateReq":[False],
        "Length":[int(AgentBytes / 4)],
        "OutType":[1],
        "DestDist":None,
        "CycleDist":None
    }
    # Phase 0, map communication process
    FinalDict['ChangTrig'] = {
        "AddressType":[0, 0, 0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[2, 2, 1],          # 0: Send, 1: Store, 2: Delete, 3: Do Nothing
        "DestTuple":[(0, 0, 0, 0, 0),
                     (0, 0, 0, 0, 0),
                     (0, 0, 0, 0, 0)],
        "CycleCost":[1, 1, 1],
        "UpdateReq":[False, False, False],
        "Length":[1, 1, 1],
        "OutType":[2, 3, 3],
        "DestDist":None,
        "CycleDist":None
    }
    FinalDict['SelfShake'] = {
        "AddressType":[0, 0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[6, 3],          # 0: Send, 1: Store, 2: Delete, 3: Do Nothing
        "DestTuple":[(0, 0, 0, 0, 0),
                     (0, 0, 0, 0, 0)],
        "CycleCost":[1, 0],
        "UpdateReq":[False, False],
        "Length":[1, 1],
        "OutType":[3, 3],
        "DestDist":None,
        "CycleDist":None
    }
    FinalDict['PhaseChange'] = {
        "AddressType":[0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[3],          # 0: Send, 1: Store, 2: Delete, 3: Do Nothing
        "DestTuple":[(0, 0, 0, 0, 0)],
        "CycleCost":[1],
        "UpdateReq":[True],
        "Length":[1],
        "OutType":[0],
        "DestDist":None,
        "CycleDist":None
    }
    FinalDict['FlowCount'] = {
        "AddressType":[0, 0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[1, 3],          # 0: Send, 1: Store, 2: Delete, 3: Do Nothing
        "DestTuple":[(0, 0, 0, 0, 0),
                     (0, 0, 0, 0, 0)],
        "CycleCost":[1, 0],
        "UpdateReq":[True, False],
        "Length":[1, 1],
        "OutType":[999, 3],
        "DestDist":None,
        "CycleDist":None
    }
    FinalDict['AddEnd'] = {
        "AddressType":[0, 0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[1, 3],          # 0: Send, 1: Store, 2: Delete, 3: Do Nothing
        "DestTuple":[(0, 0, 0, 0, 0),
                     (0, 0, 0, 0, 0)],
        "CycleCost":[1, 0],
        "UpdateReq":[True, False],
        "Length":[1, 1],
        "OutType":[999, 3],
        "DestDist":None,
        "CycleDist":None
    }
    for i in range(len(DeployList[0])):
        for j in range(AgentNum):
            FinalDict[f'RemoveElement_f{i * AgentNum + j}'] = {
                "AddressType":[0, 0],    # 0: relative address; 1: absolute address
                "DestType":0,
                "CycleType":0,
                "OpSel":[2, 3],          # 0: Send, 1: Store, 2: Delete, 3: Do Nothing
                "DestTuple":[(0, 0, 0, 0, 0),
                             (0, 0, 0, 0, 0)],
                "CycleCost":[1, 0],
                "UpdateReq":[False, False],
                "Length":[1, 1],
                "OutType":[i * AgentNum + j + 6, 
                           3],
                "DestDist":None,
                "CycleDist":None
            }
        FinalDict[f'Act_n{i}'] = {
            "AddressType":[0, 0] * AgentNum,    # 0: relative address; 1: absolute address
            "DestType":0,
            "CycleType":0,
            "OpSel":[2, 0] * AgentNum,
            "DestTuple":[(0, 0, 0, 0, 0),
                         (0, 0, 0, 0, '0')] * AgentNum,
            "CycleCost":[config['RBFactor'], 1] * AgentNum,
            "UpdateReq":[False, False] * AgentNum,
            "Length":[StoMessage[-1], 1] * AgentNum,
            "OutType":[i * AgentNum + 6, 0,
                       i * AgentNum + 7, 0,
                       i * AgentNum + 8, 0],
            "DestDist":None,
            "CycleDist":None
        }
    FlowIDs = GetParentList(TargetList, DeployList, AgentNum)
    Loader, PlusShake, MinusShake = SysPartition(LayerRoute, DeployList, FlowIDs)
    Ending = [[LayerRoute[layer][LayerRoute[layer].index(item) - 1] for item in Loader[layer]]
               for layer in range(len(DeployList))]
    RealShake = FindConn(TargetList, FlowIDs, DeployList, AgentNum)
    File = open("HandShakeDebug.txt", "w")
    for layer in range(len(RealShake)):
        for ind in range(len(RealShake[layer])):
            print(DeployList[layer][ind], RealShake[layer][ind], file=File)
    File.close()
    # Map communication possibility computation
    SearchPlace = FindSearchPlace(config['View'], config['ViewType'])
    CommPool = []
    for sx in range(AvgScale):
        for sy in range(AvgScale):
            tempcomm = np.zeros(9)
            for obs in SearchPlace:
                ox, oy = obs
                dx, dy = sx + ox, sy + oy
                if dx >= AvgScale and 0 <= dy < AvgScale:
                    tempcomm[0] += 1
                elif dx < 0 and 0 <= dy < AvgScale:
                    tempcomm[1] += 1
                elif 0 <= dx < AvgScale and dy >= AvgScale:
                    tempcomm[2] += 1
                elif 0 <= dx < AvgScale and dy < 0:
                    tempcomm[3] += 1
                elif dx >= AvgScale and dy >= AvgScale:
                    tempcomm[4] += 1
                elif dx >= AvgScale and dy < 0:
                    tempcomm[5] += 1
                elif dx < 0 and dy >= AvgScale:
                    tempcomm[6] += 1
                elif dx < 0 and dy < 0:
                    tempcomm[7] += 1
                else:
                    tempcomm[8] += 1
            CommPool.append(tempcomm)
    CommPool = np.array(CommPool)
    CommPool, Counts = np.unique(np.array(CommPool), axis=0, return_counts=True)
    SearchCost = np.ceil(np.log2(AgentNum) * config['RBFactor'])
    # Send Handshake Message
    for i in range(len(CommList)):
        cores = CommList[i]
        Dest, OpList, CommDest, CycleCost, MessLength, MessType, Dist = MapCommDict(
            DestCores=cores,
            CommPool=CommPool,
            Counts=Counts,
            SearchCycle=SearchCost,
            DeployList=DeployList[0]
        )
        FinalDict[f'ChangeSig_{i}'] = {
            "AddressType":[1] * len(Dest) + [0],    # 0: relative address; 1: absolute address
            "DestType":0,
            "CycleType":0,
            "OpSel":[0] * len(Dest) + [1],
            "DestTuple":Dest + [(0, 0, 0, 0, 0)],
            "CycleCost":[1] * len(Dest) + [1],
            "UpdateReq":[False] * len(Dest) + [True],
            "Length":[1] * len(Dest) + [1],
            "OutType":[2] * len(Dest) + [2],
            "DestDist":None,
            "CycleDist":None
        }
        Next = []
        for agent in range(AgentNum):
            if TargetList.get((i, agent)) is not None and len(TargetList[(i, agent)]) > 1:
                Next.append(tuple(TargetList[(i, agent)][1]))
        Next = list(set(Next))
        # FinalDict[f'ShakeS_l0_comm_{i}'] = {
        #     "AddressType":[1] * len(Next) + [1] * len(Dest),    # 0: relative address; 1: absolute address
        #     "DestType":0,
        #     "CycleType":0,
        #     "OpSel":[0] * len(Next) + [0] * len(Dest),
        #     "DestTuple":Next + Dest,
        #     "CycleCost":[1] * len(Next) + [1] * len(Dest),
        #     "UpdateReq":[False] * (len(Next) + len(Dest) - 1) + [True],
        #     "Length":[1] * len(Next) + [1] * len(Dest),
        #     "OutType":[2] * len(Next) + [2] * len(Dest),
        #     "DestDist":None,
        #     "CycleDist":None
        # }
        FinalDict[f'Jump_n{i}'] = {
            "AddressType":[1] * len(RealShake[0][i]),    # 0: relative address; 1: absolute address
            "DestType":0,
            "CycleType":0,
            "OpSel":[0] * len(RealShake[0][i]),          # 0: Send, 1: Store, 2: Delete, 3: Do Nothing
            "DestTuple":RealShake[0][i],
            "CycleCost":[1] * len(RealShake[0][i]),
            "UpdateReq":[False] * (len(RealShake[0][i]) - 1) + [True],
            "Length":[1] * len(RealShake[0][i]),
            "OutType":[2] * len(RealShake[0][i]),
            "DestDist":None,
            "CycleDist":None
        }
        if len(Dest) > 0:
            FinalDict[f'ShakeS_l0_comm_{i}'] = {
                "AddressType":[1] * len(Dest) + [0],    # 0: relative address; 1: absolute address
                "DestType":0,
                "CycleType":0,
                "OpSel":[0] * len(Dest) + [5],
                "DestTuple":Dest + [(0, 0, 0, 0, 0)],
                "CycleCost":[1] * len(Dest) + [0],
                "UpdateReq":[False] * len(Dest) + [True],
                "Length":[1] * len(Dest) + [-AgentNum],
                "OutType":[2] * len(Dest) + [11],
                "DestDist":None,
                "CycleDist":None
            }
        else:
            FinalDict[f'ShakeS_l0_comm_{i}'] =  {
                "AddressType":[0],    # 0: relative address; 1: absolute address
                "DestType":0,
                "CycleType":0,
                "OpSel":[5],
                "DestTuple":[(0, 0, 0, 0, 0)],
                "CycleCost":[0],
                "UpdateReq":[True],
                "Length":[-AgentNum],
                "OutType":[11],
                "DestDist":None,
                "CycleDist":None
            }
        FinalDict[f'Comm{i}'] = {
            "AddressType":[[1 for _ in destList] for destList in CommDest],    # 0: relative address; 1: absolute address
            "DestType":1,
            "CycleType":1,
            "OpSel":OpList,
            "DestTuple":CommDest,
            "CycleCost":CycleCost,
            "UpdateReq":[[False] * len(OpList[i]) for i in range(len(OpList))],
            "Length":MessLength,
            "OutType":MessType,
            "DestDist":Dist,
            "CycleDist":Dist
        }
        # Return Message Dict
        ReDirect = [1, 0, 3, 2, 7, 6, 5, 4]
        for direct in range(8):
            if CommList[i][ReDirect[direct]] is not None:
                FinalDict[f'Return{i}_d{ReDirect[direct]}'] = {
                    "AddressType":[1],    # 0: relative address; 1: absolute address
                    "DestType":0,
                    "CycleType":0,
                    "OpSel":[0],
                    "DestTuple":[DeployList[0][int(CommList[i][ReDirect[direct]])]],
                    "CycleCost":[SearchCost],
                    "UpdateReq":[False],
                    "Length":[1],
                    "OutType":[11],
                    "DestDist":None,
                    "CycleDist":None
                }
        NextDest = [[tuple(TargetList[(i, j)][1])] + [(0, 0, 0, 0, 0)] for j in range(AgentNum)]
        FinalDict[f'AcceptReturn_l0_n{i}'] = {
            "AddressType":[[1 for _ in destKind] + [0] for destKind in NextDest],    # 0: relative address; 1: absolute address
            "DestType":2,
            "CycleType":3,
            "OpSel":[[[0, 6],
                      [3, 6]] for j in range(AgentNum)],
            "DestTuple":NextDest,
            "CycleCost":[[[1, 1],
                          [1, 1]] for j in range(AgentNum)],
            "UpdateReq":[[[False, False],
                          [False, False]] for j in range(AgentNum)],
            "Length":[[[1, 1],
                       [1, 1]] for j in range(AgentNum)],
            "OutType":[[[i * AgentNum + j + 6, 11],
                        [3, 11]] for j in range(AgentNum)],
            "DestDist":None,
            "CycleDist":[[config['Density'], 1] for _ in range(AgentNum)]
        }
    # Phase others, flow processing
    for i in range(len(DeployList[0])):
        for j in range(AgentNum):
            FinalDict[f'IniFlow_f{i}_a{j}'] = {
                "AddressType":[0],    # 0: relative address; 1: absolute address
                "DestType":0,
                "CycleType":0,
                "OpSel":[1],
                "DestTuple":[(0, 0, 0, 0, 0)],
                "CycleCost":[1],
                "UpdateReq":[False],
                "Length":[1],
                "OutType":[i * AgentNum + j + 6],
                "DestDist":None,
                "CycleDist":None
            }
            FinalDict[f'StoFlow_f{i * AgentNum + j}'] = {
                "AddressType":[0],    # 0: relative address; 1: absolute address
                "DestType":0,
                "CycleType":0,
                "OpSel":[2],
                "DestTuple":[(0, 0, 0, 0, 0)],
                "CycleCost":[1],
                "UpdateReq":[False],
                "Length":[1],
                "OutType":[i * AgentNum + j + 6],
                "DestDist":None,
                "CycleDist":None
            }
    for i in range(len(DeployList)):
        StartPoints = DeployList[i]
        SysRoute = LayerRoute[i]
        for j in range(len(StartPoints)):
            SysPlace = SysRoute.index(j)
            if i != 0 and (MinusShake[i][SysPlace] > 0 or FlowIDs.get((i, j)) is not None) and j not in Loader[i]:
                FinalDict[f'MinusTrans_l{i}_n{j}'] = {
                    "AddressType":[1, 0],    # 0: relative address; 1: absolute address
                    "DestType":0,
                    "CycleType":0,
                    "OpSel":[0, 6],
                    "DestTuple":[DeployList[i][SysRoute[(SysPlace - 1)%len(SysRoute)]],
                                 (0, 0, 0, 0, 0)],
                    "CycleCost":[1, 1],
                    "UpdateReq":[False, False],
                    "Length":[1, 1],
                    "OutType":[5, 2],
                    "DestDist":None,
                    "CycleDist":None
                }
            elif i != 0 and (MinusShake[i][SysPlace] > 0 or FlowIDs.get((i, j)) is not None):
                FinalDict[f'MinusTrans_l{i}_n{j}'] = {
                    "AddressType":[0],    # 0: relative address; 1: absolute address
                    "DestType":0,
                    "CycleType":0,
                    "OpSel":[6],
                    "DestTuple":[(0, 0, 0, 0, 0)],
                    "CycleCost":[1],
                    "UpdateReq":[False],
                    "Length":[1],
                    "OutType":[2],
                    "DestDist":None,
                    "CycleDist":None
                }
            if i != 0 and (PlusShake[i][SysPlace] > 0 or FlowIDs.get((i, j)) is not None) and j not in Ending[i]:
                FinalDict[f'PlusTrans_l{i}_n{j}'] = {
                    "AddressType":[1, 0],    # 0: relative address; 1: absolute address
                    "DestType":0,
                    "CycleType":0,
                    "OpSel":[0, 6],
                    "DestTuple":[DeployList[i][SysRoute[(SysPlace + 1)%len(SysRoute)]],
                                 (0, 0, 0, 0, 0)],
                    "CycleCost":[1, 1],
                    "UpdateReq":[False, False],
                    "Length":[1, 1],
                    "OutType":[4, 2],
                    "DestDist":None,
                    "CycleDist":None
                }
            elif i != 0 and (PlusShake[i][SysPlace] > 0 or FlowIDs.get((i, j)) is not None):
                FinalDict[f'PlusTrans_l{i}_n{j}'] = {
                    "AddressType":[0],    # 0: relative address; 1: absolute address
                    "DestType":0,
                    "CycleType":0,
                    "OpSel":[6],
                    "DestTuple":[(0, 0, 0, 0, 0)],
                    "CycleCost":[1],
                    "UpdateReq":[False],
                    "Length":[1],
                    "OutType":[2],
                    "DestDist":None,
                    "CycleDist":None
                }
            if i != 0:
                FinalDict[f'RemoveElement_l{i}_n{j}_f{999}'] = {
                    "AddressType":[0] + [1] * len(RealShake[i][j]),    # 0: relative address; 1: absolute address
                    "DestType":0,
                    "CycleType":0,
                    "OpSel":[2] + [0] * len(RealShake[i][j]),          # 0: Send, 1: Store, 2: Delete, 3: Do Nothing
                    "DestTuple":[(0, 0, 0, 0, 0)] + RealShake[i][j],
                    "CycleCost":[1] * (len(RealShake[i][j]) + 1),
                    "UpdateReq":[False] * len(RealShake[i][j]) + [True],
                    "Length":[1] * (len(RealShake[i][j]) + 1),
                    "OutType":[999] + [2] * len(RealShake[i][j]),
                    "DestDist":None,
                    "CycleDist":None
                }
            if FlowIDs.get((i, j)) is None and i != 0 and j not in Ending[i]:
                FinalDict[f'InitMac_l{i}_n{j}'] = {
                    "AddressType":[1] * 2,    # 0: relative address; 1: absolute address
                    "DestType":0,
                    "CycleType":0,
                    "OpSel":[0] + [6],
                    "DestTuple":[DeployList[i][SysRoute[(SysPlace + 1)%len(SysRoute)]]] + [(0, 0, 0, 0, 0)],
                    "CycleCost":[1] + [0],
                    "UpdateReq":[False] + [True],
                    "Length":[1] + [1],
                    "OutType":[0] + [3],
                    "DestDist":None,
                    "CycleDist":None
                }
                continue
            elif FlowIDs.get((i, j)) is None and i != 0:
                FinalDict[f'InitMac_l{i}_n{j}'] = {
                    "AddressType":[1],    # 0: relative address; 1: absolute address
                    "DestType":0,
                    "CycleType":0,
                    "OpSel":[6],
                    "DestTuple":[(0, 0, 0, 0, 0)],
                    "CycleCost":[0],
                    "UpdateReq":[True],
                    "Length":[1],
                    "OutType":[3],
                    "DestDist":None,
                    "CycleDist":None
                }
                continue
            elif FlowIDs.get((i, j)) is None:
                continue
            PresentFlowIDs = FlowIDs[(i, j)]
            FlowType = [s * AgentNum + a + 6 for (s, a) in PresentFlowIDs]
            if i != 0:
                if j not in Ending[i]:
                    FinalDict[f'InitMac_l{i}_n{j}'] = {
                        "AddressType":[1] + [0] * int(2 * len(PresentFlowIDs) + 1),    # 0: relative address; 1: absolute address
                        "DestType":0,
                        "CycleType":0,
                        "OpSel":[0] + [1] * len(PresentFlowIDs) + [5] * len(PresentFlowIDs) + [6],
                        "DestTuple":[DeployList[i][SysRoute[(SysPlace + 1)%len(SysRoute)]]] + 
                                    [(0, 0, 0, 0, 0)] * int(2 * len(PresentFlowIDs)) + [(0, 0, 0, 0, 0)],
                        "CycleCost":[1] + [0] * int(2 * len(PresentFlowIDs)) + [6],
                        "UpdateReq":[False] + [False] * int(2 * len(PresentFlowIDs)) + [True],
                        "Length":[1] + [0] * len(PresentFlowIDs) + [1] * len(PresentFlowIDs) + [1],
                        "OutType":[0] + FlowType + FlowType + [max(FlowType) + 1],
                        "DestDist":None,
                        "CycleDist":None
                    }
                else:
                    FinalDict[f'InitMac_l{i}_n{j}'] = {
                        "AddressType":[0] * int(2 * len(PresentFlowIDs) + 1),    # 0: relative address; 1: absolute address
                        "DestType":0,
                        "CycleType":0,
                        "OpSel":[1] * len(PresentFlowIDs) + [5] * len(PresentFlowIDs) + [6],
                        "DestTuple":[(0, 0, 0, 0, 0)] * int(2 * len(PresentFlowIDs)) + [(0, 0, 0, 0, 0)],
                        "CycleCost":[0] * int(2 * len(PresentFlowIDs)) + [0],
                        "UpdateReq":[False] * int(2 * len(PresentFlowIDs)) + [True],
                        "Length":[0] * len(PresentFlowIDs) + [1] * len(PresentFlowIDs) + [1],
                        "OutType":FlowType + FlowType + [max(FlowType) + 1],
                        "DestDist":None,
                        "CycleDist":None
                    }
            for ID in PresentFlowIDs:
                DestIndex = tuple(TargetList[ID][i + 1])
                FT = int(ID[0] * AgentNum + ID[1])
                if i != 0:
                    FinalDict[f'FollowMac_l{i}_n{j}_f{FT}'] = {
                        "AddressType":[1] * StoMessage[i],    # 0: relative address; 1: absolute address
                        "DestType":0,
                        "CycleType":0,
                        "OpSel":[0] * StoMessage[i],
                        "DestTuple":[DestIndex] * StoMessage[i],
                        "CycleCost":[1] * StoMessage[i],
                        "UpdateReq":[False] * (StoMessage[i] - 1) + [True],
                        "Length":[1] * StoMessage[i],
                        "OutType":[FT + 6] * StoMessage[i],
                        "DestDist":None,
                        "CycleDist":None
                    }
    FinalDict['ShakeR'] = {
        "AddressType":[0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[6],
        "DestTuple":[(0, 0, 0, 0, 0)],
        "CycleCost":[1],
        "UpdateReq":[True],
        "Length":[1],
        "OutType":[2],
        "DestDist":None,
        "CycleDist":None
    }
    FinalDict['ShakeN'] = {
        "AddressType":[0, 0, 0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[6, 6, 6],
        "DestTuple":[(0, 0, 0, 0, 0),
                     (0, 0, 0, 0, 0),
                     (0, 0, 0, 0, 0)],
        "CycleCost":[1, 1, 1],
        "UpdateReq":[True, False, False],
        "Length":[1, 1, 1],
        "OutType":[2, 4, 5],
        "DestDist":None,
        "CycleDist":None
    }
    FinalDict['ShakeP'] = {
        "AddressType":[0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[6],
        "DestTuple":[(0, 0, 0, 0, 0)],
        "CycleCost":[1],
        "UpdateReq":[False],
        "Length":[1],
        "OutType":[4],
        "DestDist":None,
        "CycleDist":None
    }
    FinalDict['ShakeM'] = {
        "AddressType":[0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[6],
        "DestTuple":[(0, 0, 0, 0, 0)],
        "CycleCost":[1],
        "UpdateReq":[False],
        "Length":[1],
        "OutType":[5],
        "DestDist":None,
        "CycleDist":None
    }
    FinalDict['Clean'] = {
        "AddressType":[0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[3],
        "DestTuple":[(0, 0, 0, 0, 0)],
        "CycleCost":[1],
        "UpdateReq":[False],
        "Length":[1],
        "OutType":[4],
        "DestDist":None,
        "CycleDist":None
    }
    FinalDict['RecvData'] = {
        "AddressType":[0],    # 0: relative address; 1: absolute address
        "DestType":0,
        "CycleType":0,
        "OpSel":[6],
        "DestTuple":[(0, 0, 0, 0, 0)],
        "CycleCost":[1],
        "UpdateReq":[False],
        "Length":[1],
        "OutType":[2],
        "DestDist":None,
        "CycleDist":None
    }
    return FinalDict


def main():
    return


if __name__ == "__main__":
    main()