from exceptions import *
from re import match
from os.path import expanduser
from datetime import datetime

from openpyxl.utils import column_index_from_string, get_column_letter

selectors = ('Monitoring', 'Assessment', 'ControlRules')

defaultdir = expanduser('~') + '/Dropbox/' + str(datetime.today().year) + '/TNCWebTool/'


def check_sel(sel):
    return sel in selectors

subject_regex = '^([MAC]).*:([A-Z]*)([0-9]*)$'


def convert_subject_to_reference(subject):
    """

    :param subject: matches subject_regex
    :return: (sel, record) dictionary key
    """
    g = match(subject_regex, subject)
    sel = [k for k in selectors if k[0] == g.groups()[0]]
    if len(sel) < 1:
        raise BadSelectorError
    sel = sel[0]

    if len(g.groups()[1]) > 0:
        # column ref
        record = (None, column_index_from_string(g.groups()[1]))
    elif len(g.groups()[2]) > 0:
        # row ref
        record = (int(g.groups()[2]), None)
    else:
        print "Regex did not match input string."
        record = (None, None)

    reference = (sel, record)
    return reference


def convert_reference_to_subject(reference):
    """

    :param reference: (sel, record)
    :return:
    """
    sel, record = reference
    suffix = ':'
    if record[0] is None:
        # col ref
        suffix += get_column_letter(record[1])
    elif record[1] is None:
        # row ref
        suffix += unicode(record[0])
    return sel + suffix


