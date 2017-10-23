import keyword
from string import digits

from fuzzysearch import find_near_matches

KW_LIST = keyword.kwlist + ["print", "list", "dict", "set", "file", "open", "assert", "range"]


class CodeFixer:
    def __init__(self, code, indents, poss_lines):
        self.code = code
        self.indents = indents
        self.poss_lines = poss_lines

    def fix(self):
        fixed_lines = []
        contextual_data = []
        lines = self.code.splitlines()

        # Iterate over all "root" elements to create scope, not actually changing the lines yet
        for idx, (indent, line) in enumerate(zip(self.indents, lines)):
            if indent == 0:
                _, contextual_data = self._fix_line(line, idx, contextual_data)

        for idx, line in enumerate(lines):
            new_line, contextual_data = self._fix_line(line, idx, contextual_data)
            fixed_lines.append(new_line)

        return "\n".join("{indent}{code}".format(indent="  " * indent, code=line) for indent, line in
                         zip(self.indents, fixed_lines))

    def _levenshtein(self, word, contextual_data):
        start = 0  # doesn't change
        end = 0
        l_dist = 10  # max change is 2 anyway
        curr_best_word = None

        for kw in contextual_data + KW_LIST:
            pos = find_near_matches(kw, word, max_l_dist=min(2, len(kw) - 1), max_insertions=0, max_deletions=0)

            for p in pos or []:
                if p.start == start:
                    # If word is longer, or if theres less l_dist (prioritising contextual_data)
                    if end < p.end or (end == p.end and p.dist < l_dist and not (
                                    curr_best_word in contextual_data and kw in KW_LIST)):
                        end = p.end
                        curr_best_word = kw
                        l_dist = p.dist

        return curr_best_word, start, end

    def _fix_word(self, word, word_number, line_number, contextual_data=None, prev_word="", next_word=""):
        if contextual_data is None:
            contextual_data = []

        if prev_word == "import" or next_word == "=":
            contextual_data.append(word)  # add the imported module, or the var name to contextual data
            return word, contextual_data

        elif not prev_word:
            best_word, start, end = self._levenshtein(word, contextual_data)
            if best_word:
                word = word[:start] + best_word + word[end:]

        return word, contextual_data

    def _fix_line(self, line, line_number, contextual_data=None):
        if contextual_data is None:
            contextual_data = []

        fixed_words = []
        words = line.split()
        for idx, word in enumerate(words):
            prev_word = fixed_words[-1] if fixed_words and fixed_words[-1] in ["def", "class", "=", "import"] else None
            next_word = words[idx + 1] if len(words) > idx + 1 else None

            fixed_word, contextual_data = self._fix_word(word, idx, line_number, contextual_data=contextual_data,
                                                         prev_word=prev_word, next_word=next_word)

            #  TODO: add context logic for the "for X in _" syntax
            if prev_word == "class" or prev_word == "def": # class/method/function declaration

                if "(" in fixed_word:
                    name = fixed_word[:fixed_word.find("(")]
                    if name not in contextual_data:
                        contextual_data.append(name)

                if "(" in fixed_word and ")" in fixed_word:
                    args = fixed_word[fixed_word.find("(") + 1:fixed_word.rfind(")")]
                    if args and args not in contextual_data:
                        contextual_data.append(args)

            elif "(" in fixed_word and ")" in fixed_word:  # method/function call
                # TODO: add support for multiple args
                argstart = fixed_word.find("(") + 1
                argend = fixed_word.rfind(")")
                args = fixed_word[argstart:argend]
                if args in contextual_data or all(arg_char in digits for arg_char in args):
                    pass  # all good here, valid variable or int
                elif args:
                    new_args, start, end = self._levenshtein(args, contextual_data)
                    if new_args and new_args in contextual_data:
                        pass  # all good
                    else:
                        # we should use digits
                        possibles = self.poss_lines[line_number][idx]
                        new_args = ""
                        start_pos = fixed_word.find(args)
                        curr_possibilities = {i: possibles[i] for i in range(start_pos, start_pos + len(args))}
                        for char, possible_char in zip(args, curr_possibilities.values()):
                            top3 = [digit_chars for digit_chars in possible_char[1:3] if str(digit_chars) in digits]
                            if any(top3):  # if any of top3 are digits
                                new_args += top3[0]

                        fixed_word = fixed_word[:argstart] + new_args + fixed_word[argend:]

            if prev_word == "=" and len(fixed_words) > 2:  # shouldve already been caught but sanity check
                var_name = fixed_words[-2]
                if var_name not in contextual_data:
                    contextual_data.append(var_name)  # add var name before = sign to contextual data

            fixed_words.append(fixed_word)

        new_line = " ".join(fixed_words)

        # If any of these, I expect it to end with a colon
        # NOTE: this is currently hardcoding; not interesting.
        # if any(new_line.startswith(b) for b in ["class", "def", "if", "for"]) and new_line.endswith("i"):
        #     new_line = new_line[:-1] + ":"

        return new_line, contextual_data
