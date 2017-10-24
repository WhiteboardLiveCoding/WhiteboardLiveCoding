import keyword
import logging
import string

from fuzzysearch import find_near_matches

KW_LIST = keyword.kwlist + ["print", "list", "dict", "set", "file", "open", "assert", "range"]
LOGGER = logging.getLogger()

SPEC_ATTR = ["doc", "name", "qualname", "module", "defaults", "code", "globals", "dict", "closure",
             "annotations", "kwdefaults", "main"]


class CodeFixer:
    def __init__(self, code, indents, poss_lines):
        self.code = code
        self.indents = indents
        self.poss_lines = poss_lines
        self.context = []

    def fix(self):
        fixed_lines = []
        lines = self.code.splitlines()

        # Iterate over all "root" elements to create scope, not actually changing the lines yet
        for idx, (indent, line) in enumerate(zip(self.indents, lines)):
            if indent == 0:
                self._fix_line(line, idx)

        for idx, line in enumerate(lines):
            new_line = self._fix_line(line, idx)
            fixed_lines.append(new_line)

        return "\n".join("{indent}{code}".format(indent="  " * indent, code=line) for indent, line in
                         zip(self.indents, fixed_lines))

    def _levenshtein(self, word, check_on=None):
        if not check_on:
            check_on = self.context + KW_LIST

        start = 0  # doesn't change
        end = 0
        l_dist = 10  # max change is 2 anyway
        curr_best_word = None

        for kw in check_on:
            pos = find_near_matches(kw, word, max_l_dist=min(2, len(kw) - 1), max_insertions=0, max_deletions=0)

            for p in pos or []:
                if p.start == start:
                    # If word is longer, or if theres less l_dist (prioritising contextual_data)
                    if end < p.end or (end == p.end and p.dist < l_dist and not (
                                    curr_best_word in self.context and kw in KW_LIST)):
                        end = p.end
                        curr_best_word = kw
                        l_dist = p.dist

        return curr_best_word, start, end

    def _fix_word(self, word, word_number=None, line_number=None, prev_word="", next_word=""):
        if prev_word == "import" or prev_word == "for" or next_word == "=":
            if word and word not in self.context:
                self.context.append(word)  # add the imported module, or the var name to contextual data
            return word

        elif word.startswith('--') and word.endswith('--'):
            no_dash = word.strip('--')
            best_word, start, end = self._levenshtein(no_dash, check_on=SPEC_ATTR)
            if best_word and len(best_word) == len(no_dash):
                word = "__" + best_word + "__"
            else:
                word = "__" + no_dash + "__"

        elif not prev_word:
            best_word, start, end = self._levenshtein(word)
            if best_word:
                word = word[:start] + best_word + word[end:]

        return word

    def _fix_line(self, line, line_number):
        fixed_words = []
        words = line.split()
        for word_number, word in enumerate(words):
            prev_word = fixed_words[-1] if fixed_words and fixed_words[-1] in ["def", "class", "import"] else None
            next_word = words[word_number + 1] if len(words) > word_number + 1 else None

            fixed_word = word  # set default

            if prev_word == "class" or prev_word == "def":  # class/method/function declaration
                self._set_decl(word)

            elif prev_word == "for":  # se var X as context in a 'for X in _' statement
                self._set_forloop_var(word)

            # TODO: check valid function name
            elif "(" in word and ")" in word and len(word[:word.find('(')]) > 0:  # method/function call + prefixed by function name
                fixed_word = self._fix_funccall(word, line_number, word_number)

            # TODO: functions with spaces in args
            else:  # not detected as anything special - attempt to autocorrect
                fixed_word = self._fix_word(word, word_number, line_number,
                                            prev_word=prev_word, next_word=next_word)

            if prev_word == "=" and len(fixed_words) > 2:  # shouldve already been caught but sanity check
                self._set_var(fixed_words)

            if word != fixed_word:
                LOGGER.debug("Replaced %s with %s", word, fixed_word)
            fixed_words.append(fixed_word)

        return " ".join(fixed_words)

    def _fix_funccall(self, word, line_number, word_number):
        # TODO: add support for multiple args -> requires more context due to spaces, commas etc
        argstart = word.find("(") + 1
        argend = word.rfind(")")
        args = word[argstart:argend]

        # attempt to fix the called func_name being invalid
        func_name = word[:argstart - 1]
        if func_name not in self.context:
            fixed_func_name = self._fix_word(func_name)
            if fixed_func_name in self.context:
                word = func_name + word[argstart - 1:]

        if args in self.context or all(
                        arg_char in string.digits for arg_char in args):  # TODO: add support for string args
            pass  # all good here, valid variable or int

        elif args:
            fixed_args = self._fix_args(args, word, line_number, word_number)
            word = word[:argstart] + fixed_args + word[argend:]

        return word

    def _fix_args(self, args, fixed_word, line_number, word_number):
        new_args = args
        some_args, start, end = self._levenshtein(args)
        # TODO: multiple args/words
        if "(" in args and ")" in args and len(args[:args.find('(')]) > 0: # is a nested function
            new_args = self._fix_funccall(args, line_number, word_number)

        elif some_args and some_args in self.context:
            new_args = some_args

        elif args.startswith("--") and args.endswith("--"):
            new_args = self._fix_word(args)

        else:
            # we should use digits
            possibles = self.poss_lines[line_number][word_number]
            poss_args = ""
            start_pos = fixed_word.find(args)
            curr_possibilities = {i: possibles[i] for i in range(start_pos, start_pos + len(args))}
            for char, possible_char in zip(args, curr_possibilities.values()):
                top3 = [digit_chars for digit_chars in possible_char[1:3] if str(digit_chars) in string.digits]
                if any(top3):  # if any of top3 are digits
                    poss_args += top3[0]
            if len(poss_args) == len(args):
                new_args = poss_args

        return new_args

    def _set_decl(self, fixed_word):
        if "(" in fixed_word:
            name = fixed_word[:fixed_word.find("(")]
            if name and name not in self.context:
                self.context.append(name)

        if "(" in fixed_word and ")" in fixed_word:
            args = fixed_word[fixed_word.find("(") + 1:fixed_word.rfind(")")]
            if args and args not in self.context:
                self.context.append(args)

    def _set_var(self, fixed_words):
        var_name = fixed_words[-2]
        if var_name and var_name not in self.context:
            self.context.append(var_name)  # add var name before = sign to contextual data

    def _set_forloop_var(self, var):
        if var and var not in self.context:
            self.context.append(var)
