
from MSSP.utils import convert_subject_to_reference, convert_record_to_label

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
        self.valid_answers = []  # this gets constructed from _yes_no_included and _external_answers
        self._external_answers = []
        self._yes_no_included = False
        self.satisfied_by = set()
        self.satisfies = set()  # not serialized

    def _update_valid_answers(self):
        """
        Construct self.valid_answers based on object content
        :return: none
        """
        if self._yes_no_included:
            self.valid_answers = ['No', 'Yes']
        else:
            self.valid_answers = []

        self.valid_answers.extend(self._external_answers)

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

        # handle new incoming answers
        new_answers = question.valid_answers.keys()
        useful_answers = []

        for ans in new_answers:
            if is_yes_or_no(ans):
                self._yes_no_included = True
            else:
                useful_answers.append(ans)

        if len(useful_answers) > 0:  # add new useful answers to the object (in the order encountered)
            for ans in useful_answers:
                if ans not in self._external_answers:
                    self._external_answers.append(ans)

        # reconstruct valid_answers
        self._update_valid_answers()

        # handle satisfied_by
        for ref in question.satisfied_by:
            self.satisfied_by.add(q_dict[ref])  # add index into question enum

    def merge(self, other):
        """
        Assume
        :param other:
        :return:
        """
        if self is other:
            return
        if self.valid_answers != other.valid_answers:
            print('Answers do not match. not merging.')
            return
        self.references.extend(other.references)
        [self.satisfied_by.add(k) for k in other.satisfied_by]
        [self.satisfies.add(k) for k in other.satisfies]

    @classmethod
    def from_json(cls, question):
        """

        :param question:
        :return:
        """
        mssp_question = cls()
        for r in question['References']:
            mssp_question.references.append(convert_subject_to_reference(r))

        for ans in question['ValidAnswers']:
            if is_yes_or_no(ans):
                mssp_question._yes_no_included = True
            else:
                if ans not in mssp_question._external_answers:
                    mssp_question._external_answers.append(ans)

        mssp_question._update_valid_answers()

        if 'SatisfiedBy' in question:
            mssp_question.satisfied_by = set(question['SatisfiedBy'])

        return mssp_question

    def label(self):
        return ', '.join(sorted([k + ' ' + convert_record_to_label(l) for k, l in self.references]))

    def __str__(self):
        return ' References: {0}\nValid Answers: {1}\n Satisfied By: {2}\n Satisfies: {3}'.format(
            self.label(),
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

    def label(self):
        return self.type + ' ' + convert_record_to_label(self.record)

    def reference(self):
        return self.type, self.record

    def references(self):
        return [self.reference()]

    def __str__(self):
        return ' Reference: {0}'.format(self.label())


