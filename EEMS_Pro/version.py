__version__ = "1.0.4"

# Pandas version 2.0.2 (which is distributed with later versions of ArcGIS Pro) has a bug described here: 
# https://github.com/pandas-dev/pandas/issues/46178 
# This was causing an error during the SPDF join (merge), likely because the values in the CSVID field of the EEMS 
# output CSV were being cast to floats during the pd.read_csv() call. 
# The fix was to explicitly cast the CSVID field to an Int32 within the pd.read_csv() call. 

__version__ = "1.0.3"

# Use &MediumSpace; instead of &nbsp; in the command file metadata to allow text wrapping in custom web applications.     
__version__ = "1.0.2"

# Fix NoneType error introduced by writing header to command file   

__version__ = "1.0.1"

# Check for Non-ASCII Characters 

__version__ = "1.0.0"

# Production Release

__version__ = "0.9.0"

# Internal Release for BETA Testing

#__version__ = "0.0.3"

# Add ArcGIS Desktop Compatibility 

#__version__ = "0.0.2"

# Implement Spatially Enabled Data Frame/Pandas Join

#__version__ = "0.0.1"

# Initialize ArcGIS Pro Compatible Version  

