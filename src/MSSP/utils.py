from exceptions import *
from re import match

from openpyxl.utils import column_index_from_string

selectors = ('Monitoring', 'Assessment', 'ControlRules')


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

    if len(g.groups()[2]) > 0:
        # row ref
        record = (int(g.groups()[2]), None)

    reference = (sel, record)
    return reference

