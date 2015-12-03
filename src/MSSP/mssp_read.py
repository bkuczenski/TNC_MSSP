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

grid_start = {"Monitoring":'F8',
              "Assessment":'D37',
              "ControlRules":'E9'}

default_MSSP_FILES = {
    'Assessment': 'MSSP Assessment_OCT28 2015.xlsx',
    'ControlRules': 'MSSP Harvest Control Rules_OCT28 2015.xlsx',
    'Monitoring': 'MSSP Monitoring_OCT28 2015.xlsx',
}

class MSSPFile(object):
    def __init__(self, files=default_MSSP_FILES,)


class MSSPSet(object):
    '''
    classdocs
    '''
    def read_monitoring(self, filepath, start=grid_start["Monitoring"]):
        M = xl.load_workbook(filepath)
        

    def __init__(self, version='default'):
        '''
        Constructor.
        version number is a text string to indicate the source of the files.
        There should probably also be a directory specification- but that can
        be contextual.
        
        '''
        self.version = version

