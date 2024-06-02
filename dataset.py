#!/bin/env python

"""
File: nsynth.py
Author: Kwon-Young Choi
Email: kwon-young.choi@hotmail.fr
Date: 2018-11-13
Description: Load NSynth dataset using pytorch Dataset.
If you want to modify the output of the dataset, use the transform
and target_transform callbacks as ususal.
"""
import os
import json
import glob
import numpy as np
import scipy.io.wavfile
import torch
import torch.utils.data as data
import torchvision.transforms as transforms
from sklearn.preprocessing import LabelEncoder
import librosa
from tqdm import tqdm
import threading

def multi_threaded_file_reader(file_paths):
    threads = []
    results = []

    # Define the worker function
    def read_file_thread(file_path):
        result = torch.load(file_path, map_location=torch.device('cpu'))
        results.extend(result)

    # Create and start threads
    for file_path in file_paths:
        thread = threading.Thread(target=read_file_thread, args=(file_path,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    return results

class NSynth(data.Dataset):

    """Pytorch dataset for NSynth dataset
    args:
        root: root dir containing examples.json and audio directory with
            wav files.
        transform (callable, optional): A function/transform that takes in
                a sample and returns a transformed version.
        target_transform (callable, optional): A function/transform that takes
            in the target and transforms it.
        blacklist_pattern: list of string used to blacklist dataset element.
            If one of the string is present in the audio filename, this sample
            together with its metadata is removed from the dataset.
        categorical_field_list: list of string. Each string is a key like
            instrument_family that will be used as a classification target.
            Each field value will be encoding as an integer using sklearn
            LabelEncoder.
    """
    def __init__(self, root, transforms=None, target_transform=None,
                 blacklist_pattern=[],
                 categorical_field_list=["instrument_family"]):
        """Constructor"""
        assert(isinstance(root, str))
        assert(isinstance(blacklist_pattern, list))
        assert(isinstance(categorical_field_list, list))
        self.root = root
        self.filenames = glob.glob(os.path.join(root, "audio/*.wav"))
        with open(os.path.join(root, "examples.json"), "r") as f:
            self.json_data = json.load(f)
        for pattern in blacklist_pattern:
            self.filenames, self.json_data = self.blacklist(
                self.filenames, self.json_data, pattern)
        self.categorical_field_list = categorical_field_list
        self.le = []
        for i, field in enumerate(self.categorical_field_list):
            self.le.append(LabelEncoder())
            field_values = [value[field] for value in self.json_data.values()]
            self.le[i].fit(field_values)
        self.transforms = transforms
        self.target_transform = target_transform

        #initialize normalization values
        self.mfcc_max = 341.15484619140625
        self.mfcc_min = -968.44970703125
        self.pitch_max = 2093.004522404789
        self.pitch_min = 0
        self.rms_max = 0.9348938465118408
        self.rms_min = 0

    def blacklist(self, filenames, json_data, pattern):
        filenames = [filename for filename in filenames
                     if pattern not in filename]
        json_data = {
            key: value for key, value in json_data.items()
            if pattern not in key
        }
        return filenames, json_data

    def __len__(self):
        return len(self.filenames)

    def __getitem__(self, index):
        """
        Args:
            index (int): Index
        Returns:
            tuple: (audio sample, *categorical targets, json_data)
        """
        name = self.filenames[index]
        # sample, sr = librosa.load(name, sr=44100)
        # frame_size = len(sample)

        z = torch.from_numpy(np.load(name[:-4] + "_z.npy"))
        mfcc = torch.from_numpy(np.load(name[:-4] + "_mfcc.npy"))
        pyin = torch.from_numpy(np.load(name[:-4] + "_pitch.npy"))
        rms = torch.from_numpy(np.load(name[:-4] + "_rms.npy"))
        # target = self.json_data[os.path.splitext(os.path.basename(name))[0]]
        # categorical_target = [
        #     le.transform([target[field]])[0]
        #     for field, le in zip(self.categorical_field_list, self.le)]
        # if self.transforms is not None:
        #     for transform in self.transforms:
        #         match transform:
        #             case librosa.feature.mfcc:
        #                 mfcc = torch.tensor(transform(y=sample, sr = sr))
        #             case librosa.pyin:
        #                 pyin, _, _ = transform(y=sample, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'), sr = sr, fill_na=0.0)
        #                 pyin = torch.tensor(pyin).unsqueeze(0)
        #             case librosa.feature.rms:
        #                 rms = torch.tensor(transform(y=sample))
        # if self.target_transform is not None:
        #     target = self.target_transform(target)

        #normalize data
        mfcc = (mfcc - self.mfcc_min) / ( self.mfcc_max -self.mfcc_min)
        pyin = (pyin - self.pitch_min) / (self.pitch_max - self.pitch_min) 
        # rms = (rms - rms_min) / (rms_max - rms_min)
        
        return [z, mfcc, pyin, rms]

class NSynth_ram(data.Dataset):

    """Pytorch dataset for NSynth dataset
    args:
        root: root dir containing examples.json and audio directory with
            wav files.
        transform (callable, optional): A function/transform that takes in
                a sample and returns a transformed version.
        target_transform (callable, optional): A function/transform that takes
            in the target and transforms it.
        blacklist_pattern: list of string used to blacklist dataset element.
            If one of the string is present in the audio filename, this sample
            together with its metadata is removed from the dataset.
        categorical_field_list: list of string. Each string is a key like
            instrument_family that will be used as a classification target.
            Each field value will be encoding as an integer using sklearn
            LabelEncoder.
    """
    def __init__(self, files):
        """Constructor"""
        self.data = multi_threaded_file_reader(files)

        #initialize normalization values
        self.mfcc_max = 341.15484619140625
        self.mfcc_min = -968.44970703125
        self.pitch_max = 2093.004522404789
        self.pitch_min = 0
        self.rms_max = 0.9348938465118408
        self.rms_min = 0


    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        """
        Args:
            index (int): Index
        Returns:
            tuple: (audio sample, *categorical targets, json_data)
        """

        d_index = self.data[index]

        z = d_index[0]
        mfcc = d_index[1]
        pyin = d_index[2]
        rms = d_index[3]

        #normalize data
        mfcc = (mfcc - self.mfcc_min) / ( self.mfcc_max -self.mfcc_min)
        pyin = (pyin - self.pitch_min) / (self.pitch_max - self.pitch_min) 
        # rms = (rms - rms_min) / (rms_max - rms_min)
        
        return [z[0], mfcc[0], pyin[0], rms[0]]


if __name__ == "__main__":
    # audio samples are loaded as an int16 numpy array
    # rescale intensity range as float [-1, 1]
    toFloat = transforms.Lambda(lambda x: x / np.iinfo(np.int16).max)
    # use instrument_family and instrument_source as classification targets
    dataset = NSynth(
        "/vast/df2322/data/Nsynth/nsynth-test",
        transforms = [librosa.feature.mfcc, librosa.pyin, librosa.feature.rms],
        blacklist_pattern=["string"],  # blacklist string instrument
        categorical_field_list=["instrument_family", "instrument_source"])
    loader = data.DataLoader(dataset, batch_size=32, shuffle=True)
    for samples, mfcc, pyin, rms in loader:
        print(samples.shape, mfcc.shape, pyin.shape, rms.shape)
        print(torch.min(samples), torch.max(samples))