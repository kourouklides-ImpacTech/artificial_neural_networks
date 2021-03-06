"""

Model: Standard Neural Network (SNN) with dropout layers
Method: Backpropagation
Architecture: Feedforward Neural Network

Dataset: MNIST
Task: Handwritten Digit Recognition (Multi-class Classification)

    Author: Ioannis Kourouklides, www.kourouklides.com
    License: https://github.com/kourouklides/artificial_neural_networks/blob/master/LICENSE

"""
# %%
# Python configurations

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import tensorflow as tf
import random as rn

from keras import optimizers
from keras.layers import Input, Dense, Dropout
from keras.models import Model
from keras.callbacks import ModelCheckpoint
from keras.utils import to_categorical

from sklearn.metrics import confusion_matrix
import itertools

import json
import yaml

import argparse

import os

import matplotlib.pyplot as plt

# %%


def none_or_int(value):
    if value == 'None':
        return None
    else:
        return int(value)


def none_or_float(value):
    if value == 'None':
        return None
    else:
        return float(value)


def snn_dropout_mnist(new_dir=os.getcwd()):

    os.chdir(new_dir)

    from artificial_neural_networks.code.utils.download_mnist import download_mnist

    # SETTINGS
    parser = argparse.ArgumentParser()

    # General settings
    parser.add_argument('--verbose', type=int, default=1)
    parser.add_argument('--reproducible', type=bool, default=True)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--plot', type=bool, default=False)

    # Settings for preprocessing and hyperparameters
    parser.add_argument('--scaling_factor', type=float, default=(1/255))
    parser.add_argument('--translation', type=float, default=0)
    parser.add_argument('--same_size', type=bool, default=True)
    parser.add_argument('--n_layers', type=int, default=20)
    parser.add_argument('--layer_size', type=int, default=512)
    parser.add_argument('--explicit_layer_sizes', nargs='*', type=int, default=[512, 512])
    parser.add_argument('--n_epochs', type=int, default=2)
    parser.add_argument('--batch_size', type=none_or_int, default=128)
    parser.add_argument('--optimizer', type=str, default='RMSprop')
    parser.add_argument('--lrearning_rate', type=float, default=1e-3)
    parser.add_argument('--epsilon', type=none_or_float, default=None)
    parser.add_argument('--dropout_rate_input', type=int, default=0.1)
    parser.add_argument('--dropout_rate_hidden', type=int, default=0.2)

    # Settings for saving the model
    parser.add_argument('--save_architecture', type=bool, default=True)
    parser.add_argument('--save_last_weights', type=bool, default=True)
    parser.add_argument('--save_last_model', type=bool, default=True)
    parser.add_argument('--save_models', type=bool, default=False)
    parser.add_argument('--save_weights_only', type=bool, default=False)
    parser.add_argument('--save_best', type=bool, default=False)

    args = parser.parse_args()

    if (args.verbose > 0):
        print(args)

    # For reproducibility
    if (args.reproducible):
        os.environ['PYTHONHASHSEED'] = '0'
        np.random.seed(args.seed)
        rn.seed(args.seed)
        tf.set_random_seed(args.seed)

    # %%
    # Load the MNIST dataset

    mnist_path = download_mnist()
    mnist = np.load(mnist_path)
    train_x = mnist['x_train'].astype(np.float32)
    train_y = mnist['y_train'].astype(np.int32)
    test_x = mnist['x_test'].astype(np.float32)
    test_y = mnist['y_test'].astype(np.int32)
    mnist.close()

    # %%
    # PREPROCESSING STEP

    scaling_factor = args.scaling_factor
    translation = args.translation

    img_width = train_x.shape[1]
    img_height = train_x.shape[2]

    n_train = train_x.shape[0]  # number of training examples/samples
    n_test = test_x.shape[0]  # number of test examples/samples

    n_in = img_width * img_height  # number of features / dimensions
    n_out = np.unique(train_y).shape[0]  # number of classes/labels

    # Reshape training and test sets
    train_x = train_x.reshape(n_train, n_in)
    test_x = test_x.reshape(n_test, n_in)

    # Apply preprocessing
    train_x = scaling_factor * (train_x - translation)
    test_x = scaling_factor * (test_x - translation)

    one_hot = False  # It works exactly the same for both True and False

    # Convert class vectors to binary class matrices (i.e. One hot encoding)
    if (one_hot):
        train_y = to_categorical(train_y, n_out)
        test_y = to_categorical(test_y, n_out)

    # %%
    # Model hyperparameters

    N = []
    N.append(n_in)  # input layer
    if (args.same_size):
        n_layers = args.n_layers
        for i in range(n_layers):
            N.append(args.layer_size)  # hidden layer i
    else:
        n_layers = len(args.explicit_layer_sizes)
        for i in range(n_layers):
            N.append(args.explicit_layer_sizes[i])  # hidden layer i
    N.append(n_out)  # output layer

    # ANN Architecture
    L = len(N) - 1

    x = Input(shape=(n_in,))  # input layer
    h = Dropout(rate=args.dropout_rate_input)(x)

    for i in range(1, L):
        h = Dense(units=N[i], activation='relu')(h)  # hidden layer i
        h = Dropout(rate=args.dropout_rate_hidden)(h)
    out = Dense(units=n_out, activation='softmax')(h)  # output layer

    model = Model(inputs=x, outputs=out)

    if (args.verbose > 0):
        model.summary()

    if (one_hot):
        loss_function = 'categorical_crossentropy'
    else:
        loss_function = 'sparse_categorical_crossentropy'

    metrics = ['accuracy']

    lr = args.lrearning_rate
    epsilon = args.epsilon
    optimizer_selection = {'Adadelta': optimizers.Adadelta(
                                   lr=lr, rho=0.95, epsilon=epsilon, decay=0.0),
                           'Adagrad':   optimizers.Adagrad(
                                   lr=lr, epsilon=epsilon, decay=0.0),
                           'Adam':      optimizers.Adam(
                                   lr=lr, beta_1=0.9, beta_2=0.999,
                                   epsilon=epsilon, decay=0.0, amsgrad=False),
                           'Adamax':    optimizers.Adamax(
                                   lr=lr, beta_1=0.9, beta_2=0.999,
                                   epsilon=epsilon, decay=0.0),
                           'Nadam':     optimizers.Nadam(
                                   lr=lr, beta_1=0.9, beta_2=0.999,
                                   epsilon=epsilon, schedule_decay=0.004),
                           'RMSprop':   optimizers.RMSprop(
                                   lr=lr, rho=0.9, epsilon=epsilon, decay=0.0),
                           'SGD':       optimizers.SGD(
                                   lr=lr, momentum=0.0, decay=0.0, nesterov=False)}

    optimizer = optimizer_selection[args.optimizer]

    model.compile(optimizer=optimizer,
                  loss=loss_function,
                  metrics=metrics)

    # %%
    # Save trained models for every epoch

    models_path = r'artificial_neural_networks/trained_models/'
    model_name = 'mnist_snn_dropout'
    weights_path = models_path + model_name + '_weights'
    model_path = models_path + model_name + '_model'
    file_suffix = '_{epoch:04d}_{val_acc:.4f}_{val_loss:.4f}'

    if (args.save_weights_only):
        file_path = weights_path
    else:
        file_path = model_path

    file_path += file_suffix

    # monitor='val_loss'
    monitor = 'val_acc'

    if (args.save_models):
        checkpoint = ModelCheckpoint(file_path + '.h5',
                                     monitor=monitor,
                                     verbose=args.verbose,
                                     save_best_only=args.save_best_only,
                                     mode='auto',
                                     save_weights_only=args.save_weights_only)
        callbacks = [checkpoint]
    else:
        callbacks = []

    # %%
    # TRAINING PHASE

    model_history = model.fit(x=train_x, y=train_y,
                              validation_data=(test_x, test_y),
                              batch_size=args.batch_size,
                              epochs=args.n_epochs,
                              verbose=args.verbose,
                              callbacks=callbacks)

    # %%
    # TESTING PHASE

    train_y_pred = np.argmax(model.predict(train_x), axis=1)
    test_y_pred = np.argmax(model.predict(test_x), axis=1)

    train_score = model.evaluate(x=test_x, y=test_y, verbose=args.verbose)
    train_dict = {'val_loss': train_score[0], 'val_acc': train_score[1]}

    test_score = model.evaluate(x=test_x, y=test_y, verbose=args.verbose)
    test_dict = {'val_loss': test_score[0], 'val_acc': test_score[1]}

    if (args.verbose > 0):
        print('Train loss:', train_dict['val_loss'])
        print('Train accuracy:', train_dict['val_acc'])

        print('Test loss:', test_dict['val_loss'])
        print('Test accuracy:', test_dict['val_acc'])

    # %%
    # Data Visualization

    def plot_confusion_matrix(cm, classes, title='Confusion matrix',
                              cmap=plt.cm.Blues):

        plt.imshow(cm, interpolation='nearest', cmap=cmap)
        plt.title(title)
        plt.colorbar()
        tick_marks = np.arange(len(classes))
        plt.xticks(tick_marks, classes)
        plt.yticks(tick_marks, classes)

        fmt = 'd'
        thresh = cm.max() / 2.
        for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
            plt.text(j, i, format(cm[i, j], fmt),
                     horizontalalignment="center",
                     color="white" if cm[i, j] > thresh else "black")

        plt.ylabel('Actual label')
        plt.xlabel('Predicted label')
        plt.tight_layout()
        plt.show()

    if (args.plot):
        train_cm = confusion_matrix(train_y, train_y_pred)
        test_cm = confusion_matrix(test_y, test_y_pred)

        classes = list(range(n_out))

        plot_confusion_matrix(train_cm, classes=classes,
                              title='Confusion matrix for training set')
        plot_confusion_matrix(test_cm, classes=classes,
                              title='Confusion matrix for test set')

    # %%
    # Save the architecture and the lastly trained model

    architecture_path = models_path + model_name + '_architecture'

    last_suffix = file_suffix.format(epoch=args.n_epochs,
                                     val_acc=test_dict['val_acc'],
                                     val_loss=test_dict['val_loss'])

    if (args.save_architecture):
        # Save only the archtitecture (as a JSON file)
        json_string = model.to_json()
        json.dump(json.loads(json_string), open(architecture_path + '.json', "w"))

        # Save only the archtitecture (as a YAML file)
        yaml_string = model.to_yaml()
        yaml.dump(yaml.load(yaml_string), open(architecture_path + '.yml', "w"))

    # Save only the weights (as an HDF5 file)
    if (args.save_last_weights):
        model.save_weights(weights_path + last_suffix + '.h5')

    # Save the whole model (as an HDF5 file)
    if (args.save_last_model):
        model.save(model_path + last_suffix + '.h5')

    return model

# %%


if __name__ == '__main__':
    model = snn_dropout_mnist('../../../../../')
