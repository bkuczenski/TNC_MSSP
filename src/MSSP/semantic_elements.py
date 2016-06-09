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

    def __str__(self):
        return self.text or 'no text'


class SemanticElementSet(object):
    """
    A uuid-indexed replacement for ElementSet.

    The class has two dictionaries, one the reverse of the other, which functions to guarantee uniqueness of
    elements.

    Internals:
        obj._ns_uuid = namespace UUID
        obj._d[key] = value, where key is a UUID, value is a SemanticElement
        obj._rd[string] = key, where string is self._element_to_string(value), key is a UUID

    Methods:
        class.from_element_set(element_set) - creates a SemanticElementSet from an old-style (spreadsheet) ElementSet
        class.from_json(json, colormap=None) - creates a SemanticElementSet from a json file

        obj.get_index(element) looks up in _rd
        obj[index] looks up UUID in _d

        obj[index] = element - creates or updates the string with the given UUID index - updates _d and _rd

        obj.add_element(text, fill_color)
    """
    def __init__(self, ns_uuid=None, colormap=None):
        self._d = dict()
        self._rd = dict()  # reverse dictionary
        self.dups = []
        self._colormap = colormap
        if ns_uuid is not None:
            if isinstance(ns_uuid, uuid.UUID):
                self._ns_uuid = ns_uuid
            else:
                self._ns_uuid = uuid.UUID(ns_uuid)
        else:
            self._ns_uuid = uuid.uuid4()

    def _add_element(self, element):
        self[self._index_from_element(element)] = element

    def _lookup_rgb(self, color, field='ColorName'):
        try:
            return self._colormap[self._colormap[field] == color]['RGB'].iloc[0]
        except IndexError:
            raise KeyError('Key %s was not found in colormap column %s' % (color, field))

    @classmethod
    def from_element_set(cls, element_set):
        the_set = cls()
        for element in element_set:
            the_set.add_element(element.text, element.fill_color)
        return the_set

    @classmethod
    def from_json(cls, json_in, colormap=None):
        """
        This is the ugliest hack, I don't even..
        :param json_in:
        :param colormap:
        :return:
        """
        the_set = cls(ns_uuid=json_in['nsUuid'], colormap=colormap)
        for i in json_in['Elements']:
            if colormap is None:
                i_id = uuid.UUID(i['AttributeID'])
                i_txt = i['AttributeText']
                the_set[i_id] = SemanticElement(text=i_txt)
            else:
                i_id = uuid.UUID(i['NoteID'])
                i_txt = i['NoteText']
                rgb = the_set._lookup_rgb(i['NoteColor'])
                the_set[i_id] = SemanticElement(text=i_txt, fill_color=rgb)
        return the_set

    @staticmethod
    def _string_from_element(element):
        return 'color[%s] text[%s]' % (element.fill_color, element.text)

    def _index_from_element(self, element):
        try:
            return uuid.uuid3(self._ns_uuid, self._string_from_element(element).encode('utf-8'))
        except UnicodeDecodeError:
            print('Failed with %s' % self._string_from_element(element))
            raise

    def get_index(self, element):
        return self._rd[self._string_from_element(element)]

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        if not isinstance(key, uuid.UUID):
            key = uuid.UUID(key)
        return self._d[key]

    def __setitem__(self, key, value):
        """
        value must have 'text' and 'fill_color' attributes
        :param key:
        :param value:
        :return:
        """
        if not isinstance(key, uuid.UUID):
            key = uuid.UUID(key)
        if not isinstance(value, SemanticElement):
            value = SemanticElement(value.text, fill_color=value.fill_color)
        rkey = self._string_from_element(value)
        if rkey in self._rd:  # duplicate values not allowed
            if key != self._rd[rkey]:
                print('Value %s already exists\nold key %s\nnew key %s' % (rkey, self._rd[rkey], key))
                self.dups.append((key, self._rd[rkey]))
                return
            else:
                assert key in self._d
        if key in self._d:  # updates ARE allowed - but we need to delete the old reverse-key mapping
            chk_key = self._rd.pop(self._string_from_element(self._d[key]))
            assert chk_key == key, 'Corrupt dict found!'

        self._d[key] = value
        self._rd[rkey] = key

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

    def find_string(self, string):
        """
        look for direct-matching strings (not regex)
        :param string:
        :return:
        """
        return [k for k, v in self._d.items() if v.text == string]

    def add_element(self, text, fill_color=None):
        """
        creates a semantic element then adds it if it doesn't already exist
        :param text:
        :param fill_color:
        :return: the UUID of the existing or created element
        """
        element = SemanticElement(text, fill_color=fill_color)
        try:
            key = self.get_index(element)
        except KeyError:
            self._add_element(element)
            key = self.get_index(element)
        return key

    def update_text(self, key, new_text):
        elt = self._d[key]
        print('Old: %s\nNew: %s' % (elt.text, new_text))
        new_elt = SemanticElement(new_text, elt.fill_color)
        self[key] = new_elt

    def update_color(self, key, new_rgb):
        if self._colormap is None:
            raise AttributeError('This ElementSet has no colormap.')
        if bool(fill_color_re.match(new_rgb)):
            new_rgb = self._lookup_rgb(new_rgb, 'RGB')
        else:  # assume string color
            new_rgb = self._lookup_rgb(new_rgb)

        elt = self._d[key]
        print('Old: %s\nNew: %s' % (elt.fill_color, new_rgb))
        new_elt = SemanticElement(elt.text, new_rgb)
        self[key] = new_elt

    def get_ns_uuid(self):
        return self._ns_uuid

    def test_dict_integrity(self):
        for key in self.keys():
            rkey = self._string_from_element(self._d[key])
            assert self._rd[rkey] == key, 'key %s failure' % key
        for rkey in self._rd.keys():
            key = self._rd[rkey]
            assert self._string_from_element(self._d[key]) == rkey, 'rkey %s failure' % rkey
