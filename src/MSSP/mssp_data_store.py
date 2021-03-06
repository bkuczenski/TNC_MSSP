"""
mssp_data_store.py

This module contains the core class for emulating the MSSP decision tool.

The constructor transforms a SpreadsheetData object into an MsspEngine object through the use of a
question_map, which is an excel spreadsheet that contains two mappings:

 1. a mapping between questions, consisting of semantic identities that tie different records together;

 2. a mapping from RGB colors to scores, which is used to assign quantitative values to notes.

Once constructed, the MsspEngine object can be used interactively to provide question prompts to a user,
collect answers, and then score the various monitoring, assessment, or control rules options.  At the moment
the scoring and evaluation is target-type-specific.

The MsspEngine can also be used to prototype administrative changes, such as adding a new question, editing
question-target mappings, or reviewing annotation relationships.

An MsspEngine object can be serialized to JSON for future development. A new MsspEngine object can also
be created by de-serializing the JSON.  This allows for interim manual revision of the MSSP content until
an admin interface is constructed.

DATA MODEL

Attributes = ElementSet
Notes = ElementSet

Questions = collection of Attributes and valid answer strings (default to Yes/No)

"""

from collections import namedtuple
from uuid import UUID
# from numpy import isnan

from MSSP.utils import convert_reference_to_subject, check_sel, selectors, ifinput
from MSSP.exceptions import MsspError
from MSSP.importers import indices

from pandas import MultiIndex

searchAttributes = namedtuple('searchAttributes', ['attributes', 'questions', 'targets'])
searchNotes = namedtuple('searchNotes', ['notes', 'questions', 'targets'])


class MsspDataStore(object):
    """
    Engine for reviewing and analyzing MSSP content in its "purified" form.

    Two class methods:
     .from_spreadsheet accepts a SpreadsheetData object
     .from_json accepts a JSON file pointer


    """

    def __init__(self, attribute_set, note_set, question_enum, target_enum,
                 question_attributes, target_attributes, criteria, caveats, colormap):
        """

        :param attribute_set: a SemanticElementSet of attributes
        :param note_set: a SemanticElementSet of notations (scores encoded by RGB)
        :param question_enum: an ordered list of questions with persistent QuestionID
        :param target_enum: an ordered list of targets with persistent TargetID
        :param question_attributes: a DataFrame linking Questions and Attributes
        :param target_attributes: a DataFrame linking Targets and Attributes
        :param criteria: a DataFrame linking QuestionID, TargetID, answer, NoteID, score
        :param caveats: a DataFrame linking QuestionID, TargetID, threshold
        :param colormap: a DataFrame mapping RGB colors to names and scores
        :return:
        """
        self._attributes = attribute_set
        self._notes = note_set
        self._questions = question_enum
        self._targets = target_enum

        self._question_attributes = question_attributes
        self._target_attributes = target_attributes

        self._criteria = criteria
        self._caveats = caveats

        # compute 'satisfies' list from 'satisfied_by'
        [self._set_satisfies(k) for k in range(len(self._questions))]

        self.colormap = colormap  # let the user manipulate the colormap directly

    def _set_satisfies(self, satisfied_by):
        """
        Sets 'satisfies' for questions that appear in another question's 'satisfied_by'

        :param satisfied_by: index into questions enum for satisfied question
        :return: nothing
        """
        if self._questions[satisfied_by] is not None:
            sb = self._questions[satisfied_by].satisfied_by
            if len(sb) > 0:
                for q in sb:
                    self._questions[q].satisfies.add(satisfied_by)

    def _replace_field_with_answer(self, df, field='Threshold'):
        """

        :param df:
        :param field:
        :return:
        """
        def lookup(rec):
            return self._questions[rec['QuestionID']].valid_answers[rec[field]]

        df['AnswerValue'] = df.apply(lookup, axis=1, reduce=True)
        df.drop(field, axis=1, inplace=True)

    def _replace_note_id_with_note(self, df):
        df['Note'] = df['NoteID'].map(lambda x: self._notes[x].text)
        df.drop('NoteID', axis=1, inplace=True)

    def _make_attr_list(self, index, record='question'):
        """
        List of attributes associated with a given record
        :param record: 'question' or 'target'
        :param index:
        :return:
        """
        if record == 'question':
            mapping = self._question_attributes
            key = 'QuestionID'
        elif record == 'target':
            mapping = self._target_attributes
            key = 'TargetID'
        else:
            raise MsspError('Invalid record specifier %s' % record)
        return mapping.loc[mapping[key] == index, 'AttributeID'].tolist()

    def _print_attributes(self, index, record='question'):
        attr_keys = self._make_attr_list(index, record=record)
        if record == 'question':
            mylist = self._questions
        elif record == 'target':
            mylist = self._targets
        else:
            raise MsspError('Invalid record specifier %s' % record)
        title = mylist[index].title
        cat = mylist[index].category
        exclude = []
        if title is not None:
            print('"%s"' % self._attributes[title])
            exclude += [title]
        if cat is not None:
            print('(Category: %s)' % self._attributes[cat])
            exclude += [cat]

        for k in attr_keys:
            if k not in exclude:
                print('  * %s' % self._attributes[k])

        return attr_keys

    def _color_of_cell(self, element):
        """
        Return the color encoded by the element's fill_color
        :param element:
        :return:
        """
        return self.colormap[self.colormap['RGB'] == element.fill_color]['ColorName'].iloc[0]

    def _cri_for_record(self, index, record='question', answer=None):
        fieldname = {
            'question': 'QuestionID',
            'target': 'TargetID'
        }[record]
        criteria = self._criteria[self._criteria[fieldname] == index].copy()
        # TODO: make this return 'satisfies' entries as well
        if answer is not None:
            if record == 'target':
                print('Ignoring answer value for target-based query')
            else:
                answer_value = indices(self._questions[index].valid_answers, lambda x: x == answer)
                if len(answer_value) != 1:
                    print('Got spurious answer matching results: %s' % answer_value)
                else:
                    # filter to only passing answers
                    criteria = criteria[criteria['Threshold'] <= answer_value]

        # re-encode answer value with answer text (and call it Answer Value)
        self._replace_field_with_answer(criteria)
        return criteria

    def _cavs_for_record(self, index, record='question', answer=None):
        fieldname = {
            'question': 'QuestionID',
            'target': 'TargetID'
        }[record]
        caveats = self._caveats[self._caveats[fieldname] == index].copy()
        self._replace_field_with_answer(caveats, field='Answer')
        if answer is not None:
            if record == 'target':
                print('Ignoring answer value for target-based query')
            else:
                # filter to only matching answers
                caveats = caveats[caveats['AnswerValue'] == answer]

        self._replace_note_id_with_note(caveats)
        return caveats

    def _print_object(self, index, record='question'):
        """
        Common functions for printing question + target records.
        :param index: the ID of the object
        :param record: 'question' or 'target'
        :return:
        """
        if record == 'question':
            fieldname = 'QuestionID'
            obj = self._questions[index]
            print('Question ID: %d' % index)
        elif record == 'target':
            fieldname = 'TargetID'
            obj = self._targets[index]
            print('Target ID: %d' % index)
        else:
            raise MsspError('Invalid record specifier %s' % record)

        obj.attributes = [k for k in self._print_attributes(index, record=record)]
        obj.criteria = None
        obj.caveats = None
        print(obj)
        criteria = self._criteria[self._criteria[fieldname] == index].copy()
        if len(criteria) > 0:
            self._replace_field_with_answer(criteria)
            print('Has Criteria:')
            print(criteria)
            obj.criteria = criteria

        caveats = self._cavs_for_record(index, record=record)
        if len(caveats) > 0:
            print('Has Caveats:')
            print(caveats)
            obj.caveats = caveats

        return obj

    # user-facing functions begin here
    def question(self, index):
        """
        Print out a question, in terms of its attributes, possible answers, and impacted targets
        :param index: index into the question enum
        :return:
        """
        if self._questions[index] is None:
            print('No question with ID %s' % index)
            return
        return self._print_object(index, record='question')

    def questions(self, index=None):
        """
        Simple indexer- return one or a list of MsspQuestion objects
        :param index:
        :return:
        """
        if index is None:
            index = [k for k, v in enumerate(self._questions) if v is not None]
        if isinstance(index, int):
            index = [index]
        return [self._questions[i] for i in index]

    def target(self, index):
        """

        :param index:
        :return:
        """
        return self._print_object(index, record='target')

    def targets(self, index):
        """
        Simple indexer- return one or a list of MsspTarget objects
        :param index:
        :return:
        """
        if isinstance(index, int):
            index = [index]
        return [self._targets[i] for i in index]

    def title(self, question=None, target=None):
        """

        :param question:
        :param target:
        :return:
        """
        if question is not None:
            title = self._questions[question].title
        elif target is not None:
            title = self._targets[target].title
        else:
            title = None
        if title is None:
            return 'no title'
        return self._attributes[title].text

    def show(self, question=None, target=None):
        """
        Print a record's attributes
        :param question:
        :param target:
        :return:
        """
        if question is not None:
            print('\nQuestionID %d: ' % question)

            self._print_attributes(question)
        elif target is not None:
            print('\nTargetID %d: ' % target)
            self._print_attributes(target, record='target')

    def attribute(self, index):
        attr = self._attributes[index]
        return attr.text

    def attributes(self, index):
        """
        Print out the attribute(s) listed in the index (or list)
        :param index:
        :return:
        """
        if isinstance(index, UUID):
            index = [index]

        for i in index:
            print 'AttributeID %s: %s' % (i, self._attributes[i])

    def note(self, note_id):
        note = self._notes[note_id]
        return note.text, self._color_of_cell(note)

    def notes(self, index):
        """
        print out the note(s) listed in the index (or list)
        :param index:
        :return:
        """
        if isinstance(index, int):
            index = [index]

        for i in index:
            n = self._notes[i]
            print 'NoteID %s [%s]: %s' % (i, self._color_of_cell(n), n.text)

    def questions_with_attribute(self, index):
        qs = set([v['QuestionID'] for k, v in self._question_attributes.iterrows() if v['AttributeID'] == index])
        return sorted(list(qs))

    def targets_with_attribute(self, index):
        ts = set([v['TargetID'] for k, v in self._target_attributes.iterrows() if v['AttributeID'] == index])
        return sorted(list(ts))

    def remap_duplicate_attribute_references(self):
        for dup, orig in self._attributes.dups:
            self._question_attributes.loc[self._question_attributes['AttributeID'] == dup, 'AttributeID'] = orig
            self._target_attributes.loc[self._target_attributes['AttributeID'] == dup, 'AttributeID'] = orig

    def _find_attr_map(self, mapping, r_index, attr):
        if mapping is self._question_attributes:
            return (mapping['AttributeID'] == attr) & (mapping['QuestionID'] == r_index)
        elif mapping is self._target_attributes:
            return (mapping['AttributeID'] == attr) & (mapping['TargetID'] == r_index)
        else:
            raise MsspError('Unknown mapping')

    def attributes_for(self, r_index, record='question'):
        return self._make_attr_list(r_index, record=record)

    def find_attribute(self, string):
        return self._attributes.find_string(string)

    def find_or_create_attribute(self, string):
        if string is None:
            return None
        return self._attributes.add_element(string)

    def update_attribute(self, attr, new_string):
        self._attributes.update_text(attr, new_string)

    def add_attribute_mapping(self, r_index, attr, record='question'):
        if attr is None:
            return
        if attr not in self._attributes.keys():
            raise KeyError('Attribute not found.')
        if record == 'question':
            qi = self._find_attr_map(self._question_attributes, r_index, attr)
            if sum(qi) != 0:
                print('attribute map - %d found' % sum(qi))
                raise MsspError('QID %d: Attribute mapping already exists (%s)' % (r_index, self._attributes[attr]))
            self._question_attributes = self._question_attributes.append(
                {
                    'AttributeID': attr,
                    'QuestionID': r_index
                },
                ignore_index=True, verify_integrity=True)
        elif record == 'target':
            qi = self._find_attr_map(self._target_attributes, r_index, attr)
            if sum(qi) != 0:
                print('attribute map - %d found' % sum(qi))
                raise MsspError('TID %d: Attribute mapping already exists (%s)' % (r_index, self._attributes[attr]))
            self._target_attributes = self._target_attributes.append(
                {
                    'AttributeID': attr,
                    'TargetID': r_index
                },
                ignore_index=True, verify_integrity=True)
        else:
            raise ValueError('Unknown record specifier %s' % record)

    def del_attribute_mapping(self, r_index, attr, record='question'):
        if record == 'question':
            mapping = self._question_attributes
        elif record == 'target':
            mapping = self._target_attributes
        else:
            raise ValueError('Unknown record specifier %s' % record)

        qi = self._find_attr_map(mapping, r_index, attr)
        if sum(qi) == 1:
            if record == 'question':
                self._question_attributes = mapping[~qi]
            elif record == 'target':
                self._target_attributes = mapping[~qi]
            print('Removed %d reference' % sum(qi))
        else:
            print('%d records found (0= no association; >1= something screwy' % sum(qi))

    def set_title(self, r_index, attr, record='question'):
        try:
            self.add_attribute_mapping(r_index, attr, record=record)
        except MsspError:
            pass
        if record == 'question':
            self._questions[r_index].title = attr
        elif record == 'target':
            self._targets[r_index].title = attr

    def set_category(self, r_index, attr, record='question'):
        try:
            self.add_attribute_mapping(r_index, attr, record=record)
        except MsspError:
            pass
        if record == 'question':
            self._questions[r_index].category = attr
        elif record == 'target':
            self._targets[r_index].category = attr

    def _reorder_answer_columns(self, question, table):
        """
        Reorders the columns in a [pivot] table to match the order appearing in the question
        :param question:
        :param table:
        :return:
        """
        valid_ans = self._questions[question].valid_answers
        if isinstance(table.columns, MultiIndex):
            raise MsspError('MultiIndex reordering not-yet supported')
        new_columns = [k for k in valid_ans if k in table.columns] + [k for k in table.columns if k not in valid_ans]

        return table.reindex_axis(new_columns, 1)

    def caveats(self, question=None, target=None, answer=None):
        """
        return a table of caveats by target for valid answers to a question. pd = brilliant.
        :param question: question ID
        :param target: target ID
        :param answer: answer value (only valid if question is not None
        :return: fancy pivoted pd
        """
        if question is not None:
            cavs = self._cavs_for_record(question, record='question', answer=answer)
            if target is not None:
                cavs = cavs[cavs['TargetID'] == target]
            cavs = cavs.pivot(index='TargetID', columns='AnswerValue', values='Note').fillna('')
            cavs['Reference'] = cavs.index.map(lambda x: self._targets[int(x)].label())
            cavs = self._reorder_answer_columns(question, cavs)
            return cavs
        elif question is None and target is not None:
            cavs = self._cavs_for_record(target, record='target')
            cavs = cavs.pivot(index='QuestionID', columns='AnswerValue', values='Note').fillna('')
            return cavs
        else:
            return None

    def criteria(self, question=None, target=None, answer=None):
        """
        return a table of criteria by target for valid answers to a question. pd = brilliant.
        :param question: question ID
        :param target: target ID
        :param answer: answer threshold (only valid if question is not None)
        :return: fancy pivoted pd
        """
        if question is not None:
            cri = self._cri_for_record(question, record='question', answer=answer)
            if target is not None:
                cri = cri[cri['TargetID'] == target]
            cri = cri.pivot(index='TargetID', columns='AnswerValue', values='QuestionID').fillna('')
            cri['Reference'] = cri.index.map(lambda x: self._targets[int(x)].label())
            cri = self._reorder_answer_columns(question, cri)
            return cri
        elif question is None and target is not None:
            cri = self._cri_for_record(target, record='target')
            cri = cri.pivot(index='QuestionID', columns='AnswerValue', values='TargetID').fillna('')
            return cri
        else:
            return None

    def criteria_for_target(self, target):
        """
        All the criteria for a given target, unpivoted for automatic processing
        :param target:
        :return:
        """
        return self._criteria.loc[self._criteria['TargetID'] == target]

    def caveats_for_target(self, target):
        """
        All the caveats for a given target, unpivoted for automatic processing
        :param target:
        :return:
        """
        return self._caveats.loc[self._caveats['TargetID'] == target]

    def targets_for(self, sel):
        """
        All the targets of a given type
        :param sel:
        :return:
        """
        return [k for k, t in enumerate(self._targets) if t is not None and t.type == sel]

    def criteria_for(self, sel):
        """
        Returns a list of criteria questions limiting a given selector type
        :param sel:
        :return:
        """
        if check_sel(sel):
            t_targets = self.targets_for(sel)
            return sorted(self._criteria.loc[self._criteria['TargetID'].isin(t_targets),
                                             'QuestionID'].unique().tolist())

        else:
            print('Selector must be one of %s' % list(selectors))

    def caveats_for(self, sel):
        """
        Returns a list of caveat questions that apply to a given selector type
        :param sel:
        :return:
        """
        if check_sel(sel):
            t_targets = self.targets_for(sel)
            return sorted(self._caveats.loc[self._caveats['TargetID'].isin(t_targets), 'QuestionID'].unique().tolist())

        else:
            print('Selector must be one of %s' % list(selectors))

    def _remap_answers(self, question, mapping):
        """
        Create new criteria and caveat tables where the answer values for a specific question are re-mapped
        according to mapping.
        :param question: question ID
        :param mapping: a list of ints where mapping[old_index] = new_index
        :return: critera, caveats -- edited copies of the original arrays
        """
        print('Remapping answers with mapping %s' % mapping)
        print('map from: %s' % self._questions[question].valid_answers)

        local_cri = self._criteria.copy()
        local_cav = self._caveats.copy()
        local_cri.loc[local_cri['QuestionID'] == question, 'Threshold'] = \
            local_cri[local_cri['QuestionID'] == question]['Threshold'].map(lambda x: mapping[x])
        local_cav.loc[local_cav['QuestionID'] == question, 'Answer'] = \
            local_cav[local_cav['QuestionID'] == question]['Answer'].map(lambda x: mapping[x])
        return local_cri, local_cav

    def refactor_answers(self, question, answers):
        """
        Re-arrange or otherwise re-define the answers to a given question.  The input should include a single
        QuestionID, and a new list of the question's answers.  This list must be a SUPERSET of the question's
        existing answers [see merge_answers and delete_answer [TODO] for an antidote] and must be supplied in the
        new correct order.

        The method will generate a mapping from the current answers to the new answers, and then will go through
        all the criteria and caveats, re-mapping the index values.

        This method is made atomic by performing the mapping onto new data frames that are only installed if
        the operation is successful.
        :param question:
        :param answers:
        :return:
        """
        cur = self._questions[question].valid_answers

        if question is None or len(answers) == 0:
            print('Must supply a question and a list of answers')
            return

        diffs = set(cur).difference(set(answers))
        if len(diffs) != 0:
            print('Missing some answers: %s' % ', '.join(str(k) for k in list(diffs)))
            return

        if len(answers) != len(set(answers)):
            print('Duplicate answers provided!')
            return

        tmp = dict()
        for i in range(len(answers)):
            # tmp maps new answer to new answer index
            tmp[answers[i]] = i

        mapping = [None]*len(cur)
        for i in range(len(cur)):
            # mapping[old_index] = new_index
            mapping[i] = tmp[cur[i]]

        new_cri, new_cav = self._remap_answers(question, mapping)
        self._criteria = new_cri
        self._caveats = new_cav
        self._questions[question].valid_answers = answers

    def reorder_answers(self, question, answer_indices):
        """
        Wrapper for re-factor answers that just accepts a list of indices into the current answer list.
        :param question:
        :param answer_indices: list or tuple that contains a permutation of range(n). Allows indices to be 1-indexed
        or 0-indexed!
        :return:
        """
        cur = self._questions[question].valid_answers
        if set(answer_indices) == set(range(len(cur))):
            self.refactor_answers(question, [cur[k] for k in answer_indices])
        elif set(answer_indices) == set(range(1, len(cur)+1)):
            self.refactor_answers(question, [cur[k-1] for k in answer_indices])
        else:
            print('input does not include all indices!')

    def delete_answer(self, question, answer):
        """
        Deletes all references to the supplied answer.  If any references are found, the user will be prompted for
        confirmation prior to deleting them.

        This method has to do three things: delete criteria / caveat entries with the matching question+answer,
        re-map all the answers for that question to their new indices,
        and delete the designated answer from the question's answer list

        :param question:
        :param answer:
        :return:
        """
        cur = self._questions[question].valid_answers
        ind = [k for k, v in enumerate(cur) if v == answer]
        assert len(ind) == 1, "Not enough / too many answers found"
        ind = ind[0]

        cri_index = (self._criteria['QuestionID'] == question) & (self._criteria['Threshold'] == ind)
        cav_index = (self._caveats['QuestionID'] == question) & (self._caveats['Answer'] == ind)

        check = False
        if len(cri_index.loc[cri_index]) > 0:
            print('Matching Criteria:')
            print(self._criteria.loc[cri_index])
            check = True

        if len(cav_index.loc[cav_index]) > 0:
            print('Matching Caveats:')
            print(self._caveats.loc[cav_index])
            check = True

        if check:
            if ifinput('Really delete this answer?', 'y') != 'y':
                print('NOT deleted.')
                return

        a = range(len(cur))
        mapping = a[:ind] + [-1] + a[ind:-1]  # -1 gets deleted below

        new_cri, new_cav = self._remap_answers(question, mapping)

        new_cri = new_cri.loc[~cri_index]
        new_cav = new_cav[~cav_index]

        # 'atomic' update
        del cur[ind]  # aha! delete by reference!
        self._criteria = new_cri
        self._caveats = new_cav

    def merge_answers(self, question, answers, merge_to=None):
        """
        Merge one or more answer values together, keeping the sequence of answers the same.  References to the
        merged answers in criteria or caveats will be replaced with a reference to the 'merge_to' answer.

        examples:
        self.merge_answers(53, ['low-medium', 'medium'], merge_to='medium')
        will change all entries with 'low-medium' answer values to 'medium'.

        self.merge_answers(53, ['low-medium', 'medium'], merge_to='high')
        will change all entries with 'low-medium' or 'medium' answer values to 'high'.

        If merge_to is omitted, defaults to the first answer listed in the answers argument.

        self.merge_answers(53, ['low-medium', 'medium'])
        will change all entries with 'medium' answer values to 'low-medium'.

        In all cases the merged answers are subsequently deleted.

        pandas was a really terrible choice, internally.

        :param question:
        :param answers:
        :param merge_to:
        :return:
        """
        if isinstance(answers, str):
            answers = [answers]
        cur = self._questions[question].valid_answers
        ans_ind = [indices(cur, lambda x: x == ans)[0] for ans in answers]
        if merge_to is None:
            merge_ind = ans_ind[0]
        else:
            merge_ind = indices(cur, lambda x: x == merge_to)[0]

        mapping = range(len(cur))
        for i in mapping:
            if i in ans_ind:
                mapping[i] = merge_ind

        print('Merging answers into %s:' % cur[merge_ind])
        for i in ans_ind:
            print(' %s' % cur[i])

        if ifinput('Really continue?', 'y') != 'y':
            print('NOT merged.')
            return

        new_cri, new_cav = self._remap_answers(question, mapping)
        self._criteria = new_cri
        self._caveats = new_cav
        for i in ans_ind:
            if i != merge_ind:
                self.delete_answer(question, cur[i])

    def _remap_questions(self, questions, map_to=None):
        """
        Replace references to all question IDs listed with the one provided in map_to (or the numerical minimum
        if none is provided).
        :param questions: a list of question IDs to remap
        :param map_to: The QuestionID to be substituted. If omitted, use the numerical minimum
        :return: nothing
        """
        if map_to is None:
            map_to = min(questions)

        for table in self._question_attributes, self._caveats, self._criteria:
            table.loc[table['QuestionID'].isin(questions), 'QuestionID'] = map_to

    def _merge_and_delete(self, q, merge_to=None):
        """

        :param q:
        :param merge_to:
        :return:
        """
        if merge_to is None:
            return
        if merge_to == q:
            return
        self._questions[merge_to].merge(self._questions[q])
        self._questions[q] = None

    def merge_questions(self, questions):
        """
        Joins all the questions' valid answers together, then refactors all questions to
        have the same valid_answer list. Last thing is to re-map all the QuestionIDs from the merged questions
        onto the one with the lowest ID in: _criteria, _caveats, _question_attributes
        then the merged questions can be replaced with Nones.
        :param questions:
        :return:
        """
        new_answers = []
        for q in questions:
            for v in self._questions[q].valid_answers:
                if v not in new_answers:
                    new_answers.append(v)

        for q in questions:
            self.refactor_answers(q, new_answers)  # now all questions have the same answers properly mapped

        merge_to = min(questions)

        self._remap_questions(questions, map_to=merge_to)

        for q in questions:
            if q != merge_to:
                self._merge_and_delete(q, merge_to=merge_to)

    @staticmethod
    def _search_mapping(attrs, mapping):
        """
        Atomic search- returns records containing an attribute that matches the search term.
        :param attrs: list of attribute IDs
        :param mapping: either a
        :return: a set of indices into the specified record list
        """
        return set(mapping[mapping['AttributeID'].isin(attrs)][mapping.columns[1]])

    def search(self, terms, search_notes=False, match_any=False):
        """
        Find records that contain attributes [or notes] matching the search terms.  'terms' should be a single
        string or a list of strings.  If a list is provided, the search will return entries that match all terms
        (i.e. the intersection of result sets).  This can be changed to 'match_any' to return the union of result
        sets.

        By default, searches on attributes.  Search notes instead by specifying search_notes=True.

        By default, returns a namedtuple with names 'attributes' [or 'notes'], 'questions', and 'targets', with each
        field containing a list of indices into self.{attributes|notes|questions|targets}

        :param terms: string or list of strings to search on
        :param search_notes: (bool) search on notes (i.e. "caveats") instead of attributes (default False)
        :param match_any: (bool) match any search term (default False is to match all search terms)
        :return:
        """
        if isinstance(terms, basestring):
            terms = [terms]
        if match_any:
            q_results = set()
            t_results = set()
            a_results = set()
            operation = set.union
        else:
            q_results = set(range(len(self._questions)))
            t_results = set(range(len(self._targets)))
            if search_notes:
                a_results = set(self._notes.keys())
            else:
                a_results = set(self._attributes.keys())
            operation = set.intersection

        if search_notes:
            rt = searchNotes
            for term in terms:
                notes = self._notes.search(term)
                a_results = operation(a_results, notes)

                n_results = self._caveats[self._caveats['NoteID'].isin(notes)]

                q_results = operation(q_results, set(n_results['QuestionID']))
                t_results = operation(t_results, set(n_results['TargetID']))

        else:
            rt = searchAttributes
            for term in terms:
                attrs = self._attributes.search(term)
                a_results = operation(a_results, attrs)

                q_results = operation(q_results, self._search_mapping(attrs, self._question_attributes))
                t_results = operation(t_results, self._search_mapping(attrs, self._target_attributes))

        return rt(*(sorted(list(k)) for k in (a_results, q_results, t_results)))

    def serialize(self):
        """
        Serializes the MsspEngine object out to a collection of dictionaries.

        The serialization includes the following files:

         - attributes.json: a dict of attribute UUIDs + text (only those mentioned in questions or targets)

         - notes.json: a dict of note UUIDs + text

         - questions.json: an enumeration of questions with spreadsheet refs, attribute UUIDs, ordered valid
        answers, and list of satisfied_by keys.

         - targets.json: an enumeration of targets with spreadsheet ref and attribute UUIDs

         - criteria.json: a collection of question ID, explicit answer threshold, and target ID

         - caveats.json: a collection of question ID, explicit answer, target ID, note UUID

         - colormap.json: a collection of colorname, RGB value, and score (or scoring mechanism)

        They could conceivably all be placed into a single file, but that would not be useful for human-readability.

        :return: bool
        """

        questions = []
        targets = []
        criteria = []
        caveats = []
        colormap = []
        attributes = []
        notes = []

        attr_set = set()
        note_set = set()

        print "Creating {0} questions...".format(len(self._questions))
        for k in range(len(self._questions)):
            v = self._questions[k]
            attr_list = self._make_attr_list(k, record='question')
            if len(attr_list) == 0:
                continue
            add = {
                "QuestionID": k,
                "References": [convert_reference_to_subject(i) for i in v.references],
                "ValidAnswers": v.valid_answers,
                "Attributes": [str(i) for i in attr_list]
            }
            if v.title is not None:
                add["Title"] = str(v.title)
            if v.category is not None:
                add["Category"] = str(v.category)
            for i in attr_list:
                attr_set.add(i)
            if len(v.satisfied_by) > 0:
                add["SatisfiedBy"] = list(v.satisfied_by)
            questions.append(add)

        print "Creating {0} targets...".format(len(self._targets))
        for k in range(len(self._targets)):
            v = self._targets[k]
            attr_list = self._make_attr_list(k, record='target')
            if len(attr_list) == 0:
                continue
            add = {
                "TargetID": k,
                "Reference": convert_reference_to_subject(v.reference()),
                "Attributes": [str(i) for i in attr_list]
            }
            if v.title is not None:
                add["Title"] = str(v.title)
            if v.category is not None:
                add["Category"] = str(v.category)
            for i in attr_list:
                attr_set.add(i)
            targets.append(add)

        print "Creating {0} criteria...".format(len(self._criteria))
        for i, k in self._criteria.iterrows():
            threshold = self._questions[k['QuestionID']].valid_answers[k['Threshold']]
            add = {
                "QuestionID": long(k['QuestionID']),
                "Threshold": threshold,
                "TargetID": long(k['TargetID'])
            }
            criteria.append(add)

        cav_groups = self._caveats.groupby(['QuestionID', 'TargetID'])

        print "Creating {0} caveats...".format(len(cav_groups))
        for (qid, tid), group in cav_groups:
            answers = [{"Answer": a} for i, a in enumerate(self._questions[qid].valid_answers)]
            for i, r in group.iterrows():
                answers[r['Answer']]['NoteID'] = str(r['NoteID'])
                note_set.add(r['NoteID'])
            add = {
                "QuestionID": qid,
                "TargetID": tid,
                "Answers": answers
            }
            caveats.append(add)

        print "Creating {0} attributes...".format(len(attr_set))
        for attr in attr_set:
            attributes.append({
                "AttributeID": str(attr),
                "AttributeText": self._attributes[attr].text
            })

        print "Creating {0} notes...".format(len(note_set))
        for note in note_set:
            notes.append({
                "NoteID": str(note),
                "NoteText": self._notes[note].text,
                "NoteColor": self._color_of_cell(self._notes[note])
            })

        print "Creating colormap..."
        for i, k in self.colormap.iterrows():
            add = {
                "RGB": k['RGB'],
                "ColorName": k['ColorName'],
                "Score": k['Score']
            }
            colormap.append(add)

        json_out = {
            "colormap": colormap,
            "questions": sorted(questions, key=lambda x: x['QuestionID']),
            "targets": sorted(targets, key=lambda x: x['TargetID']),
            "criteria": criteria,
            "caveats": caveats,
            "attributes": {
                'nsUuid': str(self._attributes.get_ns_uuid()),
                'Elements': sorted(attributes, key=lambda x: x['AttributeID'])
            },
            "notes": {
                'nsUuid': str(self._attributes.get_ns_uuid()),
                'Elements': sorted(notes, key=lambda x: x['NoteID'])
            }
        }
        return json_out
