import keyword

from fuzzysearch import find_near_matches

KW_LIST = keyword.kwlist + ["print", "list", "dict", "set", "file", "open", "assert", "range"]


class CodeFixer:
    def __init__(self, code, indents):
        self.code = code
        self.indents = indents

    def fix(self):
        fixed_lines = []
        contextual_data = []
        lines = self.code.splitlines()

        # Iterate over all "root" elements to create scope, not actually changing the lines yet
        for indent, line in zip(self.indents, lines):
            if indent == 0:
                _, contextual_data = self._fix_line(line, contextual_data)

        for line in lines:
            new_line, contextual_data = self._fix_line(line, contextual_data)
            fixed_lines.append(new_line)

        return "\n".join("{indent}{code}".format(indent="  " * indent, code=line) for indent, line in
                         zip(self.indents, fixed_lines))

    def _fix_word(self, word, contextual_data=None, prev_word="", next_word=""):
        if contextual_data is None:
            contextual_data = []

        if prev_word == "import" or next_word == "=":
            contextual_data.append(word)  # add the imported module, or the var name to contextual data
            return word, contextual_data

        elif not prev_word:
            start = 0
            end = 0
            l_dist = 10  # max change is 2 anyway
            curr_best_match = None
            curr_best_word = None

            for kw in contextual_data + KW_LIST:
                pos = find_near_matches(kw, word, max_l_dist=min(2, len(kw) - 1), max_insertions=0, max_deletions=0)

                for p in pos or []:
                    if p.start == 0:
                        # If word is longer, or if theres less l_dist (prioritising contextual_data)
                        if end < p.end or (end == p.end and p.dist < l_dist and not (
                                curr_best_word in contextual_data and kw in KW_LIST)):
                            end = p.end
                            curr_best_match = p
                            curr_best_word = kw
                            l_dist = p.dist

            if curr_best_match and curr_best_word:
                new_word = word[:start] + curr_best_word + word[end:]
                word = new_word

        return word, contextual_data

    def _fix_line(self, line, contextual_data=None):
        if contextual_data is None:
            contextual_data = []

        fixed_words = []
        words = line.split()
        for idx, word in enumerate(words):
            prev_word = fixed_words[-1] if fixed_words and fixed_words[-1] in ["def", "class", "=", "import"] else None
            next_word = words[idx+1] if len(words) > idx + 1 else None

            new_word, contextual_data = self._fix_word(word, contextual_data=contextual_data,
                                                       prev_word=prev_word, next_word=next_word)

            if prev_word == "class" or prev_word == "def":

                if "(" in new_word:
                    name = new_word[:new_word.find("(")]
                    if name not in contextual_data:
                        contextual_data.append(name)

                if "(" in new_word and ")" in new_word:
                    args = new_word[new_word.find("(") + 1:new_word.rfind(")")]
                    # TODO: contextual data check on args
                    # if not similar to var names -> probably numbers

            if prev_word == "=" and len(fixed_words) > 2: # shouldve already been caught but sanity check
                    var_name = fixed_words[-2]
                    if var_name not in contextual_data:
                        contextual_data.append(var_name)  # add var name before = sign to contextual data

            fixed_words.append(new_word)

        new_line = " ".join(fixed_words)

        # If any of these, I expect it to end with a colon
        # NOTE: this is currently hardcoding; not interesting.
        # if any(new_line.startswith(b) for b in ["class", "def", "if", "for"]) and new_line.endswith("i"):
        #     new_line = new_line[:-1] + ":"

        return new_line, contextual_data
