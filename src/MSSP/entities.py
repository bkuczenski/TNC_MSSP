'''
Created on Oct 28, 2015

@author: brandon

Entity classes defined here

Element: any text appearing in the spreadsheet. abstract.
to be continued.  Properties include text string, text color, background color (both of which should be RGBs)

Element has __hash__ and __eq__

ElementSet: a collection of elements with a uniqueness condition.  No two Elements in an ElementSet may be
equal in all three fields.

Each MSSP class instance contains two different ElementSets: Attributes (derived from spreadsheet header
content) and Flags (derived from spreadsheet data content).  Possibly these should be per-spreadsheet, but at the
moment I can't think of any good reason why they would need to be.

The first step in populating an MSSP instance is to generate its ElementSets.

OK- attribute is just a list() that overrides append() to check uniqueness

Item: contains a spreadsheet reference ( sheet, row, column )
where either row or column is None
and a list of Attributes

Question: is an Item with an Answer Set

Target: is an Item with a TargetType (Monitoring, Assessment, ControlRule)

The second step in populating an MSSP instance is to generate a



 * Questions
   - have user prompts
   - have valid answer sets
   
 * Monitoring

'''

from openpyxl.cell.cell import Cell


class MsspError(Exception):
    pass


class EmptyCellError(MsspError):
    pass


class Element(object):
    """
    A decorated text string that appears in the spreadsheet
    """
    text = ''
    text_color = ''
    bg_color = ''
    ref = None

    def __init__(self, cell=None, worksheet=None, ref=None):
        """
        Element() constructor accepts two types of inputs:
         -- an openpyxl.cell.cell.Cell object (cell=cell)
         -- an openpyxl.worksheet.worksheet.Worksheet object and a cell reference
            (worksheet=worksheet, ref=ref)
            The 'ref' can either be a string or a (row,column) tuple
        If the user passes both a cell and a worksheet+ref, the cell wins.

        For now, everything is done using kwargs- why bother with implicit positional
        arg parsing?

        :param cell:
        :return:
        """
        if cell is None:
            if worksheet is None or ref is None:
                raise MsspError("Either cell or worksheet+ref arguments required")

            if isinstance(ref,str):
                cell = worksheet[ref]
            else:
                cell=worksheet.cell(None, ref[0], ref[1])

        if cell is not None:
            if cell.value is None:
                raise EmptyCellError

            self.text = cell.value
            self.text_color = getattr(cell.font.color, cell.font.color.type)
            self.text_color_type = cell.font.color.type

            self.bg_color = getattr(cell.fill.bgColor, cell.fill.bgColor.type)

            self.ref = cell.parent.title + '!' + cell.column + str(cell.row)

        else:
            raise MsspError("No cell input found")

    def __hash__(self):
        return hash((self.text, self.text_color, self.bg_color))

    def __eq__(self, other):
        return ((self.text == other.text) &
                (self.text_color == other.text_color) &
                (self.bg_color == other.bg_color))

    def __str__(self):
        return "%s: %s [text %s | fill %s]" % (self.ref,self.text, self.text_color, self.bg_color)

    # self is not allowed to be empty- that throws an exception
    # def isempty(self):
    #     return self.text is None


class ElementSet(object):
    """
    An ordered set of unique elements.
    Elements have __hash__ and __eq__ defined, which allows them to be used
    in sets. This class accepts an element as input and returns its index in
    the ordered set, appending if it does not exist and doing a lookup if it
    does.
    """

    index = dict()
    elements = list()
    refs = list()

    def _append(self, element):
        if element in self.index:
            k = self.index[element]
            if element.ref not in self.refs[k]:
                self.refs[k].append(element.ref)
        else:
            self.index[element] = len(self.elements)  # the element's index
            self.elements.append(element)    # the element
            self.refs.append([element.ref])  # a list of cell references

        return self.index[element]

    def add(self, *args, **kwargs):
        try:
            element = Element(*args, **kwargs)
        except EmptyCellError:
            # quit without errors if cell has no text
            return

        self._append(element)

    def add_element(self, element):
        self._append(element)

    def __getitem__(self, item):
        return self.elements[item]




