from mssp import MSSP

class Question(object):
    """
    A Question is a column in M, or a row in A or C. A question contains a collection of
    QuestionAttributes, a set of valid answer values, and a type which is either 'Criterion'
    or 'Caveat'.

    Current open question: relation between MSSP class and Question class.  An MSSP has a
    set of Questions as an attribute- but the Questions also need to know about the MSSP
    QuestionAttributes.
    """

    @classmethod
    def by_columns(cls, mssp, sel, col, attrs):
        """
        Create a question entity from a set of attributes read from a column
        :param sel:
        :param col:
        :param attrs:
        :return:
        """
        return cls(mssp, sel, (None, col), attrs)

    def __init__(self, mssp, sel, orient, attrs):
        """
        Create a question.
        :param sel: one of the valid MSSP.selectors
        :param orient: a 2-tuple indicating (None, x) for col or (x, None) for row
        :param attrs: a set of indices into the parent's QuestionAttributes ElementSet
        :return:
        """
        self.mssp = mssp
        self.selector = sel
        self.orient = orient
        self.attrs = attrs
        self.criterion = False

        if len(self.mssp.QuestionAttributes.search('criteri', self.attrs)) > 0:
            self.criterion = True

