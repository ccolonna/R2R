#!python

""" edualigner.py: RSTEDUAligner gets a plain text and a rst .dis file and try to
                   reconstruct original elementary discourse unit offsets based on original text file.
                   Why this ? .dis file terminal node text is spaced by tokenizer in rst parser. Every
                   parser tokenize its way so we need to remove extra spaces.
                   
                   ============ Rule =============== 
                   1) s' is a tokenized sentence
                   2) s is an original sentence
                   3) len(s') >= len(s) 'as extra spaces are added. Two kind of extra spaces are added:
                        space to separate word: ['?', !'] -> ['?', ' ',  '!']
                        space to break a word: ['can't'] -> ['ca', ' ', 'n\'t' ]
                    ' we don't know len(s) as the edu is given already tokenized.
                      The parser do:
                       1) tokenize sentence
                       2) break the sentence into edu (subsentence')
                       we need to know len(subsentence) where subsentence is not tokenized subsentence'
                    so we do:
                    4) given d = Sum(subsentence)
                       given s' = Sum(w) ordered sequence of w where w = Sum(char) belonging to d (example n't belongs to d)
                       
                       find all occurences z of wn (last item of the sequence) in d
                       and select the one who minimize the distance(len(s'), subd)
                       where subd is Sum(w) i to k ordered sequence of w where w = Sum(char) belonging to d and k
                       the last item of subd in d
                    5) remove all space from subd and s' and check if s = s'
                    if not:
                    as 
                    for every z      

                            _!Clark J. Vitulli was named senior vice president and general manager of this U.S. sales and marketing arm of Japanese auto maker Mazda Motor Corp. ._!))                 
                    we start from wrong assumptions!
                    tokenizer here inserted a sentence boundary full stop . where it found an abbreviation as end of sentence  Corp.
                    



                   Since the code to get this result is a bit elaborated and not complete, we keep it outside rstmarcutree python module.

                   Usage:

                   >>> from edualigner import RSTEDUAligner
                   
                   >>> original_text = RSTEDUAligner.read_plain_text('text')
                   >>> original_offsets = RSTEDUAligner.get_original_edu_offsets(tree.get_edus(), original_text)

                   Given an edu 
"""

__author__ = "Christian Colonna"

from collections import defaultdict

class RSTEDUAligner(object):
    """ This object helps to align the edu text (elementary discourse unit) of RSTTree to the original
        plain text consumed by the rst parser. This may be necessary since the parser tokenize the text
        inserting spaces and causing disalignment.    
    """

    @staticmethod
    def get_edu_offset(edu_offsets, edu_index):
        return edu_offsets[edu_index]

    @staticmethod
    def get_original_edu_offsets(edus, original_text):
        """ Return the boundaries of an edu in original plain text. We process all the file in a hit.
            This way we always know the initial boundary of the edu since it starts from zero.     
        """


        edu_offsets = defaultdict(tuple) #(starts_char, end_char)
        new_edus = []
        starts_at = 0 # the position where the current edu starts 

        for old_edu in edus:
            
            last_edu_token = old_edu.text.split()[-1]  # the terminal token of the edu

            # all the candidates that can be the end of the edu
            edu_ending_boundary_candidates = [(i + len(last_edu_token)) for i in RSTEDUAligner.find_all_occurences(last_edu_token, original_text[starts_at:])]
            
            # we select the candidate such as the length last_char  - starts_at is the closest to
            # len(tokenized edu)
            
            winning_candidate = 0
            for possible_terminal_char in edu_ending_boundary_candidates:
                if abs((len(old_edu.text)) - possible_terminal_char) <= abs((len(old_edu.text)) - winning_candidate):
                    winning_candidate = possible_terminal_char
                ends_at = winning_candidate + starts_at

#            for possible_terminal_char in edu_ending_boundary_candidates:
#                print("Integer")
#                print(''.join(old_edu.text).replace(" ",""))
#                print("possible edu")
#                print(''.join(original_text[starts_at:possible_terminal_char]).replace(" ",""))
#                if ' '.join(old_edu.text) == ' '.join(original_text[starts_at:possible_terminal_char]):
#                    ends_at = possible_terminal_char + starts_at
            
            edu_offsets[old_edu.index] = (starts_at, ends_at)
            new_edus.append(original_text[starts_at:ends_at])

            try:
                for token in old_edu.text.split():
                    assert(token in original_text[starts_at:ends_at])
            except:
                print("There's a bug, edu not aligned")
                print(" TODO") 
                # TODO: if there are more tokens, check first if it belongs to the previous edu if not it
                # belongs to next one. Adjust boundaries! Big mess! 
                # Recursion? While?
                exit

            # move the pointer: this makes the search of ending token (n log n) to the length of the document
            starts_at = ends_at
        try:
            assert(original_text.rstrip() == ''.join(new_edus))           
        except:
            print("There's a bug, length of plain text != text derived by concatenation of new edu")
            print("To correct this you need TODO: ")
            print(" while if ")
            print("CONCATENATED EDUS TEXT")
            print(''.join(new_edus))
            print(len(''.join(new_edus)))
            print(original_text.rstrip())
            print("ORIGINAL TEXT")
            print(len(original_text))
            exit           
        return(edu_offsets)

    @staticmethod
    def read_plain_text(plain_text_path):
        with open(plain_text_path) as fh:
            lines = []
            for line in fh:
                lines.append(line)
            return ''.join(lines)
    @staticmethod
    def find_all_occurences(p, s):
        """ Yields all the occurences of the substring p in the string s.
        """
        i = s.find(p)
        while i != -1:
            yield i
            i = s.find(p, i+1)
