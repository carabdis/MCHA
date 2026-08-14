This README file explains how the dataflow of the example is constructed.
In brief, the construction process can be divided into 3 steps.

# Parameter Definition
The first step is to define the specific parameters for the simulation.
These parameters in the main program are read from the "Parameter.json" file, which includes:

Note: `Parameter.json` is not included in the current release. The provided example currently defines these parameters directly in [`ExampleConstruct.py`](./ExampleConstruct.py).

- "ChipScale":

    The scale of chips in the MCHA system.

- "BlockScale":

    The scale of blocks in one chip of the MCHA system.

- "CoreNum":

    The number of cores in one block.

- "ExtTransBit":

    The parallel transmission bits between chips.

- "IntTransBit":

    The parallel transmission bits between blocks in MCHA chips.

- "FFTransBit":

    The parallel transmission bits of each FIFO embedded in the block.

- "DRAMParaNum":

    The parallel transmission channels for the MCHA system.

- "DRAMTransBit":

    The transmission bits of one channel for DRAM in the MCHA system.

- "ClockCycle":

    The processing clock period, whose unit is "ns".

- "Model":

    The PyTorch model describing the update function of the PSC applications and defining the required storage buffer for the update function.

- "Type":

    The string that defines the specific processing type of the simulation.

- "TargetTask":

    The dict that describes the target PSC task for this simulation.
    This dict includes the following variables, categorized as "block-like" or "graph-like".
    Details can be found in [FlowGen.py](../Optimizer/FlowGen.py).

# Dataflow Matching
As mentioned in the MCHA paper, the processing cores required by each layer should first be generated for further computation.
The detailed computing process can be found in the function [Genetic](../Optimizer/Genetic.py).

```ruby
def Genetic(ChipScale:tuple, BlockScale:tuple, CoreNum:int, DRAMBandWidth:float, Type:str,
            config:dict, IntBandWidth:float, BatchSize:int, InputFeature:tuple, DRAMLatency:int,
            Model:nn.Module, MemorySize:int, ClockCycle:int, NNSparsity:float=1):
    ...
```

# Core Allocation & Dataflow Deployment

The deployment of the cores can vary depending on the algorithmic definition.
In this example, we provide a specific example by randomly splitting the cores and selecting the shortest transmission path for each core.
Details can be found in [ExampleConstruct.py](./ExampleConstruct.py).
