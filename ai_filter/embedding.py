from Hangulpy import decompose, is_hangul
import csv
import torch
import torch.nn as nn
import pickle
from pathlib import Path

jamo_dictionary = {}

def decompose_string(text):
    """한글 문자열을 자모 단위로 분해"""
    return [decompose(c) for c in text if is_hangul(c)]

def add_to_dict(decomposed):
    """자모를 사전에 추가"""
    for syllable in decomposed:
        for jamo in syllable:
            if jamo not in jamo_dictionary:
                jamo_dictionary[jamo] = len(jamo_dictionary) + 1

def to_index_array(decomposed, jamo_dict):
    """자모를 인덱스 배열로 변환"""
    return [jamo_dict[jamo] for syllable in decomposed for jamo in syllable]

def padding(arr, max_len):
    """패딩을 추가하여 배열의 길이를 고정"""
    return arr[:max_len] + [0] * max(0, max_len - len(arr))

def to_embedded_tensor(filename):
    """CSV 파일을 읽어 문자열을 자모 단위로 분해하고 임베딩 벡터로 변환"""
    strings = []
    labels = []

    with open(filename, 'r') as f:
        rdr = csv.reader(f)
        for line in rdr:
            label = int(line[0])
            s = line[1]
            decomposed = decompose_string(s)

            add_to_dict(decomposed)
            strings.append(decomposed)
            labels.append(label)

    # 각 문자열을 인덱스 배열로 변환
    strings = [to_index_array(s, jamo_dictionary) for s in strings]

    # 최장 길이 문자열에 맞춰 패딩
    maxlen = max(len(s) for s in strings)
    strings = [padding(s, maxlen) for s in strings]

    # jamo_dictionary를 pickle로 저장
    with open('jamo.pydict', 'wb') as f:
        pickle.dump(jamo_dictionary, f)

    # PyTorch 텐서로 변환
    strings_tensor = torch.LongTensor(strings)
    labels_tensor = torch.FloatTensor(labels)

    return strings_tensor, labels_tensor, len(jamo_dictionary) + 1
