
from MSSP.utils import convert_subject_to_reference

def is_yes(answer):
    return answer in ('y', 'Y', 'yes', 'YES', 'Yes', 'if yes', 'if Yes', 'if YES', 'IF YES')


def is_no(answer):
    return answer in ('n', 'N', 'no', 'NO', 'No', 'if no', 'if No', 'if NO', 'IF NO', 'if not', 'if Not')


def is_yes_or_no(answer):
    return is_yes(answer) | is_no(answer)


def cast_answer(text):
    if is_yes(text):
        return 'Yes'
    elif is_no(text):
        return 'No'
    else:
        return text


class MsspQuestion(object):
    """
    An MsspQuestion is an aggregation that represents one or more spreadsheet questions.

    """
    def __init__(self):
        """
        Create an MsspQuestion from an existing
        :return: an empty MsspQuestion
        """
        self.references = []
        self.valid_answers = ['No', 'Yes']
        self.default_answers = True
        self.satisfied_by = set()
        self.satisfies = set()  # not serialized

    def append(self, question, q_dict):
        """
        Add contents of a Question object to the MsspQuestion.  If Question's valid answers are non-meaningless,
        replace default answers with import answers, or merge with non-default answers.
        :param question: a MSSP.records.Question object
        :param q_dict: a mapping of spreadsheet refs into question enum
        :return: none
        """
        # handle reference
        self.references.append((question.selector, question.record))

        # handle valid answers
        valid_answers = question.valid_answers.keys()
        useful_answers = []
        for i in range(len(valid_answers)):
            if is_yes(valid_answers[i]):
                useful_answers.append('Yes')
            elif is_no(valid_answers[i]):
                useful_answers.append('No')
            else:
                useful_answers.append(valid_answers[i])

        if len(useful_answers) > 0:
            if self.default_answers:
                # replace default answers with useful answers
                self.valid_answers = useful_answers
                self.default_answers = False
            else:
                # add supplied answers to existing answers
                for item in useful_answers:
                    if item not in self.valid_answers:
                        self.valid_answers.append(item)

        # handle satisfied_by
        for ref in question.satisfied_by:
            self.satisfied_by.add(q_dict[ref])  # add index into question enum

    @classmethod
    def from_json(cls, question):
        """

        :param question:
        :return:
        """
        mssp_question = cls()
        for r in question['References']:
            mssp_question.references.append(convert_subject_to_reference(r))
        mssp_question.valid_answers = question['ValidAnswers']
        if (len(mssp_question.valid_answers) == 2 &
            all([not is_yes_or_no(k) for k in mssp_question.valid_answers])):
            mssp_question.default_answers = True
            mssp_question.valid_answers = ['No','Yes']
        else:
            mssp_question.default_answers = False
        if 'SatisfiedBy' in question:
            mssp_question.satisfied_by = set(question['SatisfiedBy'])

        return mssp_question

    def __str__(self):
        return ' Valid Answers: {0}\n Satisfied By: {1}\n Satisfies: {2}'.format(
            self.valid_answers,
            (None, list(self.satisfied_by))[len(self.satisfied_by) > 0],
            (None, list(self.satisfies))[len(self.satisfies) > 0 ]
        )


class MsspTarget(object):
    def __init__(self, target):
        """

        :param target:
        :return:
        """
        self.type = target.selector
        self.record = target.record

    @classmethod
    def from_json(cls, target):
        from MSSP.records import Record

        # ref is sel, record
        ref = convert_subject_to_reference(target['Reference'])

        t = Record(ref[0], ref[1], [])
        return cls(t)

    def reference(self):
        return self.type, self.record

    def references(self):
        return [self.reference()]

    def __str__(self):
        return ' Reference: {0}'.format(self.reference())


