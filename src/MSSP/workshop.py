"""
Collection of scripts for processing changes from the 4/26-4/28 workshop

Tasks:
 - update attributes based on ROCK_CRAB_TEMPLATE etc spreadsheet (column-in, column-out, from row to row)
 - add titles and categories to questions, based on etc spreadsheet
  = create if does not exist
 - set target titles and categories by specifying row/column of input spreadsheets
"""
from __future__ import print_function, unicode_literals

from MSSP.utils import defaultdir  #, selectors, check_sel
from MSSP import MsspFromJson
from MSSP.json_exch import write_json
import openpyxl as xl
from openpyxl.utils import column_index_from_string
import os

Q_SHEET = 'FINAL Copy of Rock Crab Copy of FishPath_Scoring_TEMPLATE.xlsx'

json_dir = '/Users/brandon/Documents/GitHub/SNAP Fisheries Spreadsheets/json/2016-05-27/'
out_dir = '/Users/brandon/Documents/GitHub/SNAP Fisheries Spreadsheets/json/2016-05-27a/'


def update_attr(E, old_text, new_text):
    if old_text is None:
        attr = E.find_or_create_attribute(new_text)
    else:
        first_attempt = E.find_attribute(old_text)
        if len(first_attempt) == 1:
            attr = E.find_or_create_attribute(old_text)
            try:
                E.update_attribute(attr, new_text)
            except KeyError:
                print('blerg %s | %s' % (attr, new_text))
        else:
            attr = E.find_or_create_attribute(new_text)
    return attr


workshop_sel = {
    'Monitoring':
        {
            'sheet': 'Monitoring',
            'title': 'C',
            'newtitle': 'L',
            'category': 'B',
            'extras': ['A', 'D', 'I', 'J', 'K'],
            'hint': 'M',
            'rows': range(7, 44)
        },
    'Assessment':
        {
            'sheet': 'Assessment',
            'title': 'P',
            'newtitle': 'W',
            'extras': ['O', 'Q', 'V'],
            'hint': 'X',
            'rows': range(9, 37)
        },
    'ControlRules':
        {
            'sheet': 'Decision Rules',
            'title': 'C',
            'newtitle': 'K',
            'category': 'B',
            'extras': ['A', 'D', 'I', 'J'],
            'hint': 'M',
            'rows': range(7, 59)
        }
}


def open_wk_sheet(sel):
    w = xl.load_workbook(os.path.join(defaultdir, Q_SHEET))
    return w[workshop_sel[sel]['sheet']]


def get_cell(sheet, row, col):
    return sheet.cell(row=row, column=column_index_from_string(col)).value


def check_questions_on_sheet(E, sel, rows=None):
    """

    :param sel:
    :param rows:
    :return:
    """
    if rows is None:
        rows = workshop_sel[sel]['rows']
    elif isinstance(rows, int):
        rows = [rows]

    sheet = open_wk_sheet(sel)

    for row in rows:
        print('update title string')
        title = update_attr(E,
                            get_cell(sheet, row, workshop_sel[sel]['title']),
                            get_cell(sheet, row, workshop_sel[sel]['newtitle']))

        print('Find question ID')
        q = E.questions_with_attribute(title)

        if len(q) != 1:
            hint = get_cell(sheet, row, workshop_sel[sel]['hint'])
            if hint is None:
                print('%s row %d: Found %d matches; cannot isolate question ID' % (sel, row, len(q)))
                continue
            else:
                qid = int(hint)
        else:
            qid = q[0]

        if E._questions[qid].title is None:
            print('set title')
            E.set_title(qid, title)

        if 'category' in workshop_sel[sel]:
            if E._questions[qid].category is None:
                print('set category')
                E.set_category(qid, E.find_or_create_attribute(get_cell(sheet, row, workshop_sel[sel]['category'])))

        print('add extras')
        for col in workshop_sel[sel]['extras']:
            attr = E.find_or_create_attribute(get_cell(sheet, row, col))
            E.add_attribute_mapping(qid, attr)



def run_update(*args):
    E = load_engine()
    check_questions_on_sheet(E, *args)
    save_engine(E)


def load_engine(gdir=json_dir):
    return MsspFromJson(gdir)


def save_engine(E, outdir=out_dir):
    write_json(E.serialize(), outdir=outdir)
