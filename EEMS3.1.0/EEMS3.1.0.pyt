import arcpy
import tempfile
import os
import csv
import numpy
from collections import OrderedDict
from mpilot.program import Program

get_mpilot_info_p = Program()

runInBackground = True
version = "3.1.0a3"
cmdFileVarName = "%EEMS Command File Path%"
inputTableVarName = "%EEMS Input Table Path%"

########################################## General Functions ###########################################################


def WriteCommandToFile(cmd, outFldNm, cmdArgs, cmdFile):
    """ Function to write an EEMS Command to the Command File using mpilot. """

    p = Program()  # Create a program each time a command is written to avoid duplicate command writes.
    command = p.find_command_class(cmd)
    p.add_command(command, outFldNm, cmdArgs)

    with open(cmdFile, 'a') as f:
        # Remove quotes for EEMS Online Compatibility.
        s = p.to_string().replace('"', '') + "\n"
        f.write(s)
    return


def CreateMetadataDict(displayName, description, colorMap, reverseColorMap):
    """ Function to create EEMS formatted metadata. Spaces are replaced with &nbsp; for EEMS Online compatibility."""
    metadata = {}

    # The section below replaces special characters with HTML entities.
    # Certain characters will cause mpilot & EEMS Online uploads to fail (due to limitations present in MPilotParse.py)
    # List of problematic special characters: #:,=()[]
    # In mpilot the DisplayName and Descriptions can be quoted (which also works with EEMS Online),
    # but, even quoted, some characters will still cause EEMS Online to fail: =()#[
    # Quotes added by mpilot also need to be removed from the entire command string because EEMS Online won't accept
    # quotes around other arguments (e.g., outputName, DataType, etc.)
    # The DisplayName gets decoded back to ASCII for the tree diagram in spactree.js for proper display in each node.
    # HTML Entities List: https://unicode-table.com/en/html-entities
    char_to_replace = {" ": "&nbsp;",
                       "#": "&num;",
                       ":": "&colon;",
                       ",": "&sbquo;",
                       "=": "&equals;",
                       "(": "&lpar;",
                       ")": "&rpar;",
                       "[": "&lbrack;",
                       "]": "&rbrack;",
                       "'": "&rsquo;",
                       }

    if displayName and displayName != "":
        for key, value in char_to_replace.items():
            displayName = displayName.replace(key, value)
        metadata["DisplayName"] = displayName

    if description and description != "":
        for key, value in char_to_replace.items():
               description = description.replace(key, value)
        metadata["Description"] = description

    colorMap = colorMap.split(": ")[-1]
    if reverseColorMap:
        colorMap += "_r"
    metadata["ColorMap"] = colorMap

    return metadata


def UpdateFieldNames(tool, inputField, validateInputField, resultsField, outputFieldName, displayName, validateDirection=None, falseThreshold=None, trueThreshold=None):
    """ Function to update Default Field Names on certain tools (conversion tools) when certain input parameters change.
        Only way to detect user changes while not triggering re-validation on "Run Entire Model" is to use hidden (Derived) input parameters.
    """

    if inputField.value:

        if tool in ["CvtToFuzzy", "CvtToFuzzyZScore"]:
            # Change the direction if the user has reversed F and T thresholds (will trigger update of default field names).
            changeDirection = False
            if float(trueThreshold.value) > float(falseThreshold.value) and validateDirection.value == "Low":
                validateDirection.value = "High"
                changeDirection = True

            elif float(trueThreshold.value) < float(falseThreshold.value) and validateDirection.value == "High":
                validateDirection.value = "Low"
                changeDirection = True

            # Check for changes to the inputField or the thresholds.
            # Default Field Names calculated as "High" or "Low" + "_" + input name + "_Fz" (eg. High_Ag_Density_Fz)
            if not validateInputField.value or validateInputField.value != str(inputField.value) or changeDirection:
                baseOutputName = validateDirection.value + "_" + inputField.value
                resultsField.value = baseOutputName + "_Fz"
                outputFieldName.value = str(resultsField.value)
                displayName.value = outputFieldName.value.title().replace("_", " ")

                # Prevents resetting of resultsFieldName and displayName on "Run Entire Model"
                validateInputField.value = str(inputField.value)

        elif tool in ["CvtToFuzzyCat", "CvtToFuzzyCurve", "CvtToFuzzyCurveZScore"]:
            # Check for changes to the inputField.
            # Default Field Names calculated as input name + "_Fz" (eg. Ag_Density_Fz)
            if not validateInputField.value or validateInputField.value != str(inputField.value):
                baseOutputName = inputField.value
                resultsField.value = baseOutputName + "_Fz"
                outputFieldName.value = str(resultsField.value)
                displayName.value = outputFieldName.value.title().replace("_", " ")

                # Prevents resetting of resultsFieldName and displayName on "Run Entire Model"
                validateInputField.value = str(inputField.value)

        elif tool in ["CvtToBinary"]:
            if not validateInputField.value or validateInputField.value != str(inputField.value):
                baseOutputName = inputField.value
                resultsField.value = baseOutputName + "_Binary"
                outputFieldName.value = str(resultsField.value)
                displayName.value = outputFieldName.value.title().replace("_", " ")

                # Prevents resetting of resultsFieldName and displayName on "Run Entire Model"
                validateInputField.value = str(inputField.value)

        elif tool in ["CvtFromFuzzy"]:
            if not validateInputField.value or validateInputField.value != str(inputField.value):
                baseOutputName = inputField.value
                resultsField.value = baseOutputName.replace("High_", "").replace("Low_", "").replace("_Fz", "_NonFz")
                outputFieldName.value = str(resultsField.value)
                displayName.value = outputFieldName.value.title().replace("_", " ")

                # Prevents resetting of resultsFieldName and displayName on "Run Entire Model"
                validateInputField.value = str(inputField.value)


        # For all conversion tools, when the user manually changes the resultsField, change the outputFieldName (bubble) and the displayName (Metadata).
        if outputFieldName.value != resultsField.value:
            outputFieldName.value = str(resultsField.value)
            displayName.value = outputFieldName.value.title().replace("_", " ")


# List of available color maps from matplotlib.
cmaps = OrderedDict()

cmaps['Perceptually Uniform Sequential'] = [
            'viridis', 'plasma', 'inferno', 'magma', 'cividis']

cmaps['Sequential'] = [
            'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
            'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
            'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn']

cmaps['Sequential (2)'] = [
            'binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink',
            'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
            'hot', 'afmhot', 'gist_heat', 'copper']

cmaps['Diverging'] = [
            'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
            'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic']

cmaps['Cyclic'] = ['twilight', 'twilight_shifted', 'hsv']

cmaps['Qualitative'] = ['Pastel1', 'Pastel2', 'Paired', 'Accent',
                        'Dark2', 'Set1', 'Set2', 'Set3',
                        'tab10', 'tab20', 'tab20b', 'tab20c']

cmaps['Miscellaneous'] = [
            'flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
            'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg',
            'gist_rainbow', 'rainbow', 'jet', 'turbo', 'nipy_spectral',
            'gist_ncar']

cmapsList = []
for k, v in cmaps.iteritems():
    for c in v:
        cmapDislpayName = k + ": " + c
        cmapsList.append(cmapDislpayName)
cmapsList.sort()


def PrintEEMSHdr():
    arcpy.AddMessage("\n")
    arcpy.AddMessage('+------------------------------------------------------------------+')
    arcpy.AddMessage('|                                                                  |')
    arcpy.AddMessage('|         EEMS - Environmental Evaluation Modeling System          |')
    arcpy.AddMessage('|                                                                  |')
    arcpy.AddMessage('| Implementation for ArcGIS Model Builder                          |')
    arcpy.AddMessage('| Version: ' + version + ' Alpha                                             |')
    arcpy.AddMessage('| Conservation Biology Institute | info@consbio.org                |')
    arcpy.AddMessage('|                                                                  |')
    arcpy.AddMessage('+------------------------------------------------------------------+')
    arcpy.AddMessage("\n")


################################################ Toolbox Class #########################################################


class Toolbox(object):
    def __init__(self):
        self.label = "EEMS%s" % version
        self.alias = "EEMS%s" % version
        self.tools = [EEMSModelInitialize, EEMSModelRun, EEMSRead,
                      CvtToFuzzy, CvtToFuzzyZScore, CvtToFuzzyCat, CvtToFuzzyCurve, CvtToFuzzyCurveZScore, CvtToBinary, CvtFromFuzzy, CvtToFuzzyMeanToMid,
                      FuzzyUnion, FuzzyWeightedUnion, FuzzySelectedUnion, FuzzyOr, FuzzyAnd, FuzzyXOr, FuzzyNot,
                      AMinusB, Sum, WeightedSum, Multiply, ADividedByB, Minimum, Maximum, Mean, WeightedMean, Normalize]


class MetadataParameters(object):
    """ Need to maintain these parameters in a class to allow them to be updated independently within each tool."""
    def __init__(self):
        self.param1Meta = arcpy.Parameter('DisplayName', 'Display Name', 'Input', 'GPString', 'Optional', True, 'Metadata')
        self.param2Meta = arcpy.Parameter('Description', 'Description', 'Input', 'GPString', 'Optional', True, 'Metadata')
        self.param3Meta = arcpy.Parameter('ColorMap', 'Color Map', 'Input', 'GPString', 'Optional', True, 'Metadata')
        self.param4Meta = arcpy.Parameter('ReverseColorMap', 'Reverse Color Map', 'Input', 'GPBoolean', 'Optional', True, 'Metadata')
        self.defaultColorRamp = "Diverging: RdYlBu"

    def getParamList(self):
        paramList = [self.param1Meta, self.param2Meta, self.param3Meta, self.param4Meta]
        return paramList

###############################################  EEMS System Tools #####################################################


class EEMSModelInitialize(object):
    def __init__(self):
        self.label = "EEMS Model Initialize"
        self.description = "Specifies the paths to the files needed to run EEMS (input reporting units & EEMS command file). Clears the contents of the EEMS command file if it exists."
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        cmdFileName = cmdFileVarName.replace("%", "")
        inputTableName = inputTableVarName.replace("%", "")
        param0 = arcpy.Parameter('InputReportingUnits', 'Input Reporting Units', 'Input', 'DEFeatureClass', 'Required')
        param1 = arcpy.Parameter('EEMSInputTable', 'EEMS Input Table', 'Output', 'DEFeatureClass', 'Derived')
        param2 = arcpy.Parameter('EEMSInputTablePath', inputTableName, 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Output', 'DEFile', 'Required') # Must be an output, because it may not exist yet.
        param4 = arcpy.Parameter('EEMSCommandFilePath', cmdFileName, 'Output', 'GPString', 'Derived')

        param3.filter.list = ['mpt', 'MPT']
        # A separate parameter for the Command File Needs to be created so that the name can be known and used
        # as a variable in other tools (eg %EEMS Command File Path%).
        params = [param0, param1, param2, param3, param4]
        return params

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        PrintEEMSHdr()
        try:
            import mpilot

        except:
            arcpy.AddError('EEMS ' + version + ' for ArcGIS requires the mpilot python module. To install mpilot, follow the instructions below:\n\n1. Open up a command prompt(in Windows 10, you can do this by typing "cmd" into the Search box in the bottom left hand corner of your screen).\n2. Type in "cd C:\Python27\ArcGIS10.X\Scripts", replacing "X" with the version of ArcGIS Desktop you have installed.\n3. Type in "pip install mpilot".\n4. Restart ArcCatalog & ArcMap.')
            # Import again to prevent other tools in the model from executing.
            import mpilot

        parameters[1].value = parameters[0].valueAsText
        parameters[2].value = parameters[0].valueAsText
        parameters[4].value = parameters[3].valueAsText
        return


class EEMSRead(object):
    def __init__(self):
        self.label = "EEMS Read"
        self.cmd = "EEMSRead"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('EEMSInputTable', 'EEMS Input Table', 'Input', 'DETable', 'Required')
        param1 = arcpy.Parameter('InputField', 'Input Field', 'Input', 'Field', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')

        param3.value = cmdFileVarName
        # Get field names from the input reporting units
        param1.parameterDependencies = [param0.name]
        mp = MetadataParameters()
        params = [param0, param1, param2, param3] + mp.getParamList()
        params[-2].filter.list = cmapsList
        params[-2].value = "Sequential (2): binary"
        return params

    def updateParameters(self, parameters):
        # Update Metadata Display name if NONE or if the field has changed (inputfield name <> outputfieldname)
        if parameters[1].altered:
            if not parameters[-4].value or str(parameters[1].value) != parameters[2].value:
                parameters[-4].value = str(parameters[1].value).replace("_", " ")

        parameters[2].value = str(parameters[1].value)
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inTblNm = parameters[0].value
        inFldNm = parameters[1].value
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        fieldType = arcpy.ListFields(inTblNm, str(inFldNm))[0].type

        if fieldType in ['Double', 'Single']:
            dataType = 'Float'
        elif fieldType in ['Integer', 'SmallInteger']:
            dataType = 'Integer'
        else:
            warning = "\nWarning!!! Input Fields should be of type integer or float. The %s field is of type %s.\nAn attempt will be made to coerce the values in this field to a float. This may cause problems if unsuccessful.\n" % (inFldNm, fieldType)
            arcpy.AddWarning(warning)
            dataType = "Float"

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFileName', inTblNm), ('InFieldName', inFldNm), ('DataType', dataType), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class EEMSModelRun(object):
    def __init__(self):
        self.label = "EEMS Model Run"
        self.description = "Executes the commands in the EEMS command file on the input reporting units. Stores the results in the output reporting units."
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('FinalOutputField', 'Final Output Field',  'Input', 'GPString', 'Required')
        param1 = arcpy.Parameter('OutputReportingUnits', 'Output Reporting Units', 'Output', 'DEFeatureClass', 'Required')
        param2 = arcpy.Parameter('InputReportingUnits', 'Input Reporting Units', 'Input', 'GPString', 'Required')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')

        # Turned this into a feature class (rather than a table) so that it can be copied to the output feature class.
        param2.value = inputTableVarName
        param3.value = cmdFileVarName
        params = [param0, param1, param2, param3]
        return params

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):


        inputReportingUnits = parameters[2].value
        outputReportingUnits = parameters[1].value
        cmdFileNm = parameters[3].value

        messages.addMessage("\nCopying Input Reporting Units to Output Reporting Units...\n(Only Keeping OBJECTID and Shape fields)")

        self.CopyInputRUToOutputRU(inputReportingUnits, outputReportingUnits)

        messages.addMessage("\nCreating CSV file from the Input Reporting Units...")
        EEMSCSVFNm = self.CreateCSVFromInputRU(inputReportingUnits, messages)

        with open(cmdFileNm) as f:
            messages.addMessage("\nConverting EEMS Command File to a String...")
            progStr = f.read()
            progStr = progStr.replace(inputReportingUnits, EEMSCSVFNm)

            # Parse the MPilot program string and return a new Program representing the model.
            p = Program.from_source(progStr)

            # Add the CSVID Field to the list of output fields needed.
            EEMSOutFields = p.commands.keys() + ["CSVID"]

            # Add a READ command for the  CSVID Field.
            EEMSMPilotRead = p.find_command_class('EEMSRead')
            p.add_command(EEMSMPilotRead, "CSVID", {'InFileName': EEMSCSVFNm, 'InFieldName': "CSVID"})

            # Add a Write command to write the results out to the CSV file
            EEMSMPilotWrite = p.find_command_class('EEMSWrite')
            p.add_command(EEMSMPilotWrite, "Results", {'OutFileName': EEMSCSVFNm, 'OutFieldNames': EEMSOutFields})

        messages.addMessage("\nRunning EEMS on the CSV file...")
        p.run()

        messages.addMessage("\nJoining CSV file to Output Reporting Units...")
        self.JoinCSVtoOutputRU(EEMSCSVFNm, outputReportingUnits, messages)

        messages.addMessage("\nSuccess\n")
        return

    def CopyInputRUToOutputRU(self, inputReportingUnits, outputReportingUnits):
        """ Copy the input reporting units to the output reporting units, but only keep the OBJECTID and SHAPE Fields. """

        inputFieldNames = [f.name for f in arcpy.ListFields(inputReportingUnits)]

        outputFieldList = "OBJECTID OBJECTID VISIBLE NONE; Shape Shape VISIBLE NONE"
        for inputFieldName in inputFieldNames:
            if inputFieldName not in ["OBJECTID", "SHAPE"]:
                outputFieldList += "; " + inputFieldName + " " + inputFieldName + " HIDDEN NONE"

        arcpy.MakeFeatureLayer_management(
            in_features=inputReportingUnits,
            out_layer="inputReportingUnitsLayer", where_clause="", workspace="",
            field_info=outputFieldList
        )

        arcpy.CopyFeatures_management(
            in_features="inputReportingUnitsLayer",
            out_feature_class=outputReportingUnits
        )
        return

    def CreateCSVFromInputRU(self, inputReportingUnits, messages):
        """ Create the CSV File that EEMS runs on from the Input Reporting Units. """

        tmpDir = tempfile.mkdtemp()
        EEMSCSVFNm = tmpDir + os.sep + "EEMS_Output.csv"

        with open(EEMSCSVFNm, 'wb') as f:
            rows = arcpy.SearchCursor(inputReportingUnits)
            csvFile = csv.writer(f)
            fieldnames = [field.name for field in arcpy.ListFields(inputReportingUnits) if field.name != 'Shape']

            allRows = []
            for row in rows:
                rowlist = []
                for field in fieldnames:
                    rowlist.append(row.getValue(field))
                allRows.append(rowlist)

            # This changes whatever the OID field name is to a standard name "CSVID"
            fieldnames[0] = 'CSVID'

            csvFile.writerow(fieldnames)
            for row in allRows:
                csvFile.writerow(row)

        messages.addMessage(EEMSCSVFNm)
        return EEMSCSVFNm


    def JoinCSVtoOutputRU(self, csv, outputRU, messages):
        """ Join the CSV containing the EEMS Input & Output Fields to the Output Reporting Units """

        tmpOutTbl = "in_memory" + os.sep + 'Join_Table'
        arcpy.CopyRows_management(csv, tmpOutTbl)
        fieldsToJoin = ';'.join([field.name for field in arcpy.ListFields(tmpOutTbl) if field.name != 'CSVID'])
        OIDField = arcpy.Describe(str(outputRU)).OIDFieldName
        arcpy.JoinField_management(outputRU, OIDField, tmpOutTbl, 'CSVID', fieldsToJoin)

        messages.addMessage(str(outputRU))
        return


############################################  Convert to Fuzzy Tools ###################################################


class CvtToFuzzy(object):
    def __init__(self):
        self.label = "Convert to Fuzzy"
        self.cmd = "CvtToFuzzy"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputField', 'Input Field', 'Input', 'GPType', 'Required')
        param1 = arcpy.Parameter('ThresholdSettingMethod', 'Threshold Setting Method', 'Input', 'GPString', 'Optional')
        param2 = arcpy.Parameter('FalseThreshold', 'False Threshold', 'Input', 'GPDouble', 'Required')
        param3 = arcpy.Parameter('TrueThreshold', 'True Threshold', 'Input', 'GPDouble', 'Required')
        param4 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param5 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param6 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param7 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')
        param8 = arcpy.Parameter('ValidateDirection', 'Validate Direction', 'Input', 'GPString', 'Derived')

        param1.value = 'Use custom values specified below'
        param8.value = "High"
        param6.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4, param5, param6, param7, param8] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        """ Set the True and False thresholds based on the user defined threshold setting method. """

        if parameters[0].value not in [field.name for field in arcpy.ListFields(inputTableVarName)]:
            parameters[1].filter.list = ['Use custom values specified below']
        else:
            parameters[1].filter.list = ['Use custom values specified below',
                              'Min/Max (True Threshold > False Threshold)',
                              '0.5 Std Dev (True Threshold > False Threshold)', '1.0 Std Dev (True Threshold > False Threshold)', '1.5 Std Dev (True Threshold > False Threshold)', '2.0 Std Dev (True Threshold > False Threshold)','2.5 Std Dev (True Threshold > False Threshold)', '3.0 Std Dev (True Threshold > False Threshold)', '3.5 Std Dev (True Threshold > False Threshold)', '4.0 Std Dev (True Threshold > False Threshold)',
                              'Min/Max (False Threshold > True Threshold)',
                              '0.5 Std Dev (False Threshold > True Threshold)', '1.0 Std Dev (False Threshold > True Threshold)', '1.5 Std Dev (False Threshold > True Threshold)', '2.0 Std Dev (False Threshold > True Threshold)','2.5 Std Dev (False Threshold > True Threshold)', '3.0 Std Dev (False Threshold > True Threshold)', '3.5 Std Dev (False Threshold > True Threshold)', '4.0 Std Dev (False Threshold > True Threshold)',
                              ]

        if parameters[1].value == "Use custom values specified below":
            parameters[2].enabled = True
            parameters[3].enabled = True

        if (parameters[0].altered or parameters[1].altered) and parameters[1].value != "Use custom values specified below":
            field_values = []
            field_name = parameters[0].value
            with arcpy.da.SearchCursor(inputTableVarName, field_name) as sc:
                for row in sc:
                    if row[0] is not None:
                        field_values.append(row[0])
                min_val = numpy.min(field_values)
                max_val = numpy.max(field_values)
                mean_val = numpy.mean(field_values)
                std = numpy.std(field_values)

                threshold_setting_method = parameters[1].value

                if threshold_setting_method == "Min/Max (True Threshold > False Threshold)":
                    parameters[2].value = min_val
                    parameters[3].value = max_val
                elif threshold_setting_method == "Min/Max (False Threshold > True Threshold)":
                    parameters[2].value = max_val
                    parameters[3].value = min_val
                else:
                    num_std_dev = float(threshold_setting_method.split(" ")[0])
                    if "True Threshold > False Threshold" in threshold_setting_method:
                        parameters[2].value = round((mean_val - (num_std_dev * std)), 8)
                        parameters[3].value = round((mean_val + (num_std_dev * std)), 8)

                    elif "False Threshold > True Threshold" in threshold_setting_method:
                        parameters[2].value = round((mean_val + (num_std_dev * std)), 8)
                        parameters[3].value = round((mean_val - (num_std_dev * std)), 8)

            parameters[2].enabled = False
            parameters[3].enabled = False

        if parameters[2].value is not None and parameters[3].value is not None:
            UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[7], resultsField=parameters[4], outputFieldName=parameters[5], displayName=parameters[-4], validateDirection=parameters[8], falseThreshold=parameters[2], trueThreshold=parameters[3])

        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = parameters[0].value
        falseThresh = parameters[2].value
        trueThresh = parameters[3].value
        outFldNm = parameters[5].value
        cmdFile = parameters[6].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldName', inFldNm), ('FalseThreshold', falseThresh), ('TrueThreshold', trueThresh), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class CvtToFuzzyZScore(object):
    def __init__(self):
        self.label = "Convert to Fuzzy Z Score"
        self.cmd = "CvtToFuzzyZScore"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputField', 'Input Field', 'Input', 'GPType', 'Required')
        param1 = arcpy.Parameter('FalseThresholdZScore', 'False Threshold Z Score', 'Input', 'GPDouble', 'Required')
        param2 = arcpy.Parameter('TrueThresholdZScore', 'True Threshold Z Score', 'Input', 'GPDouble', 'Required')
        param3 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param5 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param6 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')
        param7 = arcpy.Parameter('ValidateDirection', 'Validate Direction', 'Input', 'GPString', 'Derived')

        param1.value = -1
        param2.value = 1
        param7.value = "High"
        param5.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4, param5, param6, param7] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[6], resultsField=parameters[3], outputFieldName=parameters[4], displayName=parameters[-4], validateDirection=parameters[7], falseThreshold=parameters[1], trueThreshold=parameters[2])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = parameters[0].value
        falseThreshZScore = parameters[1].value
        trueThreshZScore = parameters[2].value
        outFldNm = parameters[4].value
        cmdFile = parameters[5].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldName', inFldNm), ('FalseThresholdZScore', falseThreshZScore), ('TrueThresholdZScore', trueThreshZScore), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class CvtToFuzzyCat(object):
    """ Appears to be a bug in the source code for this operator. Error says Argument name: int_field  Should be one of: ['Integer', 'Positive Integer']  Is: Float"""
    def __init__(self):
        self.label = "Convert to Fuzzy Category"
        self.cmd = "CvtToFuzzyCat"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputField', 'Input Field', 'Input', 'GPType', 'Required')
        param1 = arcpy.Parameter('Raw Value', 'Raw Value', 'Input', 'GPValueTable', 'Required')
        param2 = arcpy.Parameter('DefaultFuzzyValue', 'Defaut Fuzzy Value', 'Input', 'GPDouble', 'Required')
        param3 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param5 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param6 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param1.columns = [['GPString', 'Raw Values'], ['GPDouble', 'Fuzzy Values']]
        param5.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4, param5, param6] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        global inputRawList, inputFuzzyList
        inputRawList = []
        inputFuzzyList = []
        if parameters[1].altered:
            for inputList in parameters[1].value:
                inputRawList.append(inputList[0])
                inputFuzzyList.append(str(inputList[1]))

        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[6], resultsField=parameters[3], outputFieldName=parameters[4], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        rawValues = "[" + ",".join(inputRawList) + "]"
        fuzzyValues = "[" + ",".join(inputFuzzyList) + "]"
        inFldNm = parameters[0].value
        defaultFuzzyValue = parameters[2].value
        outFldNm = parameters[4].value
        cmdFile = parameters[5].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldName', inFldNm), ('RawValues', rawValues), ('FuzzyValues', fuzzyValues), ('DefaultFuzzyValue', defaultFuzzyValue), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class CvtToFuzzyCurve(object):
    def __init__(self):
        self.label = "Convert to Fuzzy Curve"
        self.cmd = "CvtToFuzzyCurve"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputField', 'Input Field', 'Input', 'GPType', 'Required')
        param1 = arcpy.Parameter('Raw Value', 'Raw Value', 'Input', 'GPValueTable', 'Required')
        param2 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param3 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param4 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param5 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param1.columns = [['GPString', 'Raw Values'], ['GPDouble', 'Fuzzy Values']]
        param4.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4, param5] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        global inputRawList, inputFuzzyList
        inputRawList = []
        inputFuzzyList = []
        if parameters[1].altered:
            for inputList in parameters[1].value:
                inputRawList.append(inputList[0])
                inputFuzzyList.append(str(inputList[1]))

        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[5], resultsField=parameters[2], outputFieldName=parameters[3], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        rawValues = "[" + ",".join(inputRawList) + "]"
        fuzzyValues = "[" + ",".join(inputFuzzyList) + "]"
        inFldNm = parameters[0].value
        outFldNm = parameters[3].value
        cmdFile = parameters[4].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldName', inFldNm), ('RawValues', rawValues), ('FuzzyValues', fuzzyValues), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class CvtToFuzzyCurveZScore(object):
    def __init__(self):
        self.label = "Convert to Fuzzy Curve Z Score"
        self.cmd = "CvtToFuzzyCurveZScore"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputField', 'Input Field', 'Input', 'GPType', 'Required')
        param1 = arcpy.Parameter('ZScoreValue', 'Z Score Value', 'Input', 'GPValueTable', 'Required')
        param2 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param3 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param4 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param5 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param1.columns = [['GPString', 'Z Score Values'], ['GPDouble', 'Fuzzy Values']]
        param4.value = cmdFileVarName
        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4, param5] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        global inputZScoreList, inputFuzzyList
        inputZScoreList = []
        inputFuzzyList = []
        if parameters[1].altered:
            for inputList in parameters[1].value:
                inputZScoreList.append(inputList[0])
                inputFuzzyList.append(str(inputList[1]))

        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[5], resultsField=parameters[2], outputFieldName=parameters[3], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        zScoreValues = "[" + ",".join(inputZScoreList) + "]"
        fuzzyValues = "[" + ",".join(inputFuzzyList) + "]"
        inFldNm = parameters[0].value
        outFldNm = parameters[3].value
        cmdFile = parameters[4].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldName', inFldNm), ('ZScoreValues', zScoreValues), ('FuzzyValues', fuzzyValues), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class CvtToBinary(object):
    def __init__(self):
        self.label = "Convert to Binary"
        self.cmd = "CvtToBinary"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputField', 'Input Field', 'Input', 'GPType', 'Required')
        param1 = arcpy.Parameter('Threshold', 'Threshold', 'Input', 'GPDouble', 'Required')
        param2 = arcpy.Parameter('Direction', 'Direction', 'Input', 'GPString', 'Required')
        param3 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param5 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param6 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param1.value = 0
        param2.filter.list = ['HighToLow', 'LowToHigh']
        param2.value = "LowToHigh"
        param5.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4, param5, param6] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[6], resultsField=parameters[3], outputFieldName=parameters[4], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = parameters[0].value
        threshold = parameters[1].value
        direction = parameters[2].value
        outFldNm = parameters[4].value
        cmdFile = parameters[5].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldName', inFldNm), ('Threshold', threshold), ('Direction', direction), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class CvtFromFuzzy(object):
    def __init__(self):
        self.label = "Convert From Fuzzy"
        self.cmd = "CvtFromFuzzy"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputField', 'Input Field', 'Input', 'GPType', 'Required')
        param1 = arcpy.Parameter('FalseThreshold', 'False Threshold', 'Input', 'GPDouble', 'Required')
        param2 = arcpy.Parameter('TrueThreshold', 'True Threshold', 'Input', 'GPDouble', 'Required')
        param3 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param5 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param6 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param1.value = -1
        param2.value = 1
        param5.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4, param5, param6] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[6], resultsField=parameters[3], outputFieldName=parameters[4], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = parameters[0].value
        falseThresh = parameters[1].value
        trueThresh = parameters[2].value
        outFldNm = parameters[4].value
        cmdFile = parameters[5].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldName', inFldNm), ('FalseThreshold', falseThresh), ('TrueThreshold', trueThresh), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return
    
    
class CvtToFuzzyMeanToMid(object):
    def __init__(self):
        self.label = "Convert to Fuzzy Mean to Mid"
        self.cmd = "CvtToFuzzyMeanToMid"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputField', 'Input Field', 'Input', 'GPType', 'Required')
        param1 = arcpy.Parameter('FuzzyValues', 'Fuzzy Values', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('IgnoreZeros', 'Ignore Zeros', 'Input', 'GPString')
        param3 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param5 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param6 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param5.value = cmdFileVarName
        param2.filter.list = ["True", "False"]

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4, param5, param6] + mp.getParamList()

        params[1].value = "-1, -0.5, 0, 0.5, 1"
        params[2].value = "False"
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[6], resultsField=parameters[3], outputFieldName=parameters[4], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        
        """ Validate list of input fuzzy values (5 fuzzy values separated by commas) """ 
       
        if parameters[1].altered:
            try:
                inputFuzzyValueList = [float(val) for val in parameters[1].value.split(",")]
                count = len(inputFuzzyValueList)
                
                # VALIDATE: Count == 5 
                if count > 5 or count < 5:
                    parameters[1].setErrorMessage("Invalid number of input values (%s). Enter a list of five (no more, no less) fuzzy values separated by commas. For example: -1, -0.5, 0, 0.5, 1" % count)

                # VALIDATE: Fuzzy Input Range 
                for inputFuzzyValue in inputFuzzyValueList:
                    if inputFuzzyValue < -1 or inputFuzzyValue > 1:
                        parameters[1].setErrorMessage("Invalid Fuzzy Value (%s). Fuzzy values must be between -1 and + 1." % inputFuzzyValue)
            except:
                # ALL OTHER ERRORS
                parameters[1].setErrorMessage("Enter a list of five (no more, no less) fuzzy values separated by commas. For example: -1, -0.5, 0, 0.5, 1")
        return

    def execute(self, parameters, messages):
        
        inFldNm = parameters[0].value
        fuzzyValues = [float(val) for val in parameters[1].value.split(",")]
        ignoreZeros = parameters[2].value
        outFldNm = parameters[4].value
        cmdFile = parameters[5].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldName', inFldNm), ('IgnoreZeros', ignoreZeros), ('FuzzyValues', fuzzyValues ), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


##################################################  Fuzzy Operators  ###################################################


class FuzzyUnion(object):
    def __init__(self):
        self.label = "Fuzzy Union"
        self.cmd = "FuzzyUnion"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPType', 'Required', None, None, None, True)
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + str(parameters[0].value).replace(";", ",") + "]"
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class FuzzyWeightedUnion(object):
    def __init__(self):
        self.label = "Fuzzy Weighted Union"
        self.cmd = "FuzzyWeightedUnion"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPValueTable', 'Required')
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param0.columns = [['GPType', 'Input Field'], ['GPDouble', 'Weight']]
        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        # Use global vars to share with execute function.
        #...because we can't update object attributes because new instances are spun up for every function call.
        global inputFieldsList, inputWeightsList
        inputFieldsList = []
        inputWeightsList = []
        # Create default output field name. Truncate the field name to meet 64 char field name limit.
        if parameters[0].altered:
            for inputList in parameters[0].value:
                inputFieldsList.append(inputList[0].value)
                inputWeightsList.append(str(inputList[1]))

        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + ",".join(inputFieldsList) + "]"
        weights = "[" + ",".join(inputWeightsList) + "]"
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('Weights', weights), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class FuzzySelectedUnion(object):
    """ Note that this tool and FuzzyXOr require numpy 1.10.0 (uses np.stack). Can't upgrade arcgis version of numpy. """
    def __init__(self):
        self.label = "Fuzzy Selected Union"
        self.cmd = "FuzzySelectedUnion"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPType', 'Required', None, None, None, True)
        param1 = arcpy.Parameter('NumberofValuesToConsider', 'Number of Values To Consider', 'Input', 'GPLong')
        param2 = arcpy.Parameter('SelectTruestorFalsestValues?', 'Select Truest or Falsest Values?', 'Input', 'GPString')
        param3 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param5 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param6 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param2.filter.list = ['Truest', 'Falsest']
        param5.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4, param5, param6] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[6], resultsField=parameters[3], outputFieldName=parameters[4], displayName=parameters[-4])

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + str(parameters[0].value).replace(";", ",") + "]"
        numberToConsider = parameters[1].value
        TorF = parameters[2].value
        outFldNm = parameters[4].value
        cmdFile = parameters[5].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('TruestOrFalsest', TorF), ('NumberToConsider', numberToConsider), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class FuzzyOr(object):
    def __init__(self):
        self.label = "Fuzzy Or"
        self.cmd = "FuzzyOr"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPType', 'Required', None, None, None, True)
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + str(parameters[0].value).replace(";", ",") + "]"
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class FuzzyAnd(object):
    def __init__(self):
        self.label = "Fuzzy And"
        self.cmd = "FuzzyAnd"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPType', 'Required', None, None, None, True)
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + str(parameters[0].value).replace(";", ",") + "]"
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class FuzzyXOr(object):
    """ Note that this tool and FuzzySelectedUnion require numpy 1.10.0 (uses np.stack). Can't upgrade arcgis version of numpy. """
    def __init__(self):
        self.label = "Fuzzy XOr"
        self.cmd = "FuzzyXOr"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPType', 'Required', None, None, None, True)
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + str(parameters[0].value).replace(";", ",") + "]"
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class FuzzyNot(object):
    def __init__(self):
        self.label = "Fuzzy Not"
        self.cmd = "FuzzyNot"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputField', 'Input Field', 'Input', 'GPType', 'Required')
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = parameters[0].value
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldName', inFldNm), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


##############################################  Non-Fuzzy Operators ####################################################


class AMinusB(object):
    def __init__(self):
        self.label = "X Minus Y"
        self.cmd = "AMinusB"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('StartingField', 'Starting Field', 'Input', 'GPType', 'Required')
        param1 = arcpy.Parameter('FieldToSubtract', 'Field To Subtract', 'Input', 'GPType', 'Required')
        param2 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param3 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param4 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param5 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param4.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4, param5] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[5], resultsField=parameters[2], outputFieldName=parameters[3], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        aVal = parameters[0].value
        bVal = parameters[1].value
        outFldNm = parameters[3].value
        cmdFile = parameters[4].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('A', aVal), ('B', bVal), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class Sum(object):
    def __init__(self):
        self.label = "Sum"
        self.cmd = "Sum"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPType', 'Required', None, None, None, True)
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + str(parameters[0].value).replace(";", ",") + "]"
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class WeightedSum(object):
    def __init__(self):
        self.label = "Weighted Sum"
        self.cmd = "WeightedSum"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPValueTable', 'Required')
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param0.columns = [['GPType', 'Input Field'], ['GPDouble', 'Weight']]
        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        # Use global vars to share with execute function.
        #...because we can't update object attributes because new instances are spun up for every function call.
        global inputFieldsList, inputWeightsList
        inputFieldsList = []
        inputWeightsList = []
        # Create default output field name. Truncate the field name to meet 64 char field name limit.
        if parameters[0].altered:
            for inputList in parameters[0].value:
                inputFieldsList.append(inputList[0].value)
                inputWeightsList.append(str(inputList[1]))

        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + ",".join(inputFieldsList) + "]"
        weights = "[" + ",".join(inputWeightsList) + "]"
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('Weights', weights), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class Multiply(object):
    def __init__(self):
        self.label = "Multiply"
        self.cmd = "Multiply"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPType', 'Required', None, None, None, True)
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + str(parameters[0].value).replace(";", ",") + "]"
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class ADividedByB(object):
    def __init__(self):
        self.label = "X Divided By Y"
        self.cmd = "ADividedByB"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('StartingField', 'Starting Field', 'Input', 'GPType', 'Required')
        param1 = arcpy.Parameter('FieldToDivideBy', 'Field To Divide By', 'Input', 'GPType', 'Required')
        param2 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param3 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param4 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param5 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param4.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4, param5] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[5], resultsField=parameters[2], outputFieldName=parameters[3], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        aVal = parameters[0].value
        bVal = parameters[1].value
        outFldNm = parameters[3].value
        cmdFile = parameters[4].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('A', aVal), ('B', bVal), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class Minimum(object):
    def __init__(self):
        self.label = "Minimum"
        self.cmd = "Minimum"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPType', 'Required', None, None, None, True)
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + str(parameters[0].value).replace(";", ",") + "]"
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class Maximum(object):
    def __init__(self):
        self.label = "Maximum"
        self.cmd = "Maximum"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPType', 'Required', None, None, None, True)
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + str(parameters[0].value).replace(";", ",") + "]"
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class Mean(object):
    def __init__(self):
        self.label = "Mean"
        self.cmd = "Mean"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPType', 'Required', None, None, None, True)
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + str(parameters[0].value).replace(";", ",") + "]"
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class WeightedMean(object):
    def __init__(self):
        self.label = "Weighted Mean"
        self.cmd = "WeightedMean"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputFields', 'Input Fields', 'Input', 'GPValueTable', 'Required')
        param1 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param2 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param3 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param0.columns = [['GPType', 'Input Field'], ['GPDouble', 'Weight']]
        param3.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        global inputFieldsList, inputWeightsList
        inputFieldsList = []
        inputWeightsList = []
        if parameters[0].altered:
            for inputList in parameters[0].value:
                inputFieldsList.append(inputList[0].value)
                inputWeightsList.append(str(inputList[1]))

        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[4], resultsField=parameters[1], outputFieldName=parameters[2], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = "[" + ",".join(inputFieldsList) + "]"
        weights = "[" + ",".join(inputWeightsList) + "]"
        outFldNm = parameters[2].value
        cmdFile = parameters[3].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldNames', inFldNm), ('Weights', weights), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return


class Normalize(object):
    def __init__(self):
        self.label = "Normalize"
        self.cmd = "Normalize"
        self.description = get_mpilot_info_p.find_command_class(self.cmd).__doc__
        self.canRunInBackground = runInBackground

    def getParameterInfo(self):
        param0 = arcpy.Parameter('InputField', 'Input Field', 'Input', 'GPType', 'Required')
        param1 = arcpy.Parameter('StartVal', 'Start Value', 'Input', 'GPDouble', 'Required')
        param2 = arcpy.Parameter('EndVal', 'End Value', 'Input', 'GPDouble', 'Required')
        param3 = arcpy.Parameter('ResultsField', 'Results Field', 'Input', 'GPString', 'Required')
        param4 = arcpy.Parameter('OutputFieldName', 'Output Field Name', 'Output', 'GPString', 'Derived')
        param5 = arcpy.Parameter('EEMSCommandFile', 'EEMS Command File', 'Input', 'GPString', 'Required')
        param6 = arcpy.Parameter('ValidateInputField', 'Validate Input Field', 'Input', 'GPString', 'Derived')

        param1.value = 0
        param2.value = 1
        param5.value = cmdFileVarName

        mp = MetadataParameters()
        params = [param0, param1, param2, param3, param4, param5, param6] + mp.getParamList()
        params[-1].value = True
        params[-2].value = mp.defaultColorRamp
        params[-2].filter.list = cmapsList
        return params

    def updateParameters(self, parameters):
        UpdateFieldNames(tool=self.cmd, inputField=parameters[0], validateInputField=parameters[6], resultsField=parameters[3], outputFieldName=parameters[4], displayName=parameters[-4])
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        inFldNm = parameters[0].value
        startVal = parameters[1].value
        endVal = parameters[2].value
        outFldNm = parameters[4].value
        cmdFile = parameters[5].value

        metadataDict = CreateMetadataDict(parameters[-4].value, parameters[-3].value, parameters[-2].value, parameters[-1].value)
        cmdArgs = OrderedDict([('InFieldName', inFldNm), ('StartVal', startVal), ('EndVal', endVal), ('Metadata', metadataDict)])
        WriteCommandToFile(self.cmd, outFldNm, cmdArgs, cmdFile)
        return
