
<h1 align="left">MCHA: A Memory-Centric Hierarchical Architecture for Parallel-Sequential Computing </h1>

[Introduction](#introduction) | [Simulator](#simulator) | [Example](#example) | [Quickstart](#quickstart)｜

## Introduction
MCHA is a novel reconfigurable architecture for parallel-sequential computing applications, supporting MARL, large-scale neuromorphic model and BSP applications, featuring data indexing and processing decouple, as well as replacing frequent off-chip data-fetches with multi-tiered on-chip NoC.
This repository provide the open-source simulator for cycle-accurate throughput estimation of our design, as well as an implementation example for algorithm deployment on a MCHA system with 4 chips.

## Simulator
The simultor of MCHA is provided in [`Simulator`](./Simulator).
To conduct a detailed simulation for a specific algorithm, the following items are required.
* System Scale:

  The scale of the system is described by a 5-dimensional tuple, each define 
  (# of chips in one row, # of chips in one colum, # of blocks in one row of each chip, # of blocks in one colum of each chip, # of MCCs in each block)

* Function Dict:

  Each MCCs contain multiple types of fucntions.
  Each of these functions are described by this Function Configuration Dict, defining the time cost and detailed operations.
  Specific definition of the dict can be found in the [simulator definition explanation file](./Simulator/README.md)

* Core Dict:

  The definition of cores should answer 3 questions: "which" core at "when" time doing "what" function.
  This process is handled in a event-driven style, defining the detailed functions.
  The specific definition can be found in the [simulator definition explanation file](./Simulator/README.md) as well.
  


## Example
If you do not want to write the MCHA program yourself, we provide a simple example in [Example](./Example), including the orginal behaviour description, functional definition, dataflow construction and core dployment.
Details can be found in [Example Explanation](./Example/README.md).

## Quickstart
To run the provided example and generate the compute intensity, you can directly run the main file provided in the repository
```
python main.py
```
Then the corresponding compute intensity graph will be stored as Intensity.pdf in the generated [output directory](./Data/SimLog).