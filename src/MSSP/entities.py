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


class Element(object):
    """
    A decorated text string that appears in the spreadsheet
    """
    text = ''
    text_color = ''
    bg_color = ''

    def __init__(self, cell=None):
        if cell is not None:
            self.text = cell.value
            self.text_color = getattr(cell.font.color, cell.font.color.type)
            self.text_color_type = cell.font.color.type
            self.bg_color = getattr(cell.fill.fg)