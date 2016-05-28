"""
functions to pull target titles and categories from original spreadsheets
"""

from MSSP.mssp_work import *
from MSSP import MsspFromJson, write_to_json
from MSSP.utils import defaultdir, selectors
from MSSP.spreadsheet_data import SpreadsheetData
import openpyxl as xl
from openpyxl.utils import column_index_from_string
import os

json_dir = '/Users/brandon/Documents/GitHub/SNAP Fisheries Spreadsheets/json/2016-05-27a/'
out_dir = '/Users/brandon/Documents/GitHub/SNAP Fisheries Spreadsheets/json/2016-05-27b/'


def load_engine(gdir=json_dir):
    return MsspFromJson(gdir)


def save_engine(E, outdir=out_dir):
    write_to_json(E.serialize(), outdir=outdir)


target_titles = {
    'Monitoring':
        {
            'direction': 'row',
            'title': 'B',
            'category': 'D'
        },
    'Assessment':
        {
            'direction': 'column',
            'title': 36,
            'category': 34
        },
    'ControlRules':
        {
            'direction': 'column',
            'title': 4,
            'category': 3
        },
    'AssessmentIndices':
        {
            'direction': 'row',
            'title': 'F',
            'category': 'E'
        }
}



def open_sheet(sel):
    workbook = os.path.join(defaultdir, 'Working', MSSP_FILES[sel])
    w = xl.load_workbook(workbook)
    return w['Master']


def get_merged_cell(sheet, row, col):
    elt = SpreadsheetData._element_or_merged_range(sheet, row, col)
    return elt.text


def grab_value(sheet, reference, field='title'):
    sel = reference[0]
    if target_titles[sel]['direction'] == 'row':  # reference is (sel, (row, None))
        column = column_index_from_string(target_titles[sel][field])
        return get_merged_cell(sheet, row=reference[1][0], col=column)
    elif target_titles[sel]['direction'] == 'column':  # reference is (sel, (None, col))
        return get_merged_cell(sheet, row=target_titles[sel][field], col=reference[1][1])
    else:
        raise ValueError


def do_record_title_and_cat(E, sheet, rid, ref, record='target'):
    title = grab_value(sheet, ref, 'title')
    attr_t = E.find_or_create_attribute(title)
    E.set_title(rid, attr_t, record=record)

    category = grab_value(sheet, ref, 'category')
    attr_c = E.find_or_create_attribute(category)
    E.set_category(rid, attr_c, record=record)


def update_target_titles(E, sel):
    sheet = open_sheet(sel)
    tids = [tid for tid in E.targets_for(sel) if E._targets[tid].title is None]
    for tid in tids:
        ref = E._targets[tid].reference()
        do_record_title_and_cat(E, sheet, tid, ref)


def update_assessment_question_titles(E):
    """
    some ugly ass shit going on in here
    :param E:
    :return:
    """
    sheet = open_sheet('Assessment')
    qids = [k for k, q in enumerate(E._questions) if q is not None and q.title is None]
    for qid in qids:
        ref = [k for k in E._questions[qid].references if k[0] == 'Assessment']
        if len(ref) != 1:
            continue
        myref = ('AssessmentIndices', ref[0][1])

        do_record_title_and_cat(E, sheet, qid, myref, record='question')


def run_update():
    E = load_engine()
    for sel in selectors:
        update_target_titles(E, sel)

    update_assessment_question_titles(E)

    save_engine(E)
