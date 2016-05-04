"""
"Answerer" class
"""

from __future__ import print_function
from MSSP.utils import ifinput
from MSSP import selectors
from collections import defaultdict


def get_answer_value(valid_answers, cur=None):
    print('Valid Answers:')
    if all([isinstance(k, int) for k in valid_answers]):
        for k, v in enumerate(valid_answers):
            if k == cur:
                print('[%d]' % v)
            else:
                print(' %d ' % v)
        if cur is None:
            choice = int(raw_input('Enter a value: '))
        else:
            choice = int(ifinput('Enter a value: ', valid_answers[cur]))
        try:
            choice = [k for k, v in enumerate(valid_answers) if v == choice][0]
        except IndexError:
            return -1
    else:
        for k, v in enumerate(valid_answers):
            if k == cur:
                print('[%d: %s]' % (k+1, v))
            else:
                print(' %d: %s ' % (k+1, v))
        if cur is None:
            choice = int(raw_input('Select an answer 1-%d:' % len(valid_answers)))
        else:
            choice = int(ifinput('Select an answer 1-%d:' % len(valid_answers), cur+1))
        choice -= 1
    return choice


def get_selector():
    sel = None
    while sel not in selectors:
        print('What kind of target would you like to study?')
        for i in selectors:
            print('[%s]%s' % (i[0], i[1:]))
        choice = raw_input('Enter choice: ').lower()
        sels = [k for k in selectors if k[0].lower() == choice]
        if len(sels) == 1:
            sel=sels[0]
    return sel


class FisheryGuide(object):
    """
    A class for guiding a fishery manager to suitable targets by asking questions
    """

    def __init__(self, mssp_engine):
        self._engine = mssp_engine
        self._answers = dict()  # we want to use UUIDs someday
        self._qualifying_targets = dict()

    def answer(self, question):
        """
        Prompt the user with a given question an
        :param question:
        :return:
        """
        q = self._engine.questions(question)[0]
        if len(q.satisfied_by) > 0:
            print('Question %d is satisfied by others:' % question)
            for i in q.satisfied_by:
                if i not in self._answers:
                    self.answer(i)  # on satisfying questions, only prompt for missing q's
            self._answers[question] = max([self._answers[i] for i in q.satisfied_by])
            """
            note the 'SatisfiedBy' motif requires all satisfiers and the satisfied to have
            the same set + sequence of valid_answers. This has been verified manually but is not enforced
            structurally ....
            """

        elif len(q.valid_answers) == 1:
            self._answers[question] = 0
        else:
            choice = None
            self._engine.show(question=question)
            if question in self._answers:
                cur = self._answers[question]
            else:
                cur = None
            while choice not in range(len(q.valid_answers)):
                choice = get_answer_value(q.valid_answers, cur=cur)
                if choice not in range(len(q.valid_answers)):
                    print('Value out of range!')

            self._answers[question] = choice

        print('QuestionID %d: answered %s\n' % (question,
                                              q.valid_answers[self._answers[question]]))

    def my_answer(self, question, answer=None):
        if answer is None:
            return self._engine.questions(question)[0].valid_answers[self._answers[question]]
        else:
            return self._engine.questions(question)[0].valid_answers[answer]

    def show_qualifying_targets(self, sel):
        for i in self._qualifying_targets[sel]:
            self._engine.show(target=i)

    def show_non_qualifying_targets(self, sel):
        targets = set(self._engine.targets_for(sel)).difference(set(self._qualifying_targets[sel]))
        for i in targets:
            self._engine.show(target=i)
            print('Fails on:')
            cri = self._engine.criteria_for_target(i)
            for k, c in cri.iterrows():
                if c['Threshold'] > self._answers[c['QuestionID']]:
                    print('  Question ID %d [%s < %s]' % (c['QuestionID'], self.my_answer(c['QuestionID']),
                                                          self.my_answer(c['QuestionID'], c['Threshold'])))

    def score_target(self, target):
        self._engine.show(target=target)
        cavs = self._engine.caveats_for_target(target)
        scores = defaultdict(list)
        for i, k in cavs.iterrows():
            if k['Answer'] == self._answers[k['QuestionID']]:
                note, color = self._engine.note(k['NoteID'])
                scores[color].append('Question ID %d [%s]: %s' % (k['QuestionID'],
                                                                  self.my_answer(k['QuestionID']),
                                                                  note))
        for colors in scores:
            print('\n%s: %d notes' % (colors, len(scores[colors])))
            for n in scores[colors]:
                print('  %s' % n)

    def score_qualifying_targets(self, sel):
        for i in self._qualifying_targets[sel]:
            self.score_target(i)

    def filter(self, sel=None):
        if sel is None:
            sel = get_selector()
        qs = self._engine.criteria_for(sel)
        targets = set(self._engine.targets_for(sel))
        for q in qs:
            if q not in self._answers:
                self.answer(q)
            q_targets = set(self._engine.criteria(q, answer=self.my_answer(q)).index.tolist())
            targets = targets.intersection(q_targets)
        self._qualifying_targets[sel] = targets
        self.show_qualifying_targets(sel)

    def refine(self, sel=None):
        if sel is None:
            sel = get_selector()
        qs = self._engine.caveats_for(sel)
        for q in qs:
            if q not in self._answers:
                self.answer(q)
        self.score_qualifying_targets(sel)

    def save_answers(self):
        return {
            "answers": [{'QuestionID': k, 'Answer': v} for k, v in self._answers.items()]
        }

    def load_answers(self, json_in):
        for a in json_in['answers']:
            self._answers[int(a['QuestionID'])] = int(a['Answer'])



