# coding=utf-8
# Copyright 2018 The TensorFlow Datasets Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for tensorflow_datasets.core.dataset_builder."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

import tensorflow as tf
from tensorflow_datasets.core import dataset_builder
from tensorflow_datasets.core import dataset_info
from tensorflow_datasets.core import features
from tensorflow_datasets.core import registered
from tensorflow_datasets.core import splits
from tensorflow_datasets.core import test_utils

tf.enable_eager_execution()


class DummyDatasetSharedGenerator(dataset_builder.GeneratorBasedDatasetBuilder):

  def _split_generators(self, dl_manager):
    # Split the 30 examples from the generator into 2 train shards and 1 test
    # shard.
    del dl_manager
    return [splits.SplitGenerator(
        name=[splits.Split.TRAIN, splits.Split.TEST],
        num_shards=[2, 1],
    )]

  def _info(self):
    return dataset_info.DatasetInfo(
        specs=features.SpecDict({"x": tf.int64}),
    )

  def _generate_samples(self):
    for i in range(30):
      yield self.info.specs.encode_sample({"x": i})


class DatasetBuilderTest(tf.test.TestCase):

  def test_shared_generator(self):
    with test_utils.tmp_dir(self.get_temp_dir()) as tmp_dir:
      builder = DummyDatasetSharedGenerator(data_dir=tmp_dir)
      builder.download_and_prepare()

      written_filepaths = [
          os.path.join(builder._data_dir, fname)
          for fname in tf.gfile.ListDirectory(builder._data_dir)
      ]
      # The data_dir contains the cached directory by default
      expected_filepaths = builder._build_split_filenames(
          data_dir=builder._data_dir,
          split_info_list=builder.info.splits.values())
      expected_filepaths.append(
          os.path.join(builder._data_dir, "dataset_info.json"))
      self.assertEqual(sorted(expected_filepaths), sorted(written_filepaths))

      splits_list = [
          splits.Split.TRAIN, splits.Split.TEST
      ]
      datasets = [builder.as_dataset(split=split) for split in splits_list]
      data = [[el["x"].numpy() for el in dataset] for dataset in datasets]

      train_data, test_data = data
      self.assertEqual(20, len(train_data))
      self.assertEqual(10, len(test_data))
      self.assertEqual(list(range(30)), sorted(train_data + test_data))

  def test_load(self):
    with test_utils.tmp_dir(self.get_temp_dir()) as tmp_dir:
      dataset = registered.load(
          name="dummy_dataset_shared_generator",
          data_dir=tmp_dir,
          download=True,
          split=splits.Split.TRAIN)
      data = list(dataset)
      self.assertEqual(20, len(data))

  def test_numpy_iterator(self):
    with test_utils.tmp_dir(self.get_temp_dir()) as tmp_dir:
      builder = DummyDatasetSharedGenerator(data_dir=tmp_dir)
      builder.download_and_prepare()
      items = []
      for item in builder.numpy_iterator(split=splits.Split.TRAIN):
        items.append(item)
      self.assertEqual(20, len(items))


if __name__ == "__main__":
  tf.test.main()
