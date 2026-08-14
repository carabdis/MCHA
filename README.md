
<h1 align="left">MCHA: A Memory-Centric Hierarchical Architecture for Parallel-Sequential Computing </h1>

[Introduction](#introduction) | [Simulator](#simulator) | [Example](#example) | [Quickstart](#quickstart)｜

## Introduction
MCHA is a novel reconfigurable architecture for parallel-sequential computing applications, supporting MARL, large-scale neuromorphic models, and BSP applications. It features decoupled data indexing and processing and replaces frequent off-chip data fetches with a multi-tiered on-chip NoC.
This repository provides the open-source simulator for cycle-accurate throughput estimation of our design, as well as an implementation example for algorithm deployment on an MCHA system with 4 chips.

## Simulator
The simulator of MCHA is provided in [`Simulator`](./Simulator).
To conduct a detailed simulation for a specific algorithm, the following items are required.
* System Scale:

  The scale of the system is described by a 5-dimensional tuple, which defines
  (# of chips in one row, # of chips in one column, # of blocks in one row of each chip, # of blocks in one column of each chip, # of MCCs in each block)

* Function Dict:

  Each MCC contains multiple types of functions.
  Each of these functions is described by this Function Configuration Dict, which defines the time cost and detailed operations.
  The specific definition of the dict can be found in the [simulator definition explanation file](./Simulator/README.md).

* Core Dict:

  The definition of cores should answer 3 questions: which core performs which function and when.
  This process is handled in an event-driven style, defining the detailed functions.
  The specific definition can be found in the [simulator definition explanation file](./Simulator/README.md) as well.
  


## Example
If you do not want to write the MCHA program yourself, we provide a simple example in [Example](./Example), including the original behavior description, functional definition, dataflow construction and core deployment.
Details can be found in [Example Explanation](./Example/README.md).

## Installation
Install the required packages with:
```
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
On macOS, if installing from `requirements.txt` fails, install the required packages individually:
```
python -m pip install numpy scipy pandas matplotlib thop torch
```

## Quickstart
To run the provided example and generate the compute intensity, directly run the main file provided in the repository:
```
python main.py
```
Then the corresponding compute intensity graph will be stored as Ratio.pdf in the generated [output directory](./Data/SimLog).
