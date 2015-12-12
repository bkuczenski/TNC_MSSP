"""
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

suggestion from Owen: use "factories" instead of a constructor

class Element(object):
    @classmethod
    def cell(cls, cell):
        ... checks from line 89 ...
        text = cell.value
        text_color = getattr(cell.font.color, cell.font.color.type)
        text_color_type = cell.font.color.type
        ... more attributes ...
        return cls(text, text_color, text_color_type, ...more attributes...)

    def __init__(self, text, text_color, text_color_type, ...)
        self.text = text
        self.text_color = text_color
        self.text_color_type = text_color_type

"""

# from openpyxl.cell.cell import Cell
from .exceptions import *
import re


class Element(object):
    """
    A decorated text string that appears in the spreadsheet
    """
    text = ''
    text_color = ''
    bg_color = ''
    ref = None

    @classmethod
    def from_worksheet(cls, worksheet, ref):
        if worksheet is None or ref is None:
            raise MsspError("Both worksheet+ref arguments required")

        if isinstance(ref, str):
            if ':' in ref:
                ref = re.split(':', ref)[0]
            cell = worksheet[ref]
        else:
            cell = worksheet.cell(None, ref[0], ref[1])

        return cls(cell)

    def __init__(self, cell=None):
        """
        Element() constructor accepts an openpyxl.cell.cell.Cell object and returns
        an Element.

        Use .from_worksheet(worksheet,ref) to create an Element by reference.

        :param cell: an openpyxl.cell.cell.Cell object
        :return: an Element
        """
        if isinstance(cell, Element):
            return cell

        if cell is None:
            raise MsspError("No cell input found")

        else:
            if cell.value == 'N/A':
                cell.value = None

            if cell.value is None:
                raise EmptyInputError

            self.text = cell.value
            self.text_color = getattr(cell.font.color, cell.font.color.type)
            # TODO: convert indexed colors to RGB-
            # probably in a special function in an openpyxl interfacing module

            # self.text_color_type = cell.font.color.type  # don't need this

            self.bg_color = getattr(cell.fill.bgColor, cell.fill.bgColor.type)
            # TODO: convert indexed colors to RGB-
            # probably in a special function in an openpyxl interfacing module

            self.ref = cell.parent.title + '!' + cell.column + str(cell.row)

    def __hash__(self):
        return hash((self.text, self.text_color, self.bg_color))

    def __eq__(self, other):
        return ((self.text == other.text) &
                (self.text_color == other.text_color) &
                (self.bg_color == other.bg_color))

    def __str__(self):
        return "%s: %s [text %s | fill %s]" % (self.ref, self.text, self.text_color, self.bg_color)

    def search(self, string):
        """
        returns true if string (regex) is found in self.text
        :param string: regex
        :return: bool
        """
        return bool(re.match(string, str(self.text), flags=re.IGNORECASE))


class ElementSet(object):
    """
    An ordered set of unique elements.
    Elements have __hash__ and __eq__ defined, which allows them to be used
    in dicts. This class accepts an element as input and returns its index in
    the ordered set, appending if it does not exist and doing a lookup if it
    does.
    """

    def _append(self, element):
        if element is None:
            return

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
        except EmptyInputError:
            # quit without errors if cell has no text
            return

        return self._append(element)

    def add_element(self, element):
        return self._append(element)

    def add_elements(self, elements):
        """
        :param elements: list of elements or Nones
        :return:
        """
        ind = []
        for element in elements:
            if element is not None:
                k = self._append(element)
                if k not in ind:
                    ind.append(k)
        return ind

    def __getitem__(self, item):
        """
        Lookup item by index
        :param item:
        :return:
        """
        return self.elements[item]

    def get_index(self, elt):
        """
        Lookup index by item
        :param elt:
        :return:
        """
        if isinstance(elt, Element):
            return self.index[elt]
        else:
            return self.index[Element(elt)]

    def __iter__(self):
        return iter(self.elements)

    def __len__(self):
        return len(self.elements)

    def __init__(self):
        self.index = dict()
        self.elements = list()
        self.refs = list()

    def __str__(self):
        st = ""
        for i in self.elements:
            st += str(i) + "\n"
        return st

    def search(self, string, idx):
        """
        Search the element set for a plain string or regex. returns a list of indices
        :param string:
        :return:
        """
        ind = []
        type(string)
        for elt in self.elements:
            if elt.search(string) is True:
                ind.append(self.index[elt])

        if idx is None:
            return ind

        return list(set(ind).intersection(idx))



