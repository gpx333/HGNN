import numpy as np
import tensorflow as tf
from tensorflow.python.framework import function
from tensorflow.python.framework import dtypes
import numpy.matlib
import re
import os


class MTDataset:
    def __init__(self, data, label, task_interval, batch_size):
        self.data = data
        self.data_dim = data.shape[1]
        self.label = np.reshape(label, [1, -1])
        self.task_interval = np.reshape(task_interval, [1, -1])
        self.num_task = task_interval.size-1
        self.batch_size = batch_size
        self.__build_index__()

    def __build_index__(self):
        index_list = []
        for i in range(self.num_task):
            start = self.task_interval[0, i]
            end = self.task_interval[0, i+1]
            index_list.append(np.arange(start, end))
        self.index_list = index_list
        self.counter = np.zeros([1, self.num_task], dtype=np.int32)

    def get_next_batch(self):
        sampled_data = np.zeros([self.batch_size*self.num_task, self.data_dim], dtype=np.float32)
        sampled_label = np.zeros([1, self.batch_size*self.num_task], dtype=np.float32)
        sampled_task_ind = np.zeros([1, self.batch_size*self.num_task], dtype=np.int32)
        for i in range(self.num_task):
            cur_ind = i
            task_index = self.index_list[cur_ind] - 1
            sampled_ind = range(cur_ind * batch_size, (cur_ind + 1) * batch_size)
            sampled_task_ind[0, sampled_ind] = i
            sampled_label[0, sampled_ind] = self.label[0, sampled_ind]
            if task_index.size < self.batch_size:
                sampled_data[sampled_ind, :] = self.data[np.concatenate((task_index, np.random.randint(0, high=task_index.size, size=self.batch_size-task_index.size))), :]
            elif self.counter[0, cur_ind]+self.batch_size < task_index.size:
                sampled_data[sampled_ind, :] = self.data[task_index[self.counter[0, cur_ind]:self.counter[0, cur_ind]+self.batch_size], :]
                self.counter[0, cur_ind] = self.counter[0, cur_ind] + self.batch_size
            else:
                sampled_data[sampled_ind, :] = self.data[task_index[-self.batch_size:], :]
                self.counter[0, cur_ind] = 0
                np.random.shuffle(self.index_list[cur_ind])
        sampled_label = sampled_label.reshape([-1, 1])
        return sampled_data, sampled_label, sampled_task_ind


class MTDataset_Split:
    def __init__(self, data, label, task_interval):
        self.data = data
        self.data_dim = data.shape[1]
        self.label = np.reshape(label, [1, -1])
        self.task_interval = np.reshape(task_interval, [1, -1])
        self.num_task = task_interval.size-1
        self.__build_index__()

    def __build_index__(self):
        index_list = []
        self.num_task_ins = np.zeros([1, self.num_task])
        for i in range(self.num_task):
            start = self.task_interval[0, i]
            end = self.task_interval[0, i+1]
            self.num_task_ins[0, i] = end - start
            index_list.append(np.arange(start, end))
        self.index_list = index_list

    def split(self, train_size):
        if train_size < 1:
            train_num = np.ceil(self.num_task_ins * train_size).astype(np.int32)
        else:
            train_num = np.ones([1, self.num_task], dtype=np.int32) * train_size
            train_num = np.maximum(1, np.minimum(train_num, self.num_task_ins - 10))
            train_num = train_num.astype(np.int32)
        traindata = np.zeros([0, self.data_dim], dtype=np.float32)
        testdata = np.zeros([0, self.data_dim], dtype=np.float32)
        trainlabel = np.zeros([1, 0], dtype=np.float32)
        testlabel = np.zeros([1, 0], dtype=np.float32)
        train_task_interval = np.zeros([1, self.num_task+1], dtype=np.int32)
        test_task_interval = np.zeros([1, self.num_task+1], dtype=np.int32)
        for i in range(self.num_task):
            cur_ind = i
            task_index = self.index_list[cur_ind] - 1
            np.random.shuffle(task_index)
            train_index = task_index[0: train_num[0, i]]
            test_index = task_index[train_num[0, i]:]
            traindata = np.concatenate((traindata, self.data[train_index, :]), axis=0)
            trainlabel = np.concatenate((trainlabel, self.label[:, train_index]), axis=1)
            testdata = np.concatenate((testdata, self.data[test_index, :]), axis=0)
            testlabel = np.concatenate((testlabel, self.label[:, test_index]), axis=1)
            train_task_interval[0, i+1] = trainlabel.size
            test_task_interval[0, i+1] = testlabel.size

        trainlabel = trainlabel.reshape([-1, 1])
        testlabel = testlabel.reshape([-1, 1])
        return traindata, trainlabel, train_task_interval, testdata, testlabel, test_task_interval


def read_data_from_file(filename):
    file = open(filename, 'r')
    contents = file.readlines()
    file.close()
    num_task = int(contents[0])
    num_class = int(contents[1])
    temp_ind = re.split(',', contents[2])
    temp_ind = [int(elem) for elem in temp_ind]
    task_interval = np.reshape(np.array(temp_ind), [1, -1])
    temp_data = []
    for pos in range(3, len(contents) - 1):
        temp_sub_data = re.split(',', contents[pos])
        temp_sub_data = [float(elem) for elem in temp_sub_data]
        temp_data.append(temp_sub_data)
    data = np.array(temp_data)
    temp_label = re.split(',', contents[-1])
    temp_label = [int(elem) for elem in temp_label]
    label = np.reshape(np.array(temp_label), [1, -1])
    return data, label, task_interval, num_task, num_class


def read_regression_data_from_file(filename):
    file = open(filename, 'r')
    contents = file.readlines()
    file.close()
    num_task = int(contents[0])
    temp_ind = re.split(',', contents[1])
    temp_ind = [int(elem) for elem in temp_ind]
    task_interval = np.reshape(np.array(temp_ind), [1, -1])
    temp_data = []
    for pos in range(2, len(contents)-1):
        temp_sub_data = re.split(',', contents[pos])
        temp_sub_data = [float(elem) for elem in temp_sub_data]
        temp_data.append(temp_sub_data)
    data = np.array(temp_data)
    temp_label = re.split(',', contents[-1])
    temp_label = [float(elem) for elem in temp_label]
    label = np.reshape(np.array(temp_label), [1, -1])
    return data, label, task_interval, num_task


def compute_train_loss(i, feature_representation, hidden_output_weight, inputs_data_label, inputs_task_ind,
                       inputs_num_ins_per_task, train_loss):
    logit = tf.matmul(tf.expand_dims(feature_representation[inputs_task_ind[0, i]][i % (batch_size * inputs_data_label.shape[-1])][:], 0),
                        hidden_output_weight[inputs_task_ind[0, i], :, :])
    label = tf.expand_dims(inputs_data_label[i, :], 0)
    train_loss += tf.div(tf.losses.mean_squared_error(logit, label),
                         tf.cast(inputs_num_ins_per_task[0, inputs_task_ind[0, i]], dtype=tf.float32))
    return i + 1, feature_representation, hidden_output_weight, inputs_data_label, inputs_task_ind, inputs_num_ins_per_task, train_loss


def gradient_clipping_tf_false_consequence(optimizer, obj, gradient_clipping_threshold):
    gradients, variables = zip(*optimizer.compute_gradients(obj))
    gradients = [None if gradient is None else tf.clip_by_value(gradient, gradient_clipping_threshold,
                                                                tf.negative(gradient_clipping_threshold)) for gradient
                 in gradients]
    train_step = optimizer.apply_gradients(zip(gradients, variables))
    return train_step


def gradient_clipping_tf(optimizer, obj, option, gradient_clipping_threshold):
    train_step = tf.cond(tf.equal(option, 0), lambda: optimizer.minimize(obj),
                         lambda: gradient_clipping_tf_false_consequence(optimizer, obj, gradient_clipping_threshold))
    train_step = tf.group(train_step)
    return train_step


def generate_label_task_ind(label, task_interval):
    num_task = task_interval.size - 1
    num_ins = label.size
    label_matrix = label
    task_ind = np.zeros((1, num_ins), dtype=np.int32)
    for i in range(num_task):
        task_ind[0, task_interval[0, i]:task_interval[0, i + 1]] = i
    return label_matrix, task_ind


def compute_errors(hidden_rep, hidden_output_weight, task_ind, label, num_task):
    num_total_ins = hidden_rep.shape[0]
    num_ins = np.zeros([1, num_task])
    errors = np.zeros([1, num_task+1])
    for i in range(num_total_ins):
        probit = numpy.matmul(hidden_rep[i,:],hidden_output_weight[task_ind[0, i], :, :])
        num_ins[0, task_ind[0, i]] += 1
        errors[0, task_ind[0, i]] += np.power(np.subtract(probit, label[i]), 2.)
    for i in range(num_task):
        errors[0, i] = errors[0, i]/num_ins[0, i]
    errors[0, num_task] = np.mean(errors[0, 0:num_task])
    return errors


def change_datastruct(hidden_features, num_task):
    return tf.reshape(hidden_features, [num_task, -1, hidden_features.shape[-1]])


def compute_pairwise_dist_tf(data):
    sq_data_norm = tf.reduce_sum(tf.square(data), axis=1)
    sq_data_norm = tf.reshape(sq_data_norm, [-1, 1])
    dist_matrix = sq_data_norm - 2 * tf.matmul(data, data, transpose_b=True) + tf.matrix_transpose(sq_data_norm)
    return dist_matrix


def compute_pairwise_dist_np(data):
    n = data.shape[0]
    sq_data_norm = np.sum(data ** 2, axis=1)
    sq_data_norm = np.reshape(sq_data_norm, [-1, 1])
    dist_matrix = sq_data_norm - 2 * np.dot(data, data.transpose()) + sq_data_norm.transpose()
    return dist_matrix


def activate_function(temp, activate_op):
    if activate_op == 1:
        return tf.tanh(temp)
    elif activate_op == 2:
        return tf.nn.relu(temp)
    elif activate_op == 3:
        return tf.nn.elu(temp)
    else:
        return


def get_normed_distance_tf(data):
    norminator = tf.matmul(data, tf.transpose(data))
    square = tf.reshape(tf.sqrt(tf.reduce_sum(tf.square(data), 1)), [norminator.shape[0], 1])
    denorminator = tf.matmul(square, tf.transpose(square))
    return norminator/denorminator


def get_normed_distance_np(data):
    norminator = np.matmul(data, np.transpose(data))
    square = np.reshape(np.sqrt(np.sum(np.square(data), 1)), [norminator.shape[0], 1])
    denorminator = np.matmul(square, np.transpose(square))
    return norminator/denorminator


def GAT(attention_weight, embedding_vectors):
    transformaed_embedding_vectors = tf.matmul(embedding_vectors, attention_weight)
    attention_values = tf.nn.softmax(get_normed_distance_tf(transformaed_embedding_vectors))
    return attention_values


def get_normed_distance_tf_sample(data, num_task):
    norminator = tf.matmul(data, tf.transpose(data))
    square = tf.reshape(tf.sqrt(tf.reduce_sum(tf.square(data), 1)), [batch_size * num_task, 1])
    denorminator = tf.matmul(square, tf.transpose(square))
    return norminator/denorminator


def GAT_sample(attention_weight, embedding_vectors, num_task):
    transformaed_embedding_vectors = tf.matmul(embedding_vectors, attention_weight)
    attention_values = tf.nn.softmax(get_normed_distance_tf_sample(transformaed_embedding_vectors, num_task))
    return attention_values


def get_feature_representation(hidden_features, hidden_hidden_weights, num_task, first_task_att_w, task_attention_weight):
    hidden_representation_values = GAT_sample(hidden_hidden_weights, hidden_features, num_task)
    new_hidden_representation = tf.tanh(tf.matmul(hidden_representation_values, tf.matmul(hidden_features, hidden_hidden_weights)))
    new_hidden_representation = change_datastruct(new_hidden_representation, num_task)

    task_embedding_vectors = tf.reduce_max(new_hidden_representation, 1)
    task_attention_values = GAT(first_task_att_w, task_embedding_vectors)
    new_task_embedding_vectors = tf.tanh(tf.matmul(task_attention_values, tf.matmul(task_embedding_vectors, first_task_att_w)))
    task_attention_values = GAT(task_attention_weight, new_task_embedding_vectors)
    new_task_embedding_vectors = tf.tanh(tf.matmul(task_attention_values, tf.matmul(new_task_embedding_vectors, task_attention_weight)))

    feature_representations = []
    for i in range(num_task):
        feature_representation = tf.concat([hidden_features[i * batch_size: (i + 1) * batch_size],
                                        tf.stack([new_task_embedding_vectors[i] for _ in range(batch_size)])], 1)
        feature_representations.append(feature_representation)
    feature_representations = tf.stack(feature_representations)
    return tf.reshape(feature_representations, [num_task, -1, hidden_features.shape[-1] + F_pie])


def np_softmax(x):
    x = x - np.max(x)
    exp_x = np.exp(x)
    softmax_x = exp_x / np.sum(exp_x)
    return softmax_x


def get_embedding_vec(traindata, hidden_hidden_weights, first_task_att_w, task_attention_weight, train_hidden_features, train_task_ind, num_task):
    features = [[] for _ in range(num_task)]
    for i in range(traindata.shape[0]):
        features[train_task_ind[0, i]].append(train_hidden_features[i])
    task_embedding_vectors = []
    for i in range(num_task):
        features_values = np_softmax(get_normed_distance_np(np.stack(features[i])))
        new_features = np.tanh(np.matmul(features_values, np.matmul(features[i], hidden_hidden_weights)))
        task_embedding_vector = np.max(new_features, 0)
        task_embedding_vectors.append(task_embedding_vector)

    task_attention_values = np_softmax(get_normed_distance_np(np.stack(task_embedding_vectors)))
    new_task_embedding_vectors = np.tanh(np.matmul(task_attention_values, np.matmul(task_embedding_vectors, first_task_att_w)))
    task_attention_values = np_softmax(get_normed_distance_np(np.stack(new_task_embedding_vectors)))
    new_task_embedding_vectors = np.tanh(np.matmul(task_attention_values, np.matmul(new_task_embedding_vectors, task_attention_weight)))

    return new_task_embedding_vectors


def get_new_hidden_features(test_hidden_rep, task_embedding_vectors, test_task_ind):
    new_test_hidden_rep = []
    for i in range(test_hidden_rep.shape[0]):
        temp = np.concatenate([test_hidden_rep[i], task_embedding_vectors[test_task_ind[0, i]]], 0)
        new_test_hidden_rep.append(temp)
    new_test_hidden_rep = np.stack(new_test_hidden_rep)
    return new_test_hidden_rep


def DMTL_HGNN_reg(traindata, trainlabel, train_task_interval, dim, num_task, hidden_dim, batch_size, reg_para,
         max_epoch, testdata, testlabel, test_task_interval, activate_op):
    print('DMTL_HGNN_reg is running...')
    inputs = tf.placeholder(tf.float32, shape=[None, dim])
    inputs_data_label = tf.placeholder(tf.float32, shape=[None, 1])
    inputs_task_ind = tf.placeholder(tf.int32, shape=[1, None])
    inputs_num_ins_per_task = tf.placeholder(tf.int32, shape=[1, None])

    input_hidden_weights = tf.Variable(tf.truncated_normal([dim, hidden_dim], dtype=tf.float32, stddev=1e-1))

    hidden_features = activate_function(tf.matmul(inputs, input_hidden_weights), activate_op)

    hidden_hidden_weights = tf.Variable(tf.truncated_normal([hidden_dim, hidden_dim], dtype=tf.float32, stddev=1e-1))

    first_task_att_w = tf.Variable(tf.truncated_normal(
        [hidden_dim, GAT_hidden_dim], dtype=tf.float32, stddev=1e-1))
    task_attention_weight = tf.Variable(tf.truncated_normal(
        [GAT_hidden_dim, F_pie], dtype=tf.float32, stddev=1e-1))

    feature_representation = get_feature_representation(hidden_features, hidden_hidden_weights, num_task, first_task_att_w, task_attention_weight)

    hidden_output_weight = tf.Variable(tf.truncated_normal(
        [num_task, hidden_dim + F_pie, 1], dtype=tf.float32, stddev=1e-1))

    train_loss = tf.Variable(0.0, dtype=tf.float32)
    _, _, _, _, _, _, train_loss = tf.while_loop(
        cond=lambda i, j1, j2, j3, j4, j5, j6: tf.less(i, tf.shape(inputs_task_ind)[1]), body=compute_train_loss,
        loop_vars=(tf.constant(0, dtype=tf.int32), feature_representation, hidden_output_weight,
                   inputs_data_label, inputs_task_ind, inputs_num_ins_per_task, train_loss))

    obj = train_loss + reg_para * (tf.square(tf.norm(input_hidden_weights))+tf.square(tf.norm(hidden_output_weight)))

    learning_rate = tf.placeholder(tf.float32)
    gradient_clipping_threshold = tf.placeholder(tf.float32)
    optimizer = tf.train.AdamOptimizer(learning_rate)
    gradient_clipping_option = tf.placeholder(tf.int32)
    train_step = gradient_clipping_tf(optimizer, obj, gradient_clipping_option, gradient_clipping_threshold)
    init_op = tf.global_variables_initializer()
    with tf.Session() as sess:
        max_iter_epoch = numpy.ceil(traindata.shape[0] / (batch_size * num_task)).astype(np.int32)
        Iterator = MTDataset(traindata, trainlabel, train_task_interval, batch_size)
        sess.run(init_op)

        train_label_matrix, train_task_ind = generate_label_task_ind(trainlabel, train_task_interval)
        for iter in range(max_iter_epoch * max_epoch):
            sampled_data, sampled_label, sampled_task_ind = Iterator.get_next_batch()
            num_iter = iter // max_iter_epoch
            train_step.run(feed_dict={d1: d2 for d1, d2 in
                                      zip([learning_rate, gradient_clipping_option, gradient_clipping_threshold, inputs,
                                           inputs_data_label, inputs_task_ind, inputs_num_ins_per_task],
                                          [0.02 / (1 + num_iter), 0, -5., sampled_data, sampled_label, sampled_task_ind,
                                           np.ones([1, num_task]) * (batch_size)])})
            if iter % max_iter_epoch == 0 and num_iter % 5 == 0:
                train_hidden_features = hidden_features.eval(feed_dict={inputs: traindata, inputs_task_ind: train_task_ind})
                task_embedding_vectors = get_embedding_vec(traindata, hidden_hidden_weights.eval(), first_task_att_w.eval(), task_attention_weight.eval(),
                                    train_hidden_features, train_task_ind, num_task)
                _, test_task_ind = generate_label_task_ind(testlabel, test_task_interval)
                test_hidden_rep = hidden_features.eval(feed_dict={inputs: testdata, inputs_task_ind: test_task_ind})
                new_test_hidden_rep = get_new_hidden_features(test_hidden_rep, task_embedding_vectors, test_task_ind)
                test_errors = compute_errors(new_test_hidden_rep, hidden_output_weight.eval(), test_task_ind, testlabel, num_task)
                print('epoch = %g, test_errors = %s' % (num_iter, test_errors[0, -1]))
    return test_errors


def main_process(filename, train_size, hidden_dim, batch_size, reg_para, max_epoch, use_gpu, gpu_id='0', activate_op=1):
    if use_gpu == 1:
        os.environ['CUDA_VISIBLE_DEVICES'] = gpu_id
    else:
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    data, label, task_interval, num_task = read_regression_data_from_file(filename)
    data_split = MTDataset_Split(data, label, task_interval)
    dim = data.shape[1]
    traindata, trainlabel, train_task_interval, testdata, testlabel, test_task_interval = data_split.split(train_size)
    error = DMTL_HGNN_reg(traindata, trainlabel, train_task_interval, dim, num_task, hidden_dim,
                 batch_size, reg_para, max_epoch, testdata, testlabel, test_task_interval, activate_op)
    return error


datafile = './data/sarcos_2000.txt'
max_epoch = 200
use_gpu = 1
gpu_id = '2'
hidden_dim = 600
batch_size = 32
reg_para = 0.2
train_size = 0.7
activate_op = 1
GAT_hidden_dim = 16
F_pie = 8

mean_errors = main_process(datafile, train_size, hidden_dim, batch_size, reg_para, max_epoch, use_gpu, gpu_id,
                           activate_op)

print('final test_errors = ', mean_errors[0, -1])
