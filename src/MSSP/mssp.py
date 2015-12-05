"""
Created on Oct 28, 2015

@author: brandon
This is a set of functions for reading grid and header content from the 
MSSP spreadsheets, and formatting it into some semblance of a data
structure.

Overall strategy:
the object types are defined based on the spreadsheet content each time
(for later semantic management, perhaps?)


Since there are three different MSSP spreadsheets, this class has at least
three different functions to load the spreadsheets, however the processing
is different for each spreadsheet:
 * Monitoring
   - questions by columns
   - monitoring options by rows
   - annotations in table grid
   
 * Assessment
   - assessment methods by columns
   - indices by rows (OPEN QUESTION: relation of these to Qs)
   - minimum criteria in table grid
   - some annotations also
   
 * Harvest Control Rules
   - questions by rows
   - rules by columns
   - annotations in table grid

From that come the entity types:
 - monitoring options
 - indices
 - questions
 - criteria
    
"""


import openpyxl as xl
import entities



class MSSPFile(object):
    def __init__(self, files=default_MSSP_FILES,)


class MSSP(object):
    """
    Tools for extracting and refactoring information contained in MSSP spreadsheets

    MSSP = Management Strategy Selection Process
    Consists of a collection of 3 static spreadsheets that each contain a set of questions
    and a set of targets.

    An Element is the basic unit of spreadsheet content. It consists of a cell's value,
    text color, and background color. Every element within an ElementSet is unique across
    all three of these characteristics. Each element may have multiple references.

    The routines create four ElementSets:
     - QuestionAttributes - text annotations of questions
     - TargetAttributes - text annotations of targets
     - Criteria - table data pertaining to criteria questions
     - Caveats - table data pertaining to caveat questions

    The routines construct

    The MSSP class itself

    """
    def read_monitoring(self, filepath, start=grid_start["Monitoring"]):
        M = xl.load_workbook(filepath)
        

    def __init__(self, version='default'):
        """
        Constructor.
        version number is a text string to indicate the source of the files.
        There should probably also be a directory specification- but that can
        be contextual.
        """
        self.version = version

        self.QuestionAttributes = entities.ElementSet()
        self.TargetAttributes = entities.ElementSet()
        self.Criteria = entities.ElementSet()
        self.Caveats = entities.ElementSet()
