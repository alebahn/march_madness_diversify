#!/usr/bin/env python3

import sys
import csv
import time
from itertools import islice
from random import random

def batched(iterable, n):
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch

SCORE_SCHEME = [2,4,8,16,20,24]
# MCS_ITTERATIONS = 1
MCS_ITTERATIONS = 100000

def condition_odds(odds, last_row = -1):
    if last_row == -1:
        last_row = len(odds[0]) - 1
    total = sum(row[last_row] for row in odds)

    for row in odds:
        for i in range(last_row):
            row[i] = row[i] - row[last_row]
        row[last_row] = row[last_row] / total

    if last_row != 0:
        half = len(odds) // 2
        condition_odds(odds[:half], last_row - 1)
        condition_odds(odds[half:], last_row - 1)

def generate_mcs(odds, pick=None):
    if not odds[0]:
        return []
    if pick is None:
        rand = random()
        for i, row in enumerate(odds):
            finals_chance = row[-1]
            if rand < finals_chance:
                pick = i
                break
            rand = rand - finals_chance
    assert pick is not None, "should have pick here"
    half = len(odds) // 2
    trunc_odds = [row[:-1] for row in odds]
    if pick < half:
        lower_picks = generate_mcs(trunc_odds[:half], pick)
        upper_picks = generate_mcs(trunc_odds[half:])
    else:
        lower_picks = generate_mcs(trunc_odds[:half])
        upper_picks = generate_mcs(trunc_odds[half:], pick - half)
    picks = [lower + (upper << half) for lower, upper in zip(lower_picks, upper_picks)]
    picks.append(1 << pick)
    # print(picks)
    return picks

def iter_round(round_num):
    index=0
    while(round_num):
        if round_num & 1:
            yield index
        index = index + 1
        round_num = round_num >> 1

def mcs_odds(matches):
    match_1 = matches[0]
    # counts = [[0 for _ in range(len(match_1[0]) * 2)] for _ in match_1]
    counts = [[0 for _ in match_1] for _ in range(len(match_1[0]) * 2)]
    for match_ in matches:
        for i, round in enumerate(match_):
            for winner in iter_round(round):
                counts[winner][i] = counts[winner][i] + 1
    return [[count / len(matches) for count in team] for team in counts]

def expected_chaulk(odds, score_scheme):
    result = 0.0
    top = [0.0 for _ in score_scheme]
    for i, row in enumerate(odds):
        top = [max(a, b) for a, b in zip(top, row)]
        for j, big in enumerate(top):
            if (i + 1) % (2 ** (j + 1)) == 0:
                result += score_scheme[j] * big
                top[j] = 0.0
    return result

def generate_chaulk(odds, pick=None):
    if not pick:
        top = 0.0
        for i, row in enumerate(odds):
            if not row:
                return []
            if row[-1] > top:
                top = row[-1]
                pick = i
    half = len(odds) // 2
    trunc_odds = [row[:-1] for row in odds]
    if pick < half:
        lower_picks = generate_chaulk(trunc_odds[:half], pick)
        upper_picks = generate_chaulk(trunc_odds[half:])
    else:
        lower_picks = generate_chaulk(trunc_odds[:half])
        upper_picks = generate_chaulk(trunc_odds[half:], pick - half)
    picks = [lower + (upper << half) for lower, upper in zip(lower_picks, upper_picks)]
    picks.append(1 << pick)
    return picks

def expected_score(picks, matches, score_scheme):
    total_score = 0
    for match_ in matches:
        for p_round, m_round, round_points in zip(picks, match_, score_scheme):
            total_score = total_score + (p_round & m_round).bit_count() * round_points
    return total_score / len(matches)

def expected_max(picks1, picks2, matches, score_scheme, score_scheme2 = None):
    score_scheme2 = score_scheme2 or score_scheme
    total_score = 0
    for match_ in matches:
        match_score1 = 0
        match_score2 = 0
        for p1_round, p2_round, m_round, round_points1, round_points2 in zip(picks1, picks2, match_, score_scheme, score_scheme2):
            match_score1 = match_score1 + (p1_round & m_round).bit_count() * round_points1
            match_score2 = match_score2 + (p2_round & m_round).bit_count() * round_points2
        total_score = total_score + max(match_score1, match_score2)
    return total_score / len(matches)

def generate_canidates(odds, counts, pick=None):
    if not counts:
        yield []
        return
    if pick is None:
        picks = sorted(range(len(odds)), reverse=True, key=lambda p: odds[p][-1])[:counts[-1]]
    else:
        picks = [pick]
    half = len(odds) // 2
    trunc_odds = [row[:-1] for row in odds]
    trunc_counts = counts[:-1]
    for pick in picks:
        if pick < half:
            lower_brackets = generate_canidates(trunc_odds[:half], trunc_counts, pick)
            upper_brackets = generate_canidates(trunc_odds[half:], trunc_counts)
        else:
            lower_brackets = generate_canidates(trunc_odds[:half], trunc_counts)
            upper_brackets = generate_canidates(trunc_odds[half:], trunc_counts, pick - half)
        for lower_picks in lower_brackets:
            for upper_picks in upper_brackets:
                bracket = [lower + (upper << half) for lower, upper in zip(lower_picks, upper_picks)]
                bracket.append(1 << pick)
                yield bracket

def optimize_max(odds, matches, chaulk_bracket, score_scheme, score_scheme2=None):
    score_scheme2 = score_scheme2 or score_scheme
    top_pick = (0.0, [])
    start_time = time.perf_counter()
    # for i, bracket in enumerate(generate_canidates(odds, [1, 1, 2, 4, 16, 16])):
    for i, bracket in enumerate(generate_canidates(odds, [1, 1, 1, 2, 4, 4])):
        score = expected_max(chaulk_bracket, bracket, matches, score_scheme, score_scheme2)
        if score > top_pick[0]:
            top_pick = (score, bracket)
        # sys.stdout.write("\r")
        # sys.stdout.write(f"checked bracket {i+1}/{4**3}")
        # sys.stdout.flush()
    end_time = time.perf_counter()
    # print()
    print(f"elapsed time: {end_time - start_time}")
    return top_pick

def ind_round(round_num, index):
    return list(iter_round(round_num))[index]

def print_bracket(bracket, names):
    names = list(names)
    max_width = max(len(name) for name in names)
    bracket = [(1 << len(names)) - 1, *bracket]
    for i in range(1, len(names) * 2):
        binary = bin(i)
        prefix = binary.rstrip('0')
        zero_count = len(binary) - len(prefix)
        print(f"{' '*4*zero_count}{names[ind_round(bracket[zero_count], int(prefix, 2)//2)]}")

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} odds.csv")
        exit(1)
    odds_filename = sys.argv[1]
    print(f"odds filename: {odds_filename}")
    odds_data={}
    with open(odds_filename, 'r') as odds_file:
        odds_reader = csv.reader(odds_file)
        next(odds_reader) #skip field names
        for row in odds_reader:
            if len(row[0])==0:
                continue
            odds_data[row[0]] = [float(v) if v else 0.0 for v in row[1:]]
    print(f"{len(odds_data)} rows processed")
    for batch in batched(odds_data.values(), 32):
        total = sum(row[-1] for row in batch)
        for row in batch:
            row[-2] = row[-1]/total
    # print(odds_data)
    expectation = expected_chaulk(odds_data.values(), SCORE_SCHEME)
    print(f"expected score for chaulk bracket: {expectation}")
    conditional_odds = list(row[:] for row in odds_data.values())
    condition_odds(conditional_odds)
    matches = [generate_mcs(conditional_odds) for _ in range(MCS_ITTERATIONS)]
    # matches = [generate_mcs(odds_data.values()) for _ in range(1)]
    print(f"{len(matches)} generated.")
    # print(matches[0])
    # odds2 = mcs_odds(matches)
    # print(list(odds_data.values()))
    # print(odds2)
    chaulk_picks = generate_chaulk(odds_data.values())
    print(chaulk_picks)
    print_bracket(chaulk_picks, odds_data.keys())
    mcs_expectation = expected_score(chaulk_picks, matches, SCORE_SCHEME)
    print(f"mcs expectation: {mcs_expectation}")
    expectation_max, alt_pick = optimize_max(list(odds_data.values()), matches, chaulk_picks, SCORE_SCHEME)
    mcs_expectation = expected_score(alt_pick, matches, SCORE_SCHEME)
    print(f"mcs expectation: {mcs_expectation}")
    print(f"expectation(max(chaulk, alt)): {expectation_max}")
    print_bracket(alt_pick, odds_data.keys())

if __name__ == "__main__":
    main()
