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
from openpyxl.utils import range_boundaries, coordinate_from_string
from .exceptions import *
import elements
import mssp_work

from os.path import expanduser
from datetime import datetime


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

    selectors = ('Monitoring', 'Assessment', 'ControlRules')

    @staticmethod
    def check_sel(sel):
        return sel in MSSP.selectors

    def _open_worksheet(self, sel):
        if self.check_sel(sel):
            x = xl.load_workbook(self.working_dir + self.files[sel])
            if 'Master' in x.get_sheet_names():
                return x['Master']
            else:
                return x.active

    def __init__(self, version='default', workdir=None,
                 files=mssp_work.MSSP_FILES, grid_start=mssp_work.grid_start, valid_answers=None):
        """
        Constructor.
        Creates an MSSP object which can be used as a base to perform read-in functions.

        Input kwargs:
         version string - maybe to be used later
         workdir - working directory (default '~/Dropbox/YYYY/TNCWebTool/Working')
         files - dictionary maps selector strings to excel files
         grid_start - dictionary maps selector strings to cell references- top-left of data region
         valid_answers - dictionary maps selector strings to row/column reference with valid answer set

         files and grid_start are required; valid_answers can be None

         These variables should be defined in the script that calls the constructor

        """
        self.version = version

        self.QuestionAttributes = elements.ElementSet()
        self.TargetAttributes = elements.ElementSet()
        self.Criteria = elements.ElementSet()
        self.Caveats = elements.ElementSet()

        self.Questions = []
        self.Targets = []

        if workdir is None:
            self.working_dir = expanduser('~') + '/Dropbox/' + str(datetime.today().year) + '/TNCWebTool/Working/'
        else:
            self.working_dir = workdir

        if files is None:
            raise EmptyInputError("Please supply dictionary of MSSP files.")

        self.files = files

        if grid_start is None:
            raise EmptyInputError("Please supply dictionary of grid starting cells.")

        self.grid_start = grid_start

        self.valid_answers = valid_answers  # this one is ok to be None

    @staticmethod
    def _find_row_attributes(sheet, start):
        """
        returns a list of Elements in the row-attribute region of a spreadsheet
        :param sheet: the output of _open_worksheet
        :param sel: selector string
        :return:
        """
        last_col = sheet[start].col_idx
        first_row = sheet[start].row
        last_row = sheet.max_row

        elts=[]
        for col in range(1, last_col):
            for row in range(first_row, last_row+1):
                try:
                    elts.append(elements.Element(sheet.cell(None, row, col)))
                except EmptyInputError:
                    pass

        return elts

    @staticmethod
    def _find_column_attributes(sheet, start):
        """
        returns a list of Elements in the column-attribute region of a spreadsheet

        :param sheet:
        :param sel:
        :return:
        """
        last_row = sheet[start].row
        first_col = sheet[start].col_idx
        last_col = sheet.max_column

        elts = []
        for col in range(first_col, last_col):
            for row in range(1, last_row):
                try:
                    elts.append(elements.Element(sheet.cell(None, row, col)))
                except EmptyInputError:
                    pass

        return elts

    @staticmethod
    def cell_in_range(row, col, range):
        """
        :param row: row index
        :param col: column index
        :param range: a string describing a range
        :return:
        """
        rn_coords = range_boundaries(range)
        return ((rn_coords[0] <= col <= rn_coords[2]) &
                (rn_coords[1] <= row <= rn_coords[3]))

    def _in_merged_range(self, sheet, row, col):
        """
        If ref is contained within a merged range on sheet, returns the element describing the range
        :param sheet:
        :param ref:
        :return:
        """
        for rn in sheet.merged_cell_ranges:
            if self.cell_in_range(row, col, rn):
                return elements.Element.from_worksheet(sheet, rn)

        return None

    def _attributes_of_column(self, sheet, start, col):
        """
        Returns a list of elements belonging to the attribute range of the column,
        including merged cells if applicable
        :param sheet:
        :param start:
        :param col:
        :return:
        """
        last_row = start.row
        elts = []
        for row in range(1, last_row):
            try:
                elts.append(elements.Element(sheet.cell(None, row, col)))
            except EmptyInputError:
                # if empty, it may be part of a range
                elts.append(self._in_merged_range(sheet, row, col))
                # Nones in the element list will get ignored by the ElementSet
        return elts

    def _attributes_of_row(self, sheet, start, row):
        """
        Returns a list of elements belonging to the attribute range of the column,
        including merged cells if applicable
        :param sheet:
        :param start:
        :param col:
        :return:
        """
        last_col = start.col_idx
        elts = []
        for col in range(1, last_col):
            try:
                elts.append(elements.Element(sheet.cell(None, row, col)))
            except EmptyInputError:
                # if empty, it may be part of a range
                elts.append(self._in_merged_range(sheet, row, col))
                # Nones in the element list will get ignored by the ElementSet
        return elts

    def parse_file(self, sel, q_rows=True):
        """
        Method to parse the monitoring spreadsheet automagically.
        This function will add new entries to all four ElementSets

        First step: create new questions, each one having only QuestionAttributes
          - here we have to deal with the merging
        Third step: create new targets
          - here we have to deal with the merging
        Fourth step: determine which questions are criteria via text-mining
        Fifth step: read in Criteria and Caveats
        Sixth step: populate elements
          - Criteria questions get tagged with criteria
          - Targets get tagged with Caveats

        :param sel:
        :param q_rows: whether questions are in rows (default) or columns
        :return:
        """
        if not self.check_sel(sel):
            raise BadSelectorError

        sheet = self._open_worksheet(sel)
        start = sheet[self.grid_start[sel]]  # a cell

        """
        if q_rows is True:  # questions in rows [Assessment, ControlRules]
            print "adding questions in rows"
            for elt in self._find_row_attributes(sheet, start):
                self.QuestionAttributes.add_element(elt)
            for elt in self._find_column_attributes(sheet, start):
                self.TargetAttributes.add_element(elt)

        else:  # questions in columns [Monitoring]
        """
        if q_rows is False:
            print "adding questions in columns"
            for col in range(start.col_idx, sheet.max_column+1):
                q_attrs = self._attributes_of_column(sheet, start, col)

                # register the attributes we find
                q_inds = self.QuestionAttributes.add_elements(q_attrs)

                # create a new question with those attributes
                self.Questions.append(question.Question.by_column(sel, col, q_inds))

            for elt in self._find_row_attributes(sheet, start):
                self.TargetAttributes.add_element(elt)
            for elt in self._find_column_attributes(sheet, start):
                self.QuestionAttributes.add_element(elt)

            # now create new questions, one for each column, and assign all relevant attributes




        return True

    def parse_monitoring_sheet(self):
        """
        :return:
        """
        return self.parse_file('Monitoring', q_rows=False)
