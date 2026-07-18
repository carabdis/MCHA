import pickle
from Simulator.config_generator import SimGenerator
import argparse
from Example.ExampleConstruct import Example
import matplotlib.pyplot as plt
from pathlib import Path
import json
import numpy as np


def IntensityPlot(Folder):
    folder_path = Path(Folder)
    IntenseDict = {}
    TimeStep = []
    for file_path in folder_path.glob("*.json"):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            data = {name:np.array(data[name]) for name in data}
        for name in data:
            if IntenseDict.get(name) is None:
                IntenseDict[name] = [data[name]]
            else:
                IntenseDict[name].append(data[name])
        TimeStep.append(float(str(file_path).replace('.json', '').replace(Folder + '/Log', '')))
    Clock = 5e-9
    TimeStep = [t * Clock for t in TimeStep]
    TimeStep.sort()
    CompCost = np.array([item.sum() for item in IntenseDict['CoreCompute']])
    DRAMCost = np.array([item[:, :, -1].sum() for item in IntenseDict['ExtChipComm']]) \
             + np.array([item[:, :, :, :, 4].sum() for item in IntenseDict['InBlockComm']]) \
             + np.array([item[:, :, :, :, 4].sum() for item in IntenseDict['InChipComm']])
    InChipCost = np.array([item[:, :, :, :4].sum() for item in IntenseDict['InChipComm']])
    ExtChipCost = np.array([item[:, :, :-1].sum() for item in IntenseDict['ExtChipComm']])
    InBlockCost = np.array([item[:, :, :, :, :4].sum() for item in IntenseDict['InBlockComm']]) + np.array([item[:, :, :, :, 5:].sum() for item in IntenseDict['InBlockComm']])
    TotalCount = CompCost.sum() + DRAMCost.sum() + InChipCost.sum() + ExtChipCost.sum() + InBlockCost.sum()
    print(CompCost.sum() / TotalCount, DRAMCost.sum() / TotalCount, InChipCost.sum() / TotalCount, ExtChipCost.sum() / TotalCount, InBlockCost.sum() / TotalCount)
    CompCost /= TotalCount * 100
    DRAMCost /= TotalCount * 100
    InChipCost /= TotalCount * 100
    ExtChipCost /= TotalCount * 100
    InBlockCost /= TotalCount * 100
    plt.figure(figsize=(12, 6))
    plt.stackplot(TimeStep, DRAMCost, CompCost, InChipCost, ExtChipCost, InBlockCost,
                  labels=['DRAM Access', 'Compute', 'In Chip Communication', 'Inter-Chip COmmunication', 'FIFO Communication'],
                  colors=['#3498db', '#e74c3c', '#f01cdc', '#a74c3c', '#e7dc3c'], alpha=0.4)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.legend()
    plt.semilogy()
    # plt.show()
    plt.savefig(Folder + "/Ratio.pdf")
    return


def main():
    parser = argparse.ArgumentParser(description="MCHA Simulator")
    # parser.add_argument("input", help="Path to the input file")
    parser.add_argument("-m", "--mode", default="e", help="The processing mode of the simulator," \
    "\"e\" for simple example presentation," \
    "\"s\" for self-defined algorithm setup," \
    "\"c\" for example construction and simulation.")
    args = parser.parse_args()
    if args.mode == 'e':
        # a packed example for small MARL implementation, constrcution process can be found in ./Example
        with open('Test.pkl', 'rb') as f:
            Generator:SimGenerator = pickle.load(f)
        Test = Generator.GenerateSim()
        Folder = Test.StepSim()
        IntensityPlot(Folder)
    elif args.mode == 'c':
        # the constructing process of the example
        Example()
        IntensityPlot(Folder)
    return


if __name__ == '__main__':
    main()