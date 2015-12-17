
# from mssp import MSSP
from .elements import Element


class Record(object):
    """
    A record is a spreadsheet row or column- either a question or a target.

    Common code goes here.

    A record has a selector, which is one of the valid MSSP.selectors;
    an orientation, which is either (None, x) for columns or (x, None) for rows;
    and a set of attributes, which are elements from the MSSP object's QuestionAttributes
    or TargetAttributes.

    Records can be populated with a lookup table of orient counterpart (i.e. the None in
    the orient tuple) which returns a member of a Criteria or Caveats EntitySet.

    In the case of questions, or at least criteria questions, that response can be
    compared with the question's answer value set to return an index into it.


    """

    @staticmethod
    def is_element_list(tup):
        return all(isinstance(i, Element) for i in tup)

    def __init__(self, sel, orient, attrs):
        """
        Create a record.
        :param sel: one of the valid MSSP.selectors
        :param orient: a 2-tuple indicating (None, x) for col or (x, None) for row
        :param attrs: a set of indices into the parent's QuestionAttributes ElementSet
        :return:
        """
        self.selector = sel
        self.orient = orient
        assert self.is_element_list(attrs), "Attributes argument must be a list of Elements"
        self.attrs = attrs


class Question(Record):
    """
    A Question is a column in M, or a row in A or C.

    In addition to the normal Record properties, a Question contains a collection of
    valid answer values, and a flag indicating whether the question is a 'Criterion'
    or 'Caveat' question.

    Questions have a lookup table of orient counterpart -> answer value, which can be
    used to index into a complementary set of targets in the MSSP object.


    """

    def __init__(self, *args, **kwargs):
        super(Question, self).__init__(*args, **kwargs)

        self.criterion = any(i.search('criteri') for i in self.attrs)


class Target(Record):
    """
    A Target is a row in M, or a column in A or C.

    In addition to the normal Record properties, a Target doesn't have anything at present.

    Targets have a lookup table of orient counterpart ->
    """

    def __init__(self, *args, **kwargs):
        super(Target, self).__init__(*args, **kwargs)


