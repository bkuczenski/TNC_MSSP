"""
Replace my coding-school ElementSet with a set of "semantic elements" that are just text and fill_color
(the uniqueness properties that were important in reading the spreadsheet do not need to be replicated
here, but if needed they can be folded into the container class)
"""
from __future__ import print_function, unicode_literals

import uuid
import re

from MSSP.exceptions import MsspError
from MSSP.elements import Element


fill_color_re = re.compile('[0-9A-F]{8}')


class SemanticElement(object):
    """
    A referenceable atom of semantic content with two dimensions: text (unicode) and fill_color.
    An element has its own UUID which can be specified at initialization or else is created at random.
    """
    def __init__(self, text, fill_color=None):
        """

        :param text:
        :param fill_color:
        """
        self.text = text
        if fill_color is None:
            fill_color = '00000000'
        else:
            try:
                chk = bool(fill_color_re.match(fill_color))
                if not chk:
                    fill_color = '00000000'
            except TypeError:
                print('Type fail %s' % type(fill_color))
                fill_color = '00000000'

        self.fill_color = fill_color

    def search(self, string):
        """
        returns true if string (regex) is found in self.text
        :param string: regex
        :return: bool
        """
        return bool(re.search(string, unicode(self.text), flags=re.IGNORECASE | re.U))


class SemanticElementSet(object):
    """
    A uuid-indexed replacement for ElementSet. For now we hold off on checking uniqueness
    """
    def __init__(self, ns_uuid=None):
        self._d = dict()
        if ns_uuid is not None:
            if isinstance(ns_uuid, uuid.UUID):
                self._ns_uuid = ns_uuid
            else:
                self._ns_uuid = uuid.UUID(ns_uuid)
        else:
            self._ns_uuid = uuid.uuid4()

    @classmethod
    def from_element_set(cls, element_set):
        the_set = cls()
        for element in element_set:
            the_set._add_element(element)
        return the_set

    @classmethod
    def from_json(cls, json_in, colormap=None):
        """
        This is the ugliest hack, I don't even..
        :param json_in:
        :param colormap:
        :return:
        """
        the_set = cls(ns_uuid=json_in['nsUuid'])
        for i in json_in['Elements']:
            if colormap is None:
                i_id = uuid.UUID(i['AttributeID'])
                i_txt = i['AttributeText']
                the_set[i_id] = SemanticElement(text=i_txt)
            else:
                i_id = uuid.UUID(i['NoteID'])
                i_txt = i['NoteText']
                rgb = colormap[colormap['ColorName'] == i['NoteColor']]['RGB'].iloc[0]
                the_set[i_id] = SemanticElement(text=i_txt, fill_color=rgb)
        return the_set

    def _string_from_element(self, element):
        return 'color[%s] text[%s]' % (element.fill_color, element.text)

    def _index_from_element(self, element):
        try:
            return uuid.uuid3(self._ns_uuid, self._string_from_element(element).encode('utf-8'))
        except UnicodeDecodeError:
            print('Failed with %s' % self._string_from_element(element))
            raise

    def _add_element(self, element):
        self._d[self._index_from_element(element)] = SemanticElement(element.text, fill_color=element.fill_color)

    def get_index(self, element):
        if isinstance(element, Element):
            return self._index_from_element(element)
        elif isinstance(element, basestring):
            inds = [k for k, v in self._d.items() if v == element]
            if len(inds) > 0:
                if len(inds) > 1:
                    print('Warning: %d matches found!' % len(inds))
                return inds[0]
            else:
                print('Nothing found.')
                return None
        else:
             raise MsspError('Unknown input type')

    def __len__(self):
        return len(self._d)

    def __getitem__(self, item):
        return self._d[item]

    def __setitem__(self, key, value):
        if not isinstance(key, uuid.UUID):
            key = uuid.UUID(key)
        if not isinstance(value, SemanticElement):
            value = SemanticElement(value.text, fill_color=value.fill_color)
        self._d[key] = value

    def keys(self):
        return self._d.keys()

    def search(self, string, idx=None):
        """
        Search the element set for a plain string or regex. returns a list of indices
        :param string: the search term
        :param idx: (default:None) a set of indices to search within-- returns the intersection
        :return:
        """
        ind = []
        type(string)
        for k, v in self._d.items():
            if v.search(string) is True:
                ind.append(k)

        if idx is None:
            return ind

        return list(set(ind).intersection(idx))

    def get_ns_uuid(self):
        return self._ns_uuid
