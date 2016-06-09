"""
"Answerer" class
"""

from __future__ import print_function
from MSSP.utils import ifinput, defaultdir
from MSSP import selectors
from collections import defaultdict
import os
import json


default_file = 'fishery_guide_answers.json'


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
            sel = sels[0]
    return sel


class FisheryGuide(object):
    """
    A class for guiding a fishery manager to suitable targets by asking questions
    """
    def name(self):
        return os.path.splitext(os.path.basename(self._filename))[0]

    def get_abs_path(self, filename):
        if filename is None:
            filename = self._filename
        elif not os.path.isabs(filename):
            filename = os.path.join(defaultdir, filename)
        if os.path.isdir(filename):
            filename = os.path.join(filename, default_file)
        return os.path.normpath(filename)

    def __init__(self, mssp_engine, filename=None):
        self._engine = mssp_engine
        self._answers = dict()  # we want to use UUIDs someday
        self._qualifying_targets = dict()

        if filename is None:
            filename = defaultdir
        self._filename = self.get_abs_path(filename)

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
            if question in self._answers:
                return self._engine.questions(question)[0].valid_answers[self._answers[question]]
            else:
                return '--'
        else:
            return self._engine.questions(question)[0].valid_answers[answer]

    def show_answers(self, sel=None):
        if sel is None:
            for k in ('Monitoring', 'Assessment', 'ControlRules'):
                self.show_answers(sel=k)
        else:
            print(sel)
            print('Criteria:')
            for q in self._engine.criteria_for(sel):
                print('Question ID %3d: %-30.30s "%s"' % (q, self.my_answer(q), self._engine.title(question=q)))
            print('\nCaveats:')
            for q in self._engine.caveats_for(sel):
                print('Question ID %3d: %-30.30s "%s"' % (q, self.my_answer(q), self._engine.title(question=q)))

    def print_target_criteria(self, criteria):
        for c in criteria:
            if c['Pass']:
                print(' pass  - Question ID %3d [%s >= %s]' % (c['QuestionID'], self.my_answer(c['QuestionID']),
                      c['Threshold']))
            else:
                print('(FAIL) - Question ID %3d [%s < %s]' % (c['QuestionID'], self.my_answer(c['QuestionID']),
                      c['Threshold']))

    def qualify_target(self, target):
        """

        :param target:
        :return: a list of dicts for criteria, with keys: 'QuestionID', 'Answer', 'Threshold', 'Pass'
        """
        cri = self._engine.criteria_for_target(target)
        criteria = []
        for i, k in cri.iterrows():
            criteria.append({'QuestionID': k['QuestionID'],
                             'Answer': self.my_answer(k['QuestionID']),
                             'Threshold': self.my_answer(k['QuestionID'], answer=k['Threshold']),
                             'Pass': bool(self._answers[k['QuestionID']] >= k['Threshold'])})
        return criteria

    @staticmethod
    def print_target_score(scores):
        """

        :param scores: a dict of color keys containing lists of 'QuestionID', 'Answer', 'Note' dicts
        :return:
        """
        for color in scores:
            print('\n[* %s *]: %d notes' % (color, len(scores[color])))
            for n in scores[color]:
                print('   Question ID %d [%s]: %s' % (n['QuestionID'],
                                                      n['Answer'],
                                                      n['Note']))

    def score_target(self, target):
        """

        :param target:
        :return: a dict of color keys containing lists of dicts for notes having that color, with keys
         'QuestionID', 'Answer', 'Note'
        """
        cavs = self._engine.caveats_for_target(target)
        scores = defaultdict(list)
        for i, k in cavs.iterrows():
            if k['Answer'] == self._answers[k['QuestionID']]:
                note, color = self._engine.note(k['NoteID'])
                scores[color].append({'QuestionID': k['QuestionID'],
                                      'Answer': self.my_answer(k['QuestionID']),
                                      'Note': note})
        return dict(scores)

    def _nonqualifying_targets(self, sel):
        if sel not in self._qualifying_targets:
            self.filter(sel)
        return set(self._engine.targets_for(sel)).difference(set(self._qualifying_targets[sel]))

    @staticmethod
    def _score_profile(scores):
        score = 0
        if 'green' in scores:
            score += len(scores['green'])
        if 'orange' in scores:
            score -= len(scores['orange'])
        if 'yellow' in scores:
            score -= len(scores['yellow'])
        if 'red' in scores:
            score -= 10*len(scores['red'])
        return score

    def _profile(self, target):
        profile = dict(TargetID=target, Title=self._engine.title(target=target))
        profile['Criteria'] = sorted(self.qualify_target(target), key=lambda k: k['QuestionID'])
        profile['Pass'] = bool(all([x['Pass'] for x in profile['Criteria']]))
        if profile['Pass']:
            profile['Caveats'] = self.score_target(target)
            profile['Score'] = self._score_profile(profile['Caveats'])
        return profile

    def score_qualifying_targets(self, sel):
        scores = []
        if sel not in self._qualifying_targets:
            self.filter(sel)
        for i in self._qualifying_targets[sel]:
            scores.append(self._profile(i))
        return sorted(scores, key=lambda x: x['Score'])

    def score_nonqualifying_targets(self, sel):
        scores = []
        for i in self._nonqualifying_targets(sel):
            scores.append(self._profile(i))
        return scores

    def filter(self, sel=None):
        """

        :param sel:
        :return:
        """
        if sel is None:
            sel = get_selector()
        qs = self._engine.criteria_for(sel)
        targets = set(self._engine.targets_for(sel))
        for q in qs:
            if q not in self._answers:
                self.answer(q)
            t_pass = set(self._engine.criteria(q, answer=self.my_answer(q)).index.tolist())
            if sel == 'Monitoring':
                """
                for monitoring, every criterion is evaluated for every target; target must pass all
                solution set is the intersection of all passing sets
                """
                targets = targets.intersection(t_pass)
            elif sel == 'Assessment':
                """
                for assessment, criteria only apply to certain targets- the ones that fail are
                the set difference between all linked targets and all passing targets.
                that set difference is excluded from the solution set.
                """
                t_fail = set(self._engine.criteria(q).index.tolist()).difference(t_pass)
                targets = targets.difference(t_fail)
            elif sel == 'ControlRules':
                # no criteria for control_rules - all targets pass
                pass

        self._qualifying_targets[sel] = targets

    def refine(self, sel=None):
        if sel is None:
            sel = get_selector()
        qs = self._engine.caveats_for(sel)
        for q in qs:
            if q not in self._answers:
                self.answer(q)

    def show_qualifying_targets(self, sel):
        for i in self._qualifying_targets[sel]:
            self._engine.show(target=i)

    def show_non_qualifying_targets(self, sel):
        for i in self._nonqualifying_targets(sel):
            self._engine.show(target=i)
            self.print_target_criteria(self.qualify_target(i))

    def guide(self, sel=None):
        """
        Main entry function to "guide" a fishery manager to qualify and rank targets.
        :param sel:
        :return: a dictionary containing a score report that can be written to disk
        """
        if sel is None:
            sel = get_selector()
        self.filter(sel)
        self.refine(sel)
        return {
            'FisheryGuide': self.name(),
            'Selector': sel,
            'QualifyingTargets': self.score_qualifying_targets(sel),
            'NonQualifyingTargets': self.score_nonqualifying_targets(sel)
        }

    def export_answers(self):
        return {
            "answers": [{'QuestionID': k, 'Answer': v} for k, v in self._answers.items()]
        }

    def import_answers(self, json_in):
        for a in json_in['answers']:
            self._answers[int(a['QuestionID'])] = int(a['Answer'])

    def save_answers(self, filename=None):
        filename = self.get_abs_path(filename)
        with open(filename, 'w') as fp:
            json.dump(self.export_answers(), fp, indent=4)
        print('Answers written to %s' % filename)
        self._filename = filename

    def load_answers(self, filename=None):
        filename = self.get_abs_path(filename)
        with open(filename, 'r') as fp:
            j = json.load(fp)
        self.import_answers(j)
        self._filename = filename

    def save_guide(self, guide, filename=None):
        filename = self.get_abs_path(filename)
        guide_name = self.name() + '.' + guide['Selector'].lower() + '.json'
        filename = os.path.join(os.path.dirname(filename), guide_name)
        with open(filename, 'w') as fp:
            json.dump(guide, fp, indent=4)
        print('%s guide written to %s' % (guide['Selector'], filename))
