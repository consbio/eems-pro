# Environmental Evaluation Modeling System (EEMS) Pro

The Environmental Evaluation Modeling System (EEMS) is an evaluative fuzzy logic modeling system developed by the Conservation Biology Institute (Sheehan & Gough, 2016). Simply put, fuzzy-logic allows the user to assign shades of gray to thoughts and ideas rather than being limited to the binary (true/false) determinations of traditional logic. It is this concept of "partial truth" which allows fuzzy-logic models to more accurately capture and resemble human patterns of thought. 

EEMS modeling has been applied by CBI scientists in a range of ecological evaluations. In the Tehachapis and Southern Sierra a model incorporating data for habitat presence, habitat linkage, and disturbance was used to find areas of high ecological value and to provide guidance for reserve design to inform siting Wind Energy. For the Bureau of Land Management Rapid Ecological Assessments of the Sonoran Desert and Colorado Plateau ecoregions, several EEMS models were developed and used to evaluate a variety of current and projected ecological metrics. More recently, CBI used EEMS to help support the offshore wind energy planning process in California by developing models designed to help assess a range of considerations at a given location, such as energy potential, deployment feasibility, ocean uses, fisheries, and marine life occurrence. 

EEMS is written in Python and maintained as a collection of libraries within MPilot (A plugin-based, environmental modeling framework developed by CBI). 

EEMS Pro consists of a set of script tools within a Python Toolbox (EEMS_Pro.pyt). It interfaces with the EEMS libraries in MPilot and allows for the visual construction of fuzzy logic models from within ESRI's ModelBuilder environment.

To use EEMS Pro, the user first prepares an Input Reporting Units Feature Class containing the polygons and input fields to be evaluated. This is then added to the ModelBuilder canvas where it is connected to the tools in the EEMS Pro Toolbox to create a logical tree-based hierarchy. At the bottom of that hierarchy, initial input data (regardless of the type--ordinal, nominal, or continuous) are first READ in and converted to fuzzy space (based on the premise that each input value can be represented by a value ranging from -1 for totally false to +1 for totally true).  Values in raw space may be combined using mathematical operators (e.g. SUM, WEIGHTED MEAN) before being translated into fuzzy space. Fuzzy logic operations (analogous to basic logic operations such as AND and OR) are then used to combine nodes hierarchically until a final value representing the answer to a primary question is produced (e.g. What is the relative value of endangered species habitat across our study area?). 

When the ModelBuilder model is run, EEMS Pro creates (1) A command (mpt) file containing the model instructions, and, (2) a CSV file created from attribute table of the input reporting units feature class. These two files are handed off to the EEMS libraries in MPilot where the model is executed and the resulting output data are added to the CSV. The CSV file (containing both the input and output fields) is then joined backed to an output copy of the input reporting units. 

The current version of EEMS Pro is designed to be compatible with both ArcGIS Pro and ArcGIS Desktop. It includes a new set of data manipulation and conversion tools, interface changes, usability enhancements, bug fixes, and a set of input parameters which allows metadata to be associated with each node in a model (currently this includes a Display Name, Description, Data Sources, and a Color Map). This information is used by EEMS Online, Data Basin, and other web applications to improve model interpretation and usability.

For more information on fuzzy logic and EEMS, including a tutorial, please refer to the EEMS Pro Manual. 

## Requirements 

```bash
1. Windows 7 or greater

2. ArcGIS Pro or ArcGIS Desktop (v10.6 or greater)

3. MPilot (v1.2.5 or greater)

In addition to the software requirements listed above, the user should have formal GIS training, and be experienced with ArcGIS and ArcGIS Model Builder.  
```

## Installing 

In order to use EEMS Pro, you'll need to have ArcGIS Pro or ArcGIS Desktop Installed, as well as the MPilot Python module. 

If you plan on using EEMS Pro with ArcGIS Desktop, you can simply install MPilot into your ArcGIS python installation using `pip` 
```bash
$ pip install mpilot
```
However, if you plan on using EEMS Pro in ArcGIS Pro, you will need to install MPilot into a cloned conda environment. 

More information on the installation process for both ArcGIS platforms is available in the EEMS Pro Manual. 

## Getting Started

EEMS Models are constructed in ArcGIS Model Builder using the tools in the EEMS Pro toolbox. Refer to EEMS_Pro_Manual.pdf for additional information regarding the principles of fuzzy logic modeling, as well as a tutorial to help you get started.

## Citation

Sheehan, T. and Gough, M. (2016) A platform-independent fuzzy logic modeling framework for environmental decision support. Ecological Informatics. 34:92-101


