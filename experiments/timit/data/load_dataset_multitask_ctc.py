#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Load dataset for the multitask CTC model (TIMIT corpus).
   In addition, frame stacking and skipping are used.
   You can use the multi-GPU version.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from os.path import join
import pickle
import numpy as np

from utils.frame_stack import stack_frame
from utils.progressbar import wrap_iterator
from utils.data.multitask_ctc_all_load import DatasetBase


class Dataset(DatasetBase):

    def __init__(self, data_type, label_type_second, batch_size,
                 num_stack=None, num_skip=None,
                 is_sorted=True, is_progressbar=False, num_gpu=1):
        """A class for loading dataset.
        Args:
            data_type: string, train or dev or test
            label_type_second: string, phone39 or phone48 or phone61
            batch_size: int, the size of mini-batch
            num_stack: int, the number of frames to stack
            num_skip: int, the number of frames to skip
            is_sorted: if True, sort dataset by frame num
            is_progressbar: if True, visualize progressbar
            num_gpu: int, if more than 1, divide batch_size by num_gpu
        """
        if data_type not in ['train', 'dev', 'test']:
            raise ValueError('data_type is "train" or "dev" or "test".')

        self.data_type = data_type
        self.label_type_main = 'character'
        self.label_type_second = label_type_second
        self.batch_size = batch_size * num_gpu
        self.num_stack = num_stack
        self.num_skip = num_skip
        self.is_sorted = is_sorted
        self.is_progressbar = is_progressbar
        self.num_gpu = num_gpu

        self.input_size = 123
        self.dataset_main_path = join(
            '/n/sd8/inaguma/corpus/timit/dataset/ctc/character', data_type)
        self.dataset_second_path = join(
            '/n/sd8/inaguma/corpus/timit/dataset/ctc/',
            label_type_second, data_type)

        # Load the frame number dictionary
        with open(join(self.dataset_main_path, 'frame_num.pickle'), 'rb') as f:
            self.frame_num_dict = pickle.load(f)

        # Sort paths to input & label by frame num
        frame_num_tuple_sorted = sorted(self.frame_num_dict.items(),
                                        key=lambda x: x[1])
        input_paths, label_main_paths, label_second_paths = [], [], []
        for input_name, frame_num in frame_num_tuple_sorted:
            input_paths.append(join(
                self.dataset_main_path, 'input', input_name + '.npy'))
            label_main_paths.append(join(
                self.dataset_main_path, 'label', input_name + '.npy'))
            label_second_paths.append(join(
                self.dataset_second_path, 'label', input_name + '.npy'))
        if len(label_main_paths) != len(label_second_paths):
            raise ValueError(
                'The numbers of labels between ' +
                'character and phone are not same.')
        self.input_paths = np.array(input_paths)
        self.label_main_paths = np.array(label_main_paths)
        self.label_second_paths = np.array(label_second_paths)
        self.data_num = len(self.input_paths)

        # Load all dataset in advance
        print('=> Loading ' + data_type +
              ' dataset (' + label_type_second + ')...')
        input_list, label_main_list, label_second_list = [], [], []
        for i in wrap_iterator(range(self.data_num), self.is_progressbar):
            input_list.append(np.load(self.input_paths[i]))
            label_main_list.append(np.load(self.label_main_paths[i]))
            label_second_list.append(np.load(self.label_second_paths[i]))
        self.input_list = np.array(input_list)
        self.label_main_list = np.array(label_main_list)
        self.label_second_list = np.array(label_second_list)

        # Frame stacking
        if (num_stack is not None) and (num_skip is not None):
            print('=> Stacking frames...')
            stacked_input_list = stack_frame(self.input_list,
                                             self.input_paths,
                                             self.frame_num_dict,
                                             num_stack,
                                             num_skip,
                                             is_progressbar)
            self.input_list = np.array(stacked_input_list)
            self.input_size = self.input_size * num_stack

        self.rest = set([i for i in range(self.data_num)])
