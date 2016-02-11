"""
Working script file for MSSP work.
As functions are formalized, the plan is to remove them from here and
put them into classes.

Other aspects, like the lists of active spreadsheet files, can live
here permanently.

Questions / Policies for TNC personnel:

 1- CAVEAT questions: are they all yes/no?
 2- CAVEAT questions: do the caveats for a given question all apply to the same SENSE of the question?
 3- Assessment worksheet: M

"""

import openpyxl as xl

from os.path import expanduser
from datetime import datetime

from openpyxl.styles.colors import COLOR_INDEX

VERSIONS = {
    'January': {
        'files': {
            'Assessment': 'MSSP Assessment_NOV 2015.xlsx',
            'ControlRules': 'MSSP Harvest Control Rules_NOV 2015_fixed.xlsx',
            'Monitoring': 'MSSP Monitoring_OCT28 2015.xlsx'
            },
        'grid_start': {
            "Monitoring": 'F8',
            "Assessment": 'G40',
            "ControlRules": 'E9'
            },
        'answer_senses': {
            "Monitoring": (7, None),
            "Assessment": (None, 2),
            "ControlRules": (None, 4)
        }
    },
    'February': {
        'files': {
            'Assessment': 'MSSP Assessment_JAN 2016.xlsx',
            'ControlRules': 'MSSP Harvest Control Rules_JAN 2016_fixed.xlsx',
            'Monitoring': 'MSSP Monitoring_JAN 2016.xlsx'
            },
        'grid_start': {
            "Monitoring": 'F8',
            "Assessment": 'G40',
            "ControlRules": 'E9'
            },
        'answer_senses': {
            "Monitoring": (7, None),
            "Assessment": (None, 2),
            "ControlRules": (None, 4)
        }
    }
}

Version = 'February'

QUESTION_MAP = 'QuestionsAndColors.xlsx'

MSSP_FILES = VERSIONS[Version]['files']
grid_start = VERSIONS[Version]['grid_start']
answer_senses = VERSIONS[Version]['answer_senses']

working_dir = expanduser('~') + '/Dropbox/' + str(datetime.today().year) + '/TNCWebTool/'


# get color specification
def get_real_color(color_obj, workbook=None):
    if color_obj.type == 'rgb':
        return color_obj.rgb
    elif color_obj.type == 'indexed':
        if workbook is None:
            raise Exception("indexed type and workbook not defined")
        else:
            return COLOR_INDEX[color_obj.indexed]
    else:
        raise NotImplementedError("color type {0} not supported".format(color_obj.type))


def compare(cell1, cell2):
    for attr in cell1.__slots__:
        if getattr(cell1,attr) != getattr(cell2,attr):
            print "Attribute: {}".format(attr)
            print " C1: {}".format(getattr(cell1,attr))
            print " C2: {}".format(getattr(cell2,attr))
            print " "

