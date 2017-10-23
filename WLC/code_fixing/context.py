import keyword

from fuzzysearch import find_near_matches

KW_LIST = keyword.kwlist + ["print", "list", "dict", "set", "file", "open", "assert", "range"]


def word_context_analysis(characters, contextual_data=None, prev_context=False):
    if not contextual_data:
        contextual_data = []

    word = "".join(character.get_code(get_letters=False).lower() for character in characters)

    if prev_context == "import":  # no numbers -> replace possibly similar matches.
        word = "".join(character.get_code(get_letters=True).lower() for character in characters)
        contextual_data.append(word)  # add the imported module to contextual
        return word

    elif not prev_context:
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
                    if end < p.end or (end == p.end and p.dist < l_dist and not (curr_best_word in contextual_data and kw in KW_LIST)):
                        end = p.end
                        curr_best_match = p
                        curr_best_word = kw
                        l_dist = p.dist

        if curr_best_match and curr_best_word:
            new_word = word[:start] + curr_best_word + word[end:]
            word = new_word

    return word
