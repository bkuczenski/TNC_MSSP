"""
Working script file for MSSP work.
As functions are formalized, the plan is to remove them from here and
put them into classes.

Other aspects, like the lists of active spreadsheet files, can live
here permanently.
"""

import os
import openpyxl as xl

WORKING_DIR = os.path.expanduser('~') + '/Dropbox/2015/TNCWebTool/Working/'

MSSP_FILES = {
    'Assessment': 'MSSP Assessment_OCT28 2015.xlsx',
    'ControlRules': 'MSSP Harvest Control Rules_OCT28 2015.xlsx',
    'Monitoring': 'MSSP Monitoring_OCT28 2015.xlsx',
}

M = xl.load_workbook(WORKING_DIR + MSSP_FILES['Monitoring'])

# find the number of nonempty cells in a given row?
def num_cells(worksheet, row):
    pass


def compare(cell1, cell2):
    for attr in cell1.__slots__:
        if getattr(cell1,attr) != getattr(cell2,attr):
            print "Attribute: {}".format(attr)
            print " C1: {}".format(getattr(cell1,attr))
            print " C2: {}".format(getattr(cell2,attr))
            print " "



