#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 1999-2020 Alibaba Group Holding Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
import scipy.sparse as sps

from mars.tiles import get_tiled
from mars.tensor.datasource import tensor, arange, zeros
from mars.tensor.indexing import take, compress, extract, choose, \
    unravel_index, nonzero, flatnonzero, fill_diagonal
from mars.tensor import mod, stack, hstack
from mars.config import options
from mars.tests.core import ExecutorForTest, TestBase


class Test(TestBase):
    def setUp(self):
        self.executor = ExecutorForTest('numpy')
        self.old_chunk = options.chunk_size
        options.chunk_size = 10

    def tearDown(self):
        options.chunk_size = self.old_chunk

    def testBoolIndexingExecution(self):
        raw = np.random.random((11, 8, 12, 14))
        arr = tensor(raw, chunk_size=3)

        index = arr < .5
        arr2 = arr[index]
        size_res = self.executor.execute_tensor(arr2, mock=True)
        res = self.executor.execute_tensor(arr2)

        self.assertEqual(sum(s[0] for s in size_res), arr.nbytes)
        np.testing.assert_array_equal(np.sort(np.concatenate(res)), np.sort(raw[raw < .5]))

        index2 = tensor(raw[:, :, 0, 0], chunk_size=3) < .5
        arr3 = arr[index2]
        res = self.executor.execute_tensor(arr3, concat=True)[0]

        expected = raw[raw[:, :, 0, 0] < .5]
        self.assertEqual(sum(it.size for it in res), expected.size)
        self.assertEqual(res.shape, expected.shape)

        raw = np.asfortranarray(np.random.random((11, 8, 12, 14)))
        arr = tensor(raw, chunk_size=3)

        index = tensor(raw[:, :, 0, 0], chunk_size=3) < .5
        arr2 = arr[index]
        res = self.executor.execute_tensor(arr2, concat=True)[0]
        expected = raw[raw[:, :, 0, 0] < .5].copy('A')

        self.assertEqual(res.flags['C_CONTIGUOUS'], expected.flags['C_CONTIGUOUS'])
        self.assertEqual(res.flags['F_CONTIGUOUS'], expected.flags['F_CONTIGUOUS'])

    def testFancyIndexingNumpyExecution(self):
        # test fancy index of type numpy ndarray
        raw = np.random.random((11, 8, 12, 14))
        arr = tensor(raw, chunk_size=(2, 5, 7, 8))

        index = [9, 10, 3, 1, 8, 10]
        arr2 = arr[index]

        res = self.executor.execute_tensor(arr2, concat=True)[0]
        np.testing.assert_array_equal(res, raw[index])

        index = np.random.permutation(8)
        arr3 = arr[:2, ..., index]

        res = self.executor.execute_tensor(arr3, concat=True)[0]
        np.testing.assert_array_equal(res, raw[:2, ..., index])

        index = [1, 3, 9, 10]
        arr4 = arr[..., index, :5]

        res = self.executor.execute_tensor(arr4, concat=True)[0]
        np.testing.assert_array_equal(res, raw[..., index, :5])

        index1 = [8, 10, 3, 1, 9, 10]
        index2 = [1, 3, 9, 10, 2, 7]
        arr5 = arr[index1, :, index2]

        res = self.executor.execute_tensor(arr5, concat=True)[0]
        np.testing.assert_array_equal(res, raw[index1, :, index2])

        index1 = [1, 3, 5, 7, 9, 10]
        index2 = [1, 9, 9, 10, 2, 7]
        arr6 = arr[index1, :, index2]

        res = self.executor.execute_tensor(arr6, concat=True)[0]
        np.testing.assert_array_equal(res, raw[index1, :, index2])
        # fancy index is ordered, no concat required
        self.assertGreater(len(get_tiled(arr6).nsplits[0]), 1)

        index1 = [[8, 10, 3], [1, 9, 10]]
        index2 = [[1, 3, 9], [10, 2, 7]]
        arr7 = arr[index1, :, index2]

        res = self.executor.execute_tensor(arr7, concat=True)[0]
        np.testing.assert_array_equal(res, raw[index1, :, index2])

        index1 = [[1, 3], [3, 7], [7, 7]]
        index2 = [1, 9]
        arr8 = arr[0, index1, :, index2]

        res = self.executor.execute_tensor(arr8, concat=True)[0]
        np.testing.assert_array_equal(res, raw[0, index1, :, index2])

    def testFancyIndexingTensorExecution(self):
        # test fancy index of type tensor

        raw = np.random.random((11, 8, 12, 14))
        arr = tensor(raw, chunk_size=(6, 5, 7, 8))

        raw_index = [8, 10, 3, 1, 9, 10]
        index = tensor(raw_index, chunk_size=4)
        arr2 = arr[index]

        res = self.executor.execute_tensor(arr2, concat=True)[0]
        np.testing.assert_array_equal(res, raw[raw_index])

        raw_index = np.random.permutation(8)
        index = tensor(raw_index, chunk_size=3)
        arr3 = arr[:2, ..., index]

        res = self.executor.execute_tensor(arr3, concat=True)[0]
        np.testing.assert_array_equal(res, raw[:2, ..., raw_index])

        raw_index = [1, 3, 9, 10]
        index = tensor(raw_index)
        arr4 = arr[..., index, :5]

        res = self.executor.execute_tensor(arr4, concat=True)[0]
        np.testing.assert_array_equal(res, raw[..., raw_index, :5])

        raw_index1 = [8, 10, 3, 1, 9, 10]
        raw_index2 = [1, 3, 9, 10, 2, 7]
        index1 = tensor(raw_index1, chunk_size=4)
        index2 = tensor(raw_index2, chunk_size=3)
        arr5 = arr[index1, :, index2]

        res = self.executor.execute_tensor(arr5, concat=True)[0]
        np.testing.assert_array_equal(res, raw[raw_index1, :, raw_index2])

        raw_index1 = [1, 3, 5, 7, 9, 10]
        raw_index2 = [1, 9, 9, 10, 2, 7]
        index1 = tensor(raw_index1, chunk_size=3)
        index2 = tensor(raw_index2, chunk_size=4)
        arr6 = arr[index1, :, index2]

        res = self.executor.execute_tensor(arr6, concat=True)[0]
        np.testing.assert_array_equal(res, raw[raw_index1, :, raw_index2])

        raw_index1 = [[8, 10, 3], [1, 9, 10]]
        raw_index2 = [[1, 3, 9], [10, 2, 7]]
        index1 = tensor(raw_index1)
        index2 = tensor(raw_index2, chunk_size=2)
        arr7 = arr[index1, :, index2]

        res = self.executor.execute_tensor(arr7, concat=True)[0]
        np.testing.assert_array_equal(res, raw[raw_index1, :, raw_index2])

        raw_index1 = [[1, 3], [3, 7], [7, 7]]
        raw_index2 = [1, 9]
        index1 = tensor(raw_index1, chunk_size=(2, 1))
        index2 = tensor(raw_index2)
        arr8 = arr[0, index1, :, index2]

        res = self.executor.execute_tensor(arr8, concat=True)[0]
        np.testing.assert_array_equal(res, raw[0, raw_index1, :, raw_index2])

        raw_a = np.random.rand(30, 30)
        a = tensor(raw_a, chunk_size=(13, 17))
        b = a.argmax(axis=0)
        c = a[b, arange(30)]
        res = self.executor.execute_tensor(c, concat=True)[0]

        np.testing.assert_array_equal(res, raw_a[raw_a.argmax(axis=0), np.arange(30)])

        # test one chunk
        arr = tensor(raw, chunk_size=20)

        raw_index = [8, 10, 3, 1, 9, 10]
        index = tensor(raw_index, chunk_size=20)
        arr9 = arr[index]

        res = self.executor.execute_tensor(arr9, concat=True)[0]
        np.testing.assert_array_equal(res, raw[raw_index])

        raw_index1 = [[1, 3], [3, 7], [7, 7]]
        raw_index2 = [1, 9]
        index1 = tensor(raw_index1)
        index2 = tensor(raw_index2)
        arr10 = arr[0, index1, :, index2]

        res = self.executor.execute_tensor(arr10, concat=True)[0]
        np.testing.assert_array_equal(res, raw[0, raw_index1, :, raw_index2])

        # test order
        raw = np.asfortranarray(np.random.random((11, 8, 12, 14)))
        arr = tensor(raw, chunk_size=(2, 3, 2, 3))

        raw_index = [8, 10, 3, 1, 9, 10]
        index = tensor(raw_index, chunk_size=4)
        arr11 = arr[index]

        res = self.executor.execute_tensor(arr11, concat=True)[0]
        expected = raw[raw_index].copy('A')
        np.testing.assert_array_equal(res, expected)
        self.assertEqual(res.flags['C_CONTIGUOUS'], expected.flags['C_CONTIGUOUS'])
        self.assertEqual(res.flags['F_CONTIGUOUS'], expected.flags['F_CONTIGUOUS'])

    def testSliceExecution(self):
        raw = np.random.random((11, 8, 12, 14))
        arr = tensor(raw, chunk_size=3)

        arr2 = arr[2:9:2, 3:7, -1:-9:-2, 12:-11:-4]
        res = self.executor.execute_tensor(arr2, concat=True)[0]

        np.testing.assert_array_equal(res, raw[2:9:2, 3:7, -1:-9:-2, 12:-11:-4])

        arr3 = arr[-4, 2:]
        res = self.executor.execute_tensor(arr3, concat=True)[0]
        np.testing.assert_equal(res, raw[-4, 2:])

        raw = sps.random(12, 14, density=.1)
        arr = tensor(raw, chunk_size=3)

        arr2 = arr[-1:-9:-2, 12:-11:-4]
        res = self.executor.execute_tensor(arr2, concat=True)[0]

        np.testing.assert_equal(res.toarray(), raw.toarray()[-1:-9:-2, 12:-11:-4])

        # test order
        raw = np.asfortranarray(np.random.random((11, 8, 12, 14)))
        arr = tensor(raw, chunk_size=3)

        arr2 = arr[2:9:2, 3:7, -1:-9:-2, 12:-11:-4]
        res = self.executor.execute_tensor(arr2, concat=True)[0]
        expected = raw[2:9:2, 3:7, -1:-9:-2, 12:-11:-4].copy('A')

        np.testing.assert_array_equal(res, expected)
        self.assertEqual(res.flags['C_CONTIGUOUS'], expected.flags['C_CONTIGUOUS'])
        self.assertEqual(res.flags['F_CONTIGUOUS'], expected.flags['F_CONTIGUOUS'])

        arr3 = arr[0:13, :, None]
        res = self.executor.execute_tensor(arr3, concat=True)[0]
        expected = raw[0:13, :, None].copy('A')

        np.testing.assert_array_equal(res, expected)
        self.assertEqual(res.flags['C_CONTIGUOUS'], expected.flags['C_CONTIGUOUS'])
        self.assertEqual(res.flags['F_CONTIGUOUS'], expected.flags['F_CONTIGUOUS'])

    def testMixedIndexingExecution(self):
        rs = np.random.RandomState(0)
        raw = rs.random((11, 8, 12, 13))
        arr = tensor(raw, chunk_size=3)

        raw_cond = raw[0, :, 0, 0] < .5
        cond = tensor(raw[0, :, 0, 0], chunk_size=3) < .5
        arr2 = arr[10::-2, cond, None, ..., :5]
        size_res = self.executor.execute_tensor(arr2, mock=True)
        res = self.executor.execute_tensor(arr2, concat=True)[0]

        new_shape = list(arr2.shape)
        new_shape[1] = cond.shape[0]
        self.assertEqual(sum(s[0] for s in size_res), int(np.prod(new_shape) * arr2.dtype.itemsize))
        np.testing.assert_array_equal(res, raw[10::-2, raw_cond, None, ..., :5])

        b_raw = np.random.random(8)
        raw_cond = b_raw < .5
        conds = [raw_cond, tensor(b_raw, chunk_size=2) < .5]
        for cond in conds:
            arr3 = arr[-2::-3, cond, ...]
            res = self.executor.execute_tensor(arr3, concat=True)[0]

            np.testing.assert_array_equal(res, raw[-2::-3, raw_cond, ...])

        # test multiple bool index and fancy index
        cond1 = np.zeros(11, dtype=bool)
        cond1[rs.permutation(11)[:5]] = True
        cond2 = np.zeros(12, dtype=bool)
        cond2[rs.permutation(12)[:5]] = True
        f3 = np.random.randint(13, size=5)

        expected = raw[cond1, ..., cond2, f3]

        t = arr[cond1, ..., cond2, f3]
        res = self.executor.execute_tensor(t, concat=True)[0]
        np.testing.assert_array_equal(res, expected)

        ctx, executor = self._create_test_context(self.executor)
        with ctx:
            t = arr[tensor(cond1), ..., tensor(cond2), tensor(f3)]
            res = executor.execute_tensors([t])[0]
            np.testing.assert_array_equal(res, expected)

    def testSetItemExecution(self):
        rs = np.random.RandomState(0)

        raw = data = rs.randint(0, 10, size=(11, 8, 12, 13))
        arr = tensor(raw.copy(), chunk_size=3)
        raw = raw.copy()

        idx = slice(2, 9, 2), slice(3, 7), slice(-1, -9, -2), 2
        arr[idx] = 20
        res = self.executor.execute_tensor(arr, concat=True)[0]

        raw[idx] = 20
        np.testing.assert_array_equal(res, raw)
        self.assertEqual(res.flags['C_CONTIGUOUS'], raw.flags['C_CONTIGUOUS'])
        self.assertEqual(res.flags['F_CONTIGUOUS'], raw.flags['F_CONTIGUOUS'])

        raw = data
        shape = raw[idx].shape

        arr2 = tensor(raw.copy(), chunk_size=3)
        raw = raw.copy()

        replace = rs.randint(10, 20, size=shape[:-1] + (1,)).astype('f4')
        arr2[idx] = tensor(replace, chunk_size=4)
        res = self.executor.execute_tensor(arr2, concat=True)[0]

        raw[idx] = replace
        np.testing.assert_array_equal(res, raw)

        raw = np.asfortranarray(np.random.randint(0, 10, size=(11, 8, 12, 13)))
        arr = tensor(raw.copy('A'), chunk_size=3)
        raw = raw.copy('A')

        idx = slice(2, 9, 2), slice(3, 7), slice(-1, -9, -2), 2
        arr[idx] = 20
        res = self.executor.execute_tensor(arr, concat=True)[0]

        raw[idx] = 20
        np.testing.assert_array_equal(res, raw)
        self.assertEqual(res.flags['C_CONTIGUOUS'], raw.flags['C_CONTIGUOUS'])
        self.assertEqual(res.flags['F_CONTIGUOUS'], raw.flags['F_CONTIGUOUS'])

        # test bool indexing set
        raw = data

        arr = tensor(raw.copy(), chunk_size=3)
        raw1 = rs.rand(11)
        arr[tensor(raw1, chunk_size=4) < 0.6, 2: 7] = 3
        res = self.executor.execute_tileable(arr, concat=True)[0]

        raw[raw1 < 0.6, 2: 7] = 3
        np.testing.assert_array_equal(res, raw)

        raw = np.random.randint(3, size=10).astype(np.int64)
        raw2 = np.arange(3)

        arr = zeros((10, 3))
        arr[tensor(raw) == 1, tensor(raw2) == 1] = 1
        res = self.executor.execute_tileable(arr, concat=True)[0]

        expected = np.zeros((10, 3))
        expected[raw == 1, raw2 == 1] = 1
        np.testing.assert_array_equal(res, expected)

        ctx, executor = self._create_test_context(self.executor)
        with ctx:
            raw = data

            arr = tensor(raw.copy(), chunk_size=3)
            raw1 = rs.rand(11)
            set_data = rs.rand((raw1 < 0.8).sum(), 8, 12, 13)
            arr[tensor(raw1, chunk_size=4) < 0.8] = tensor(set_data)

            res = self.executor.execute_tileables([arr])[0]

            raw[raw1 < 0.8] = set_data
            np.testing.assert_array_equal(res, raw)

        # test error
        with self.assertRaises(ValueError):
            t = tensor(raw, chunk_size=3)
            t[0, 0, 0, 0] = zeros(2, chunk_size=10)
            _ = self.executor.execute_tensor(t)

    def testSetItemStructuredExecution(self):
        rec_type = np.dtype([('a', np.int32), ('b', np.double),
                             ('c', np.dtype([('a', np.int16), ('b', np.int64)]))])

        raw = np.zeros((4, 5), dtype=rec_type)
        arr = tensor(raw.copy(), chunk_size=3)

        arr[1:4, 1] = (3, 4., (5, 6))
        arr[1:4, 2] = 8
        arr[1:3] = np.arange(5)
        arr[2:4] = np.arange(10).reshape(2, 5)
        arr[0] = np.arange(5)

        raw[1:4, 1] = (3, 4., (5, 6))
        raw[1:4, 2] = 8
        raw[1:3] = np.arange(5)
        raw[2:4] = np.arange(10).reshape(2, 5)
        raw[0] = np.arange(5)

        res = self.executor.execute_tensor(arr, concat=True)[0]
        self.assertEqual(arr.dtype, raw.dtype)
        self.assertEqual(arr.shape, raw.shape)
        np.testing.assert_array_equal(res, raw)

    def testTakeExecution(self):
        data = np.random.rand(10, 20, 30)
        t = tensor(data, chunk_size=10)

        a = t.take([4, 1, 2, 6, 200])

        res = self.executor.execute_tensor(a, concat=True)[0]
        expected = np.take(data, [4, 1, 2, 6, 200])
        np.testing.assert_array_equal(res, expected)

        a = take(t, [5, 19, 2, 13], axis=1)

        res = self.executor.execute_tensor(a, concat=True)[0]
        expected = np.take(data, [5, 19, 2, 13], axis=1)
        np.testing.assert_array_equal(res, expected)

        with self.assertRaises(ValueError):
            take(t, [1, 3, 4], out=tensor(np.random.rand(4)))

        out = tensor([1, 2, 3, 4])
        a = take(t, [4, 19, 2, 8], out=out)

        res = self.executor.execute_tensor(out, concat=True)[0]
        expected = np.take(data, [4, 19, 2, 8])
        np.testing.assert_array_equal(res, expected)

    def testCompressExecution(self):
        data = np.array([[1, 2], [3, 4], [5, 6]])
        a = tensor(data, chunk_size=1)

        t = compress([0, 1], a, axis=0)

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = np.compress([0, 1], data, axis=0)
        np.testing.assert_array_equal(res, expected)

        t = compress([0, 1], a, axis=1)

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = np.compress([0, 1], data, axis=1)
        np.testing.assert_array_equal(res, expected)

        t = a.compress([0, 1, 1])

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = np.compress([0, 1, 1], data)
        np.testing.assert_array_equal(res, expected)

        t = compress([False, True, True], a, axis=0)

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = np.compress([False, True, True], data, axis=0)
        np.testing.assert_array_equal(res, expected)

        t = compress([False, True], a, axis=1)

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = np.compress([False, True], data, axis=1)
        np.testing.assert_array_equal(res, expected)

        with self.assertRaises(np.AxisError):
            compress([0, 1, 1], a, axis=1)

        # test order
        data = np.asfortranarray([[1, 2], [3, 4], [5, 6]])
        a = tensor(data, chunk_size=1)

        t = compress([0, 1, 1], a, axis=0)

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = np.compress([0, 1, 1], data, axis=0)
        np.testing.assert_array_equal(res, expected)
        self.assertEqual(res.flags['C_CONTIGUOUS'], expected.flags['C_CONTIGUOUS'])
        self.assertEqual(res.flags['F_CONTIGUOUS'], expected.flags['F_CONTIGUOUS'])

        t = compress([0, 1, 1], a, axis=0, out=tensor(np.empty((2, 2), order='F', dtype=int)))

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = np.compress([0, 1, 1], data, axis=0, out=np.empty((2, 2), order='F', dtype=int))
        np.testing.assert_array_equal(res, expected)
        self.assertEqual(res.flags['C_CONTIGUOUS'], expected.flags['C_CONTIGUOUS'])
        self.assertEqual(res.flags['F_CONTIGUOUS'], expected.flags['F_CONTIGUOUS'])

    def testExtractExecution(self):
        data = np.arange(12).reshape((3, 4))
        a = tensor(data, chunk_size=2)
        condition = mod(a, 3) == 0

        t = extract(condition, a)

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = np.extract(np.mod(data, 3) == 0, data)
        np.testing.assert_array_equal(res, expected)

    def testChooseExecution(self):
        options.chunk_size = 2

        choices = [[0, 1, 2, 3], [10, 11, 12, 13],
                   [20, 21, 22, 23], [30, 31, 32, 33]]
        a = choose([2, 3, 1, 0], choices)

        res = self.executor.execute_tensor(a, concat=True)[0]
        expected = np.choose([2, 3, 1, 0], choices)

        np.testing.assert_array_equal(res, expected)

        a = choose([2, 4, 1, 0], choices, mode='clip')  # 4 goes to 3 (4-1)
        expected = np.choose([2, 4, 1, 0], choices, mode='clip')

        res = self.executor.execute_tensor(a, concat=True)[0]
        np.testing.assert_array_equal(res, expected)

        a = choose([2, 4, 1, 0], choices, mode='wrap')  # 4 goes to (4 mod 4)
        expected = np.choose([2, 4, 1, 0], choices, mode='wrap')  # 4 goes to (4 mod 4)

        res = self.executor.execute_tensor(a, concat=True)[0]
        np.testing.assert_array_equal(res, expected)

        a = [[1, 0, 1], [0, 1, 0], [1, 0, 1]]
        choices = [-10, 10]

        b = choose(a, choices)
        expected = np.choose(a, choices)

        res = self.executor.execute_tensor(b, concat=True)[0]
        np.testing.assert_array_equal(res, expected)

        a = np.array([0, 1]).reshape((2, 1, 1))
        c1 = np.array([1, 2, 3]).reshape((1, 3, 1))
        c2 = np.array([-1, -2, -3, -4, -5]).reshape((1, 1, 5))

        b = choose(a, (c1, c2))
        expected = np.choose(a, (c1, c2))

        res = self.executor.execute_tensor(b, concat=True)[0]
        np.testing.assert_array_equal(res, expected)

        # test order
        a = np.array([0, 1]).reshape((2, 1, 1), order='F')
        c1 = np.array([1, 2, 3]).reshape((1, 3, 1), order='F')
        c2 = np.array([-1, -2, -3, -4, -5]).reshape((1, 1, 5), order='F')

        b = choose(a, (c1, c2))
        expected = np.choose(a, (c1, c2))

        res = self.executor.execute_tensor(b, concat=True)[0]
        np.testing.assert_array_equal(res, expected)
        self.assertEqual(res.flags['C_CONTIGUOUS'], expected.flags['C_CONTIGUOUS'])
        self.assertEqual(res.flags['F_CONTIGUOUS'], expected.flags['F_CONTIGUOUS'])

        b = choose(a, (c1, c2), out=tensor(np.empty(res.shape, order='F')))
        expected = np.choose(a, (c1, c2), out=np.empty(res.shape, order='F'))

        res = self.executor.execute_tensor(b, concat=True)[0]
        np.testing.assert_array_equal(res, expected)
        self.assertEqual(res.flags['C_CONTIGUOUS'], expected.flags['C_CONTIGUOUS'])
        self.assertEqual(res.flags['F_CONTIGUOUS'], expected.flags['F_CONTIGUOUS'])

    def testUnravelExecution(self):
        a = tensor([22, 41, 37], chunk_size=1)
        t = stack(unravel_index(a, (7, 6)))

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = np.stack(np.unravel_index([22, 41, 37], (7, 6)))

        np.testing.assert_array_equal(res, expected)

    def testNonzeroExecution(self):
        data = np.array([[1, 0, 0], [0, 2, 0], [1, 1, 0]])
        x = tensor(data, chunk_size=2)
        t = hstack(nonzero(x))

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = np.hstack(np.nonzero(data))

        np.testing.assert_array_equal(res, expected)

        t = hstack((x > 1).nonzero())

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = np.hstack(np.nonzero(data > 1))

        np.testing.assert_array_equal(res, expected)

    def testFlatnonzeroExecution(self):
        x = arange(-2, 3, chunk_size=2)

        t = flatnonzero(x)

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = np.flatnonzero(np.arange(-2, 3))

        np.testing.assert_equal(res, expected)

    def testFillDiagonalExecution(self):
        # 2-d
        raws = [np.random.rand(30, 11),
                np.random.rand(15, 15),
                np.random.rand(11, 30),
                sps.random(30, 11, density=0.1, format='csr')]

        def copy(x):
            if hasattr(x, 'nnz'):
                # sparse
                return x.A
            else:
                return x.copy()

        for raw in raws:
            # test 1 chunk, wrap=False
            t = tensor(raw, chunk_size=30)
            fill_diagonal(t, 1)

            res = self.executor.execute_tensor(t, concat=True)[0]
            expected = copy(raw)
            np.fill_diagonal(expected, 1)

            np.testing.assert_array_equal(np.asarray(res), expected)

            # test 1 chunk, wrap=True
            t = tensor(raw, chunk_size=30)
            fill_diagonal(t, 1, wrap=True)

            res = self.executor.execute_tensor(t, concat=True)[0]
            expected = copy(raw)
            np.fill_diagonal(expected, 1, wrap=True)

            np.testing.assert_array_equal(np.asarray(res), expected)

            # test multiple chunks, wrap=False
            t = tensor(raw, chunk_size=(12, 4))
            fill_diagonal(t, 1)

            res = self.executor.execute_tensor(t, concat=True)[0]
            expected = copy(raw)
            np.fill_diagonal(expected, 1)

            np.testing.assert_array_equal(np.asarray(res), expected)

            t = tensor(raw, chunk_size=(4, 12))
            fill_diagonal(t, 1)

            res = self.executor.execute_tensor(t, concat=True)[0]
            expected = copy(raw)
            np.fill_diagonal(expected, 1)

            np.testing.assert_array_equal(np.asarray(res), expected)

            # test multiple chunk, val with list type
            t = tensor(raw, chunk_size=(12, 4))
            fill_diagonal(t, [1, 2, 3])

            res = self.executor.execute_tensor(t, concat=True)[0]
            expected = copy(raw)
            np.fill_diagonal(expected, [1, 2, 3])

            np.testing.assert_array_equal(np.asarray(res), expected)

            # test multiple chunk, val with tensor type
            t = tensor(raw, chunk_size=(12, 4))
            fill_diagonal(t, tensor([1, 2, 3]))

            res = self.executor.execute_tensor(t, concat=True)[0]
            expected = copy(raw)
            np.fill_diagonal(expected, [1, 2, 3])

            np.testing.assert_array_equal(np.asarray(res), expected)

            # test multiple chunks, wrap=True
            t = tensor(raw, chunk_size=(12, 4))
            fill_diagonal(t, 1, wrap=True)

            res = self.executor.execute_tensor(t, concat=True)[0]
            expected = copy(raw)
            np.fill_diagonal(expected, 1, wrap=True)

            np.testing.assert_array_equal(np.asarray(res), expected)

            t = tensor(raw, chunk_size=(4, 12))
            fill_diagonal(t, 1, wrap=True)

            res = self.executor.execute_tensor(t, concat=True)[0]
            expected = copy(raw)
            np.fill_diagonal(expected, 1, wrap=True)

            np.testing.assert_array_equal(np.asarray(res), expected)

            # test multiple chunk, val with list type
            t = tensor(raw, chunk_size=(12, 4))
            fill_diagonal(t, [1, 2, 3], wrap=True)

            res = self.executor.execute_tensor(t, concat=True)[0]
            expected = copy(raw)
            np.fill_diagonal(expected, [1, 2, 3], wrap=True)

            np.testing.assert_array_equal(np.asarray(res), expected)

            # test multiple chunk, val with tensor type
            t = tensor(raw, chunk_size=(12, 4))
            fill_diagonal(t, tensor([[1, 2], [3, 4]]), wrap=True)

            res = self.executor.execute_tensor(t, concat=True)[0]
            expected = copy(raw)
            np.fill_diagonal(expected, [1, 2, 3, 4], wrap=True)

            np.testing.assert_array_equal(np.asarray(res), expected)

        # 3-d
        raw = np.random.rand(11, 11, 11)

        expected = raw.copy()
        np.fill_diagonal(expected, 1)
        expected2 = raw.copy()
        np.fill_diagonal(expected2, 1, wrap=True)
        np.testing.assert_array_equal(expected, expected2)

        # test 1 chunk
        t = tensor(raw, chunk_size=30)
        fill_diagonal(t, 1)

        res = self.executor.execute_tensor(t, concat=True)[0]

        np.testing.assert_array_equal(res, expected)

        t = tensor(raw, chunk_size=30)
        # wrap = True does not take effect when ndim > 2
        fill_diagonal(t, 1, wrap=True)

        res = self.executor.execute_tensor(t, concat=True)[0]

        np.testing.assert_array_equal(res, expected)

        # test multiple chunk
        t = tensor(raw, chunk_size=(3, 4, 5))
        fill_diagonal(t, 1)

        res = self.executor.execute_tensor(t, concat=True)[0]

        np.testing.assert_array_equal(res, expected)

        t = tensor(raw, chunk_size=(3, 4, 5))
        # wrap = True does not take effect when ndim > 2
        fill_diagonal(t, 1, wrap=True)

        res = self.executor.execute_tensor(t, concat=True)[0]

        np.testing.assert_array_equal(res, expected)

        # test val with list type
        t = tensor(raw, chunk_size=(3, 4, 5))
        fill_diagonal(t, [[1, 2], [3, 4]])

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = raw.copy()
        np.fill_diagonal(expected, [1, 2, 3, 4])

        np.testing.assert_array_equal(res, expected)

        # test val with tensor type
        t = tensor(raw, chunk_size=(3, 4, 5))
        fill_diagonal(t, tensor([1, 2, 3]))

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = raw.copy()
        np.fill_diagonal(expected, [1, 2, 3])

        np.testing.assert_array_equal(res, expected)

        # test val with tensor type which ndim == 0
        t = tensor(raw, chunk_size=(3, 4, 5))
        fill_diagonal(t, tensor([1, 2, 3]).sum())

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = raw.copy()
        np.fill_diagonal(expected, 6)

        np.testing.assert_array_equal(res, expected)

        # test val with ndarray type which size is too long
        t = tensor(raw, chunk_size=(3, 4, 5))
        fill_diagonal(t, np.arange(20))

        res = self.executor.execute_tensor(t, concat=True)[0]
        expected = raw.copy()
        np.fill_diagonal(expected, np.arange(20))

        np.testing.assert_array_equal(res, expected)
