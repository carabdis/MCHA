This is the README file explain how the simulator functions.

# Function Dict
The first thing to explain is the configuration of Function Dict that defines all the required function in the target algorithm.
This dict should contain the following items:

- "AddressType":

    This is a list constructed by integers of "1" and "0".
    It describes whether the elements corresponding to "DestTuple" describes the absolute coordinates ("1") or relative ones ("0") of the destination.

- "DestType":

    This is an integer describing the destination definition type of the function.
    If 0, the destination of the function is deterministic.
    If 1, the destination of the function follows the distribution defined by the "DestDist".

* "CycleType":

    Same definition logic as "DestType".

Elements of the following keys varies accroding to the definition of "DestType" and "CycleType", determining the operation type of the simulator is deterministic or probabilistic.

## Deterministic

In the determinisitic mode ("DestType" and "CycleType" are all 0), the definition are as follows.
- "DestDist" & "CycleDist":

    Not activated.

- "OpSel":

    This` is a list constructed by integers defining the specific oepration types of this function.
    The length of this list is the same as that of "AddressType".
    In detail, the operation definition is as follows:
    ```
    0: Message Send
    1: Message Storage
    2: Memory Message Delete
    3: Idle
    4: New Function Trigger
    5: Define new Memory Conditional Trigger
    6: Handshake Variable Increase
    ````
- "DestTuple":

    This is a list of 5-dimension coordinates that defines the destination of the sending messages.
    The length of this list should be the same as "OpSel" and "AddressType".
    The coordinates of the destination will be the coordinates of the sender plus corresponding value in the list, if "AddressType" with the same index is "0".

- "CycleCost":

    This is a list of integers defining how many cycles the corresponding operations required.
    The length of this list is the same as "OpSel", "AddressType" and "DestTuple".

- "UpdateReq":

    This is a list of bools defining whether this operation is connected to the Phase Change Conditional Trigger.
    If "True", the operation increment the counter correponding to the Phase Change Conditional Trigger.
    The length of this list is the same as "OpSel", "AddressType", "DestTuple", and "CycleCost".

- "Length":

    This is a list of integers defining the length of output results of corresponding operations.
    The unit of this list is "packet" defined in MCHA transmission protocol, namely 32-bits or 4 bytes.
    The length of this list is the same as "OpSel", "AddressType", "DestTuple", "CycleCost", and "UpdateReq".

- "OutType":

    This is a list of integer defining the corresponding triggering oeprations of corresponding messages.
    Elements in this list are virtual variables responsible for identifying the correct function handle at the destination of the transmission.
    The length of this list is the same as "OpSel", "AddressType", "DestTuple", "CycleCost", "UpdateReq", and "Length".

## Probabilistic
In the probabilistic mode ("DetsType" and "CycleType" is 1), the function and type decoding method is similar to the determinisitc mode, the difference are as follows.

- "DestDist":

    This defined the accumulated probability of the destinations of each message.
    The last element of each list in "DestDist" is 1.
    For example, when this element is [[0.1, 0.4, 1], [0.3, 1]], this defines that this function has 2 outputs, each have 3 possible definition.

- "CycleDist":

    Similar to the definition logic of "DestDist", this is also a lists of accumulated probabilities of operations.

- Others:

    In this case, elements of these keys are changed into lists of items mentioned in the deterministic mode.
    The distribution of "OpSel", "CycleCost", "UpdateReq", "Length" and "OutType" foollows the distribution defined by "CycleDist".
    The distribution of "DestTuple" foollows the distribution defined by "DestDist".
    For example, when the "DestDist" is [[0.1, 0.4, 1], [0.3, 1]], one of the possible definitions of "DestTuple" is as follows:
    ```
    [[(0, 1, 0, 2, 3), (1, 2, 0, 2, 3), (0, 0, 0, 0, 0)],
        [(0, 1, 0, 1, 0), (0, 0, 2, 1, 0)]]
    ```
    The length of each sub-list corresponding to one group of distribution is the same as the sub-list that belongs to the distribution key ("DestDist" or "CycleDist").
    The total number of the lists is also defined by their lengths.

# Core Definition
After defining the required functions, the deployment, namely which functions belongs to which processing cores should be defined.
This is accomplished by the provided [config generator](./config_generator.py), which can translate a list of dictionary names to the corresponding simulation setup.
Specifically, a core configuration should contain:
- FunctionLists:

    The function lists contain keys or pointers to find the corresponding [Fucntion Dict](#function-dict) defined previously.
    This should contain 3 groups in total, target for "**Default Mmeory Scan**"， "**Input Trigger**", "**Memory Conditional Trigger**", respectively.
    Since the "**Phase Conditional Trigger**" is specialized as phase change, it requires no function list definition.
    Instead, it requires a phase change target lists defined below.

- Triggering Conditions:

    The triggering conditions of "**Memory Conditional Trigger**" and "**Phase Conditional Trigger**" are defined as counter lists in this simulator.
    For example, if the limit of type "1" for "**Memory Conditional Trigger**" is 10, it means the corresponding operations will be triggered when the summation of memory items and handshake variable tagged as type "1" as 10.

- TravelState:

    This is a bool list that defined whether each phase has the "**Default Mmeory Scan**" trigger.

- Traveling Phase Pointer List:

    This lists defined which phase it will jump to when the condition for "**Phase Conditional Trigger**" is met.