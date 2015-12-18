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
from openpyxl.utils import range_boundaries
from .exceptions import *
from .records import Question, Target
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

        self.Questions = {}
        self.Targets = {}

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
    def cell_in_range(row, col, rng):
        """
        :param row: row index
        :param col: column index
        :param rng: a string describing a range
        :return:
        """
        rn_coords = range_boundaries(rng)
        return ((rn_coords[0] <= col <= rn_coords[2]) &
                (rn_coords[1] <= row <= rn_coords[3]))

    @staticmethod
    def _in_merged_range(sheet, row, col):
        """
        If ref is contained within a merged range on sheet, returns the element describing the range
        :param sheet:
        :param row:
        :param col:
        :return:
        """
        for rn in sheet.merged_cell_ranges:
            if MSSP.cell_in_range(row, col, rn):
                return elements.Element.from_worksheet(sheet, rn)

        return None

    @staticmethod
    def _attributes_of_column(sheet, start, col, element_set):
        """
        Returns a list of elements belonging to the attribute range of the column,
        including merged cells if applicable
        :param sheet:
        :param start:
        :param col:
        :param element_set: the ElementSet to which the attributes are added/indexed
        :return: a list of unique entries in the ElementSet, referred to in the column
        """
        last_row = start.row
        elts = []
        for row in range(1, last_row):
            try:
                elts.append(elements.Element(sheet.cell(None, row, col)))
            except EmptyInputError:
                # if empty, it may be part of a range
                elts.append(MSSP._in_merged_range(sheet, row, col))
                # Nones in the element list will get ignored by the ElementSet

        inds = element_set.add_elements(elts)
        return [element_set[i] for i in inds]

    @staticmethod
    def _attributes_of_row(sheet, start, row, element_set):
        """
        Returns a list of elements belonging to the attribute range of the row,
        including merged cells if applicable
        :param sheet:
        :param start:
        :param row:
        :param element_set: the ElementSet to which the attributes are added/indexed
        :return: a list of unique entries in the ElementSet, referred to in the row
        """
        last_col = start.col_idx
        elts = []
        for col in range(1, last_col):
            try:
                elts.append(elements.Element(sheet.cell(None, row, col)))
            except EmptyInputError:
                # if empty, it may be part of a range
                elts.append(MSSP._in_merged_range(sheet, row, col))
                # Nones in the element list will get ignored by the ElementSet

        inds = element_set.add_elements(elts)
        return [element_set[i] for i in inds]

    @staticmethod
    def _grid_elements(sheet, start, orient, element_set):
        """
        Returns a list of data elements for a given reference, given in orient
        :param sheet:
        :param start:
        :param orient:
        :param element_set: the ElementSet to which the data elements are added/indexed
        :return: (elts, mapping) where elts is a list of unique entries in the ElementSet, and
                 mapping is a list of (index, element) tuples
        """
        elts = []
        mapping = []
        if orient[0] is None:
            # column-spec
            for row in range(start.row, sheet.max_row+1):
                try:
                    elt = elements.Element(sheet.cell(None, row, orient[1]))
                except EmptyInputError: continue
                elts.append(elt)
                mapping.append(((row, None), elt))
        else:  # row-spec
            for col in range(start.col_idx, sheet.max_column+1):
                try:
                    elt = elements.Element(sheet.cell(None, orient[0], col))
                except EmptyInputError: continue
                elts.append(elt)
                mapping.append(((None, col), elt))

        inds = element_set.add_elements(elts)
        mapped_elts = [element_set[i] for i in inds]
        return mapped_elts, mapping

    def parse_file(self, sel, q_rows=True):
        """
        Method to parse the monitoring spreadsheet automagically.
        This function will add new entries to all four ElementSets

        First step: create new questions, each one having only QuestionAttributes
          - here we have to deal with the merging
        Second step: create new targets
          - here we have to deal with the merging
        Third step: read in Criteria from Criteria questions; associate
        Fourth step: read in

        :param sel:
        :param q_rows: whether questions are in rows (default) or columns
        :return:
        """
        if not self.check_sel(sel):
            raise BadSelectorError

        sheet = self._open_worksheet(sel)
        start = sheet[self.grid_start[sel]]  # a cell

        if q_rows is True:
            # There maybe a yet cleaner way to do this
            print "adding questions in rows"
            for row in range(start.row, sheet.max_row+1):
                mapped_attrs = self._attributes_of_row(sheet, start, row, self.QuestionAttributes)
                # create a new question with those attributes
                self.Questions[(sel, (row, None))] = Question(sel, (row, None), mapped_attrs)

            print "adding targets in columns"
            for col in range(start.col_idx, sheet.max_column+1):
                mapped_attrs = self._attributes_of_column(sheet, start, col, self.TargetAttributes)
                # create a new question with those attributes
                self.Targets[(sel, (None, col))] = Target(sel, (None, col), mapped_attrs)

            print "populating questions by row"
            for row in range(start.row, sheet.max_row+1):
                try:
                    q = self.Questions[(sel, (row, None))]
                except KeyError: continue
                if q.criterion is True:
                    # index all grid elements, add to Criteria ElementSet;
                    mapped_attrs, mappings = MSSP._grid_elements(sheet, start, q.orient, self.Criteria)
                else:
                    mapped_attrs, mappings = MSSP._grid_elements(sheet, start, q.orient, self.Caveats)

                q.encode(mapped_attrs, mappings)

                # now add cross-mappings to the targets
                for mapping in mappings:
                    try:
                        t = self.Targets[(sel, mapping[0])]
                    except KeyError: continue
                    t.add_mapping(((row, None), mapping[1]))

        else:
            print "adding questions in columns"
            for col in range(start.col_idx, sheet.max_column+1):
                mapped_attrs = self._attributes_of_column(sheet, start, col, self.QuestionAttributes)
                # create a new question with those attributes
                self.Questions[(sel, (None, col))] = Question(sel, (None, col), mapped_attrs)

            print "adding targets in rows"
            for row in range(start.row, sheet.max_row+1):
                mapped_attrs = self._attributes_of_row(sheet, start, row, self.TargetAttributes)
                # create a new target with those attributes
                self.Targets[(sel, (row, None))] = Target(sel, (row, None), mapped_attrs)

            print "populating questions by column"
            for col in range(start.col_idx, sheet.max_column+1):
                try:
                    q = self.Questions[(sel, (None, col))]
                except KeyError: continue

                # pre-populate valid_answers if specification is given in MSSP object
                # if self.valid_answers is not None:

                if q.criterion is True:
                    # index all grid elements, add to Criteria ElementSet;
                    mapped_attrs, mappings = MSSP._grid_elements(sheet, start, q.orient, self.Criteria)
                else:
                    mapped_attrs, mappings = MSSP._grid_elements(sheet, start, q.orient, self.Caveats)

                q.encode(mapped_attrs, mappings)

                # now add cross-mappings to the targets
                for mapping in mappings:
                    try:
                        t = self.Targets[(sel, mapping[0])]
                    except KeyError: continue
                    t.add_mapping(((None, col), mapping[1]))

        return True

    def parse_monitoring_sheet(self):
        """
        :return:
        """
        return self.parse_file('Monitoring', q_rows=False)
