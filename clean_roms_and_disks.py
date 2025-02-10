#!/usr/bin/python

# based on https://github.com/grayaii/rom_cleaner

# NOTE: I am in the process of rewriting this to make it more readable,
# testable, optimized. Right now I just added features and tuned
# existing ones mostly on top of the old code.

import re
import os
import argparse
from functools import reduce
from copy import deepcopy

# NOTE: this `WEIGHTS` list expresses preferences for:
# * Italian
# * English
# * European verisons

# http://www.theisozone.com/tutorials/other/general/know-your-roms-a-guide-to-identifying-the-symbols/
WEIGHTS = [
    {"token": "[a]", "weight": 9, "description": "Alternate"},
    {"token": "[b]", "weight": -99, "description": "Bad Dump"},
    {"token": "[BF]", "weight": 7, "description": "Bug Fix"},
    {"token": "[c]", "weight": 8, "description": "Cracked"},
    {"token": "[f]", "weight": 6, "description": "Other Fix"},
    {"token": "[h]", "weight": 5, "description": "Hack"},
    {"token": "[o]", "weight": 10, "description": "Overdump"},
    {"token": "[p]", "weight": 4, "description": "Pirate"},
    {"token": "[t]", "weight": 3, "description": "Trained"},
    {"token": "[T]", "weight": 2, "description": "Translation"},
    {"token": "(Unl)", "weight": 1, "description": "Unlicensed"},
    {"token": "(early)", "weight": 2, "description": "Early release"},
    {
        "token_re": "v\\s?[0-9]+.*",
        "weight": 2,
        "description": "Specific version",
    },
    {
        "token_re": "Alt [0-9]+",
        "weight": 2,
        "description": "Alternative version",
    },
    {"token_re": "Rev [0-9]+", "weight": 2, "description": "Revision"},
    {"token_re": "Debug.*", "weight": 1, "description": "Debug version"},
    {"token": "(Kiosk)", "weight": 2, "description": "Kiosk version"},
    {"token": "(Demo)", "weight": -99, "description": "Demo"},
    {"token": "(Beta)", "weight": -99, "description": "Beta"},
    {"token": "[x]", "weight": -99, "description": "Bad Checksum"},
    {"token": "[!]", "weight": 100, "description": "Verified Good Dump"},
    {"token": "(a)", "weight": 80, "description": "Australian"},
    {"token": "(Aus)", "weight": 80, "description": "Australian"},
    {"token": "(Australia)", "weight": 80, "description": "Australian"},
    {"token": "(Brazil)", "weight": 0, "description": "Brazilian"},
    {"token": "(C)", "weight": 0, "description": "Chinese"},
    {"token": "(China)", "weight": 0, "description": "Chinese"},
    {"token": "(E)", "weight": 0, "description": "Europe"},
    {"token": "(EU)", "weight": 0, "description": "Europe"},
    {"token": "(Europe)", "weight": 0, "description": "Europe"},
    {"token": "(F)", "weight": 0, "description": "French"},
    {"token": "(Fr)", "weight": 0, "description": "French"},
    {"token": "(France)", "weight": 0, "description": "French"},
    {"token": "(FN)", "weight": 0, "description": "Finland"},
    {"token": "(G)", "weight": 0, "description": "German"},
    {"token": "(De)", "weight": 0, "description": "German"},
    {"token": "(Germany)", "weight": 0, "description": "German"},
    {"token": "(GR)", "weight": 0, "description": "Greece"},
    {"token": "(HK)", "weight": 0, "description": "Hong Kong"},
    {"token": "(Taiwan)", "weight": 0, "description": "Taiwan"},
    {
        "token_re": r"It\+[A-Z][a-z]",
        "weight": 1,
        "description": "Italian",
    },
    {"token_re": r"[A-Z][a-z]\+It", "weight": 0, "description": "Italian"},
    {"token": "(I)", "keep": True, "weight": 0, "description": "Italian"},
    {"token": "(It)", "weight": 0, "description": "Italian"},
    {"token": "(Italy)", "keep": True, "weight": 0, "description": "Italian"},
    {"token": "(J)", "weight": 0, "description": "Japan"},
    {"token": "(Ja)", "weight": 0, "description": "Japan"},
    {"token": "(Japan)", "weight": 0, "description": "Japan"},
    {"token": "(K)", "weight": 0, "description": "Korean"},
    {"token": "(Korea)", "weight": 0, "description": "Korean"},
    {"token": "(PD)", "weight": 80, "description": "Public Domain"},
    {"token": "(S)", "weight": 0, "description": "Spanish"},
    {"token": "(Es)", "weight": 0, "description": "Spanish"},
    {"token": "(Spain)", "weight": 0, "description": "Spanish"},
    {"token": "(Sweden)", "weight": 0, "description": "Sweden"},
    {"token": "(SW)", "weight": 0, "description": "Sweden"},
    {"token": "(NL)", "weight": 0, "description": "Dutch"},
    {"token": "(Nl)", "weight": 0, "description": "Dutch"},
    {"token": "(Netherlands)", "weight": 0, "description": "Dutch"},
    {"token": "(U)", "weight": 95, "description": "USA"},
    {'token': '(USA, Europe)',   'weight': 94,  'description': 'USA, Europe'},
    {'token': '(Japan, USA)',  'weight': 93,  'description': 'Japan, USA'},
    {"token": "(USA)", "weight": 95, "description": "USA"},
    {"token_re": r"En\+[A-Z][a-z]", "weight": 90, "description": "English"},
    {"token_re": r"[A-Z][a-z]\+En", "weight": 90, "description": "English"},
    {"token": "(En)", "weight": 95, "description": "English"},
    {"token": "(UK)", "weight": 90, "description": "England"},
    {"token": "(World)", "weight": 1, "description": "International"},
    {"token": "(Worlds)", "weight": 1, "description": "International"},
    {"token": "(Unk)", "weight": 0, "description": "Unknown Country"},
    {"token": "(Proto)", "weight": 10, "description": "Prototype"},
    {"token": "(Promo)", "weight": 10, "description": "Promo"},
    {"token": "(Sample)", "weight": 0, "description": "Sample"},
    {"token": "(Sv)", "weight": 0, "description": "Unknown"},
    {"token": "(No)", "weight": 0, "description": "Unknown"},
    {"token": "(Da)", "weight": 0, "description": "Unknown"},
    {"token": "(Pt)", "weight": 0, "description": "Unknown"},
    {"token": "(Fi)", "weight": 0, "description": "Unknown"},
    {"token": "(-)", "weight": 0, "description": "Unknown Country"},
    # {"token": "(Sachen-USA)", "weight":10, "description": ""},
    # {"token": "(Sachen-English)", "weight": 10, "description": ""},
    {'token': '(Sachen-USA)', 'weight':10, 'description': 'found it'},
    {'token': '(Sachen-English)', 'weight':10, 'description': 'found it'}
    ]


LOW_TH = -200
RENAME_ACTION = "rename"
DELETE_ACTION = "delete"


def get_compiled_rule(rule):
    compiled_rule = deepcopy(rule)
    compiled_rule["token_re"] = re.compile(rule["token_re"], re.I)
    return compiled_rule


re_weights = list(filter(lambda x: x.get("token_re"), WEIGHTS))

compiled_re_weights = reduce(
    lambda x, y: x + [get_compiled_rule(y)], re_weights, []
)

tokens_re = re.compile(r"(?:\(.*?\))|(?:\[.*?\])")


class RomsManager:
    def __init__(self, roms, action, only_one):
        self.action = action
        self.only_one = only_one
        self.roms = roms
        self._actions = {
            DELETE_ACTION: self.delete,
            RENAME_ACTION: self.rename,
        }

    def execute_action(self, action, path):
        self._actions[action](path)

    @staticmethod
    def delete(file_path):
        print("\tDeleting: {}".format(file_path))
        os.remove(file_path)

    @staticmethod
    def rename(file_path):
        orig_path = os.path.split(file_path)
        new_path = os.path.join(orig_path[0], ".{}".format(orig_path[1]))
        print("\tRenaming: {} to {}".format(file_path, new_path))
        os.rename(file_path, new_path)

    def clean(self):
        total_files = 0
        for stripped_filename, roms in self.roms.items():
            if len(roms) <= 1:
                continue

            print(stripped_filename)
            prev_weight = None

            for r in sorted(roms, key=lambda x: x.weight, reverse=True):
                total_files += 1
                if r.weight > LOW_TH:
                    if prev_weight is None:
                        print("\t:OK:{}:{}".format(r.weight, r.base_filename))
                        prev_weight = r.weight
                        continue
                    if prev_weight == r.weight and not self.only_one:
                        print("\t:OK:{}:{}".format(r.weight, r.base_filename))
                        continue

                print("\t:KO:{}:{}".format(r.weight, r.base_filename))
                if r.keep:
                    print("\t ^ Kept")
                    continue

                if self.action:
                    self.execute_action(self.action, r.rom_full_path)

        print("total unique files: {}".format(len(self.roms)))
        print("total files       : {}".format(total_files))


class Rom:
    penalty = -2  # more tokens => lower score

    def __init__(self, rom_full_path, check_keep):
        # super mario (hack) (!).nes:
        self.rom_full_path = rom_full_path
        self.check_keep = check_keep
        self.keep = False
        rom_basename = os.path.basename(rom_full_path)
        self.stripped_filename = self.get_stripped_filename(rom_basename)
        self.base_filename = rom_basename
        self.tokens = self.subtokenize(rom_basename)
        self.weight = self.calculate_weight()

    @staticmethod
    def subtokenize(string):
        token_matches = tokens_re.findall(string)

        for token_match in token_matches:
            opening_bracket = token_match[0]
            closing_bracket = token_match[-1]
            inner_string = token_match[1:-1]

            inner_string = inner_string.replace(", ", ",")
            sub_tokens = inner_string.split(",")

            yield from (
                "{}{}{}".format(
                    opening_bracket, sub_token.strip(), closing_bracket
                )
                for sub_token in sub_tokens
            )

    @staticmethod
    def get_stripped_filename(rom_basename):
        filename, ext = os.path.splitext(tokens_re.sub("", rom_basename))
        return "{}{}".format(filename.strip(), ext)

    def get_token_weight(self, token):
        rule = None

        try:
            rule = next(
                filter(
                    lambda x: x.get("token", "").lower() == token.lower(),
                    WEIGHTS,
                )
            )
        except StopIteration:
            pass

        try:
            rule = next(
                filter(
                    lambda x: x["token_re"].match(token[1:-1]),
                    compiled_re_weights,
                )
            )
        except StopIteration:
            pass

        if rule:
            return rule["weight"] + self.penalty

        if self.check_keep:
            self.keep = True

        return self.penalty

    def calculate_weight(self):
        return reduce(
            lambda x, y: x + self.get_token_weight(y), self.tokens, 0
        )


# Parse command line args:
def parseArgs():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--roms-dir",
        "--rom_dir",
        dest="roms_dir",
        help="Location where roms are stored",
        default=".",
    )
    parser.add_argument(
        "--one",
        help=(
            "Keep only one rom per title if"
            " there are more with the same weight"
        ),
        action="store_true",
    )
    parser.add_argument(
        "--keep",
        dest="keep_unkn_tags",
        help="Keep ROMs with unrecognized tags",
        action="store_true",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--rename",
        help="Rename duplicates adding a leading dot (.)",
        dest="action",
        const=RENAME_ACTION,
        action="store_const",
    )
    group.add_argument(
        "--delete",
        help="WARNING: this will delete the duplicate ROMs!",
        dest="action",
        const=DELETE_ACTION,
        action="store_const",
    )
    args = parser.parse_args()
    return args


def walk_roms(root_dir, keep_unkn_tags):
    for dirname, _, filenames in os.walk(root_dir):
        for filename in sorted(filenames, reverse=True):
            yield Rom(os.path.join(dirname, filename), keep_unkn_tags)


def make_roms_collection(roms):
    # {'test': [<__main__.Rom object at 0x7efcf097cc40>, ... ]}
    rom_collection = {}
    for rom in roms:
        filename = rom.stripped_filename
        if filename not in rom_collection:
            rom_collection[filename] = []
        rom_collection[filename].append(rom)
    return rom_collection


if __name__ == "__main__":
    args = parseArgs()
    roms_dir = args.roms_dir
    action = args.action

    print("> Running on {}".format(roms_dir))
    if action is None:
        print("> Runnin in dry run mode")

    roms = make_roms_collection(walk_roms(roms_dir, args.keep_unkn_tags))

    all_roms = RomsManager(roms, action, args.one)
    all_roms.clean()
    print("all done!")
