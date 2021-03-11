# EEMS3.00 Toolboox for ArcGIS Desktop

The Environmental Evaluation Modeling System (EEMS) is a fuzzy logic modelling system developed by CBI (Sheehan & Gough, 2016). EEMS 3.0 for ArcGIS consists of a set of script tools inside a Python Toolbox, which have been rewritten from the ground up to interface with EEMS 3.0 and the data processing framework on which it’s built (MPilot).  EEMS 3.0 for ArcGIS includes a new set of data manipulation and conversion tools, interface changes, usability enhancements, and a new set of input fields which allow the user to associate metadata with each node in an EEMS Model (currently this includes Display Name, Description, and Color Map to use for rendering). This information can then be used by EEMS Online and other web applications to improve model interpretation and usability. 

Unlike conventional GIS applications that use Boolean logic (True/False or 1/0) or scored input layers, evaluative logic models rely on fuzzy logic. Simply put, fuzzy logic allows the user to assign shades of gray to thoughts and ideas rather than being restricted to black (false) and white (true) determinations. All data inputs (regardless of the type--ordinal, nominal, or continuous) are converted into fuzzy values between -1 (false) and +1 (true) up to six decimal places. A user defined function converts inputs from original values (often referred to as raw values or values in raw space) to fuzzy values (values in fuzzy space). Values in raw space may be combined using mathematical operators (e.g. sum, weighted mean) before being translated into fuzzy space. Values in fuzzy space are combined using fuzzy logic operators (e.g. AND, OR). There are many advantages of this modeling approach: (1) it is highly interactive and flexible; (2) it is easy to visualize thought processes; (3) the logic components are modular making it easy to include or exclude pieces of the logic design; (4) the logic can be managed using a number of different mechanisms; and (5) numerous, diverse topics can be included into a single integrated analysis. 

## Getting Started

EEMS Models are constructed in ArcGIS Model Builder using the tools in the EEMS3.x.pyt toolbox. Refer to EEMS3.X_Manual.pdf for additional information regarding the principles of fuzzy logic modeling, as well as a tutorial to help you get started.

## Citation

Sheehan, T. and Gough, M. (2016) A platform-independent fuzzy logic modeling framework for environmental decision support. Ecological Informatics. 34:92-101


