import itertools
import os
import time

from datetime import datetime

import tensorflow as tf
import numpy as np

import data


class DepthMapNetwork:

    def setup(__init__):
        def init(self, input_shape, output_shape, *,
                 ckptdir='checkpoints', ckptfreq=50, tbdir='tb_logs',
                 cont=False):
            self.ckpt_path = str(os.path.join('.', ckptdir,
                                              f'{type(self).__name__}'))
            self.ckptfreq = ckptfreq

            self.cont = cont

            self.graph = tf.Graph()
            with self.graph.as_default():
                self.input = tf.placeholder(tf.float32,
                                            shape=(None, ) + input_shape,
                                            name='input')
                self.target = tf.placeholder(tf.float32,
                                             shape=(None, ) + output_shape,
                                             name='target')

                self.optimizer = tf.Print(self.input, [''],
                                          'No self.optimizer implemented', 1)
                self.output = tf.Print(self.input, [''],
                                       'No self.output implemented', 1)
                self.loss = tf.Print(self.input, [''],
                                     'No self.loss implemented', 1)

                __init__(self, input_shape, output_shape)

                self.saver = tf.train.Saver()

            self.tb_log = tf.summary.FileWriter(
                os.path.join(
                    '.', tbdir,
                    datetime.now().strftime(
                        f'%m-%dT%H-%M_{type(self).__name__}')),
                self.graph)

        return init

    def __loss(self, dataset_test, session):
        loss = 0
        for b_in, b_out in data.as_matrix_batches(dataset_test, 1):
            loss += session.run(self.loss, {self.input: b_in,
                                            self.output: b_out})
        return loss / len(dataset_test)

    def test(self, dataset):
        with tf.Session(graph=self.graph) as s:
            s.run(tf.global_variables_initializer())
            self.saver.restore(s, self.ckpt_path)

            total_loss = 0
            for i, (b_in, b_out) in enumerate(data.as_matrix_batches(dataset,
                                                                     1)):
                feed_dict = {self.input: b_in, self.target: b_out}
                dataset[i].result, loss = s.run([self.output, self.loss],
                                                feed_dict)
                total_loss += loss
            total_loss /= len(dataset)
            print(f'Mean loss is {total_loss}')

    def train(self, dataset_train, dataset_test, epochs, batchsize):
        start = time.time()
        with tf.Session(graph=self.graph) as s:
            s.run(tf.global_variables_initializer())
            if self.cont:
                self.saver.restore(s, self.ckpt_path)

            for epoch in range(1, 1 + epochs):
                epoch_start = time.time()
                print(f'Starting epoch {epoch}')

                for b_in, b_out in data.as_matrix_batches(dataset_train,
                                                          batchsize):
                    s.run(self.optimizer,
                          {self.input: b_in, self.target: b_out})

                loss = self.__loss(dataset_test, s)

                print(f'Epoch {epoch} finished',
                      f'Elapsed time: {time.time() - start:.3f}',
                      f'Epoch time: {time.time() - epoch_start:.3f}',
                      f'\nMean loss: {loss}')
                if not epoch % self.ckptfreq:
                    print(f'Saving checkpoints after epoch {epoch}')
                    self.saver.save(s, self.ckpt_path, global_step=epoch)

            print('Saving final checkpoint')
            self.saver.save(s, self.ckpt_path, global_step=epoch)


class DownsampleNetwork(DepthMapNetwork):

    @DepthMapNetwork.setup
    def __init__(self, input_shape, output_shape):
        # Grayscale
        gray = tf.image.rgb_to_grayscale(self.input)

        # Scale to nearest multiple of target size
        resize = tf.image.resize_images(gray,
                                        tuple(itertools.starmap(
                                            lambda x, y: x // y * y,
                                            zip(input_shape, output_shape))
                                            ))

        # Convolve to output size, alternating between horizontal and
        # vertical
        steps_h, steps_v = map(lambda x: x[0] // x[1],
                               zip(input_shape, output_shape))
        i_boundary = min(steps_h, steps_v) // 2 + 2
        for i in range(i_boundary):
                # Last layer is sigmoid, others relu
            last = i == i_boundary - 1
            conv = tf.layers.conv2d(conv if i > 0 else resize,
                                    1 if last else 32, 3,
                                    strides=(1 + i % 2, 2 - i % 2),
                                    padding='same',
                                    activation=(tf.nn.sigmoid
                                                if last else
                                                tf.nn.relu),
                                    name=f'Conv{i}'
                                    )
        self.output = tf.squeeze(conv)

        ema = tf.train.ExponentialMovingAverage(decay=0.9999)
        tf.summary.scalar(ema)

        self.loss = tf.reduce_mean(
            tf.squared_difference(self.output, self.target)
        )
        ema_op.apply(self.loss)

        with tf.control_dependencies(ema_op):
            self.optimizer = tf.train.AdamOptimizer(
                                learning_rate=0.001,
                                epsilon=1.0
                             ).minimize(self.loss)
