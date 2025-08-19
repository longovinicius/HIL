# FPGA-based Hardware-in-the-Loop (HIL) Simulation of Monophasic inverter with LCL Filter connected to Grid

This project aims to simulate in real time the behavior of a 2-level monophasic inverter connected to a low pass filter connected to grid. 
It was developed FPGA from Xilinx-Spartan7 XC7S100, its ports and constraints are board specific, but can be adapted to any Xilinx FPGA. 



This simulation could eventually be used to validate and test control algorithms for the inverter. XC7S100


The simulated circuit is shown below: 

![PSIM Simulation](docs/images/psim.png)

![Real-time Simulation HIL](docs\images\HIL.jpg)


PSIM's simulation was used as reference. The HIL simulation was runned in real-time with the same conditions as PSIMs model. Data was then sent from FPGA to PC via UART, to be saved and compared with PSIMs simulation. 



Hardware-in-the-Loop (HIL) is a testing technique that integrates real physical components with real-time simulated models. This approach enables the validation of embedded systems, such as electronic controllers, under conditions close to reality, without the need to use the entire physical system.

