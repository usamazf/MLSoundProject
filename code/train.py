#-----------------------------------------------------------------------------------------------#
#                                                                                               #
#   I M P O R T     L I B R A R I E S                                                           #
#                                                                                               #
#-----------------------------------------------------------------------------------------------# 
import os
import shutil
import numpy as np
import pandas as pd
import utils
from utils import Config
import tensorflow as tf
from keras import losses, models, optimizers
from keras.activations import softmax
from keras.layers import (Dense, Input, Convolution2D, BatchNormalization, Flatten, MaxPool2D, Activation)
from keras.callbacks import (EarlyStopping, ModelCheckpoint, TensorBoard)
from keras.utils import to_categorical
from sklearn.model_selection import StratifiedKFold
from keras import backend as K

#-----------------------------------------------------------------------------------------------#
#                                                                                               #
#   Define global parameters to be used through out the program                                 #
#                                                                                               #
#-----------------------------------------------------------------------------------------------#

#***********************************************************************************************#
#                                                                                               #
#   Module:                                                                                     #
#   train()                                                                                     #
#                                                                                               #
#   Description:                                                                                #
#   The training module of the project. Responsible for training the parameters for provided    #
#   features and selected options.                                                              #
#                                                                                               #
#***********************************************************************************************#
def train(tr_mnn_features, tr_mnn_labels, ts_mnn_features, tr_cnn_features, tr_cnn_labels, ts_cnn_features, n_classes):
    # call the multi-layer neural network to get results
    mnn_y_pred, mnn_probs, mnn_pred = tensor_multilayer_neural_network(tr_mnn_features, tr_mnn_labels, ts_mnn_features, n_classes, training_epochs=5000)
    # call the 1d convolutional network code here
    
    # call the 2d convolutional network code here
    cnn_2d_probs = keras_convolution_2D(tr_cnn_features, tr_cnn_labels, ts_cnn_features, n_classes, training_epochs=50)  
    # ensemble the results to get combined prediction
    return ensemble_results(mnn_probs, mnn_pred, cnn_2d_probs)
    
#***********************************************************************************************#
#                                                                                               #
#   Module:                                                                                     #
#   ensemble_results()                                                                          #
#                                                                                               #
#   Description:                                                                                #
#   Ensemble the results of all the models and return top 3 predictions.                        #
#                                                                                               #
#***********************************************************************************************#
def ensemble_results(mnn_probs, mnn_pred, cnn_2d_probs):
    # create a local ensemble output variable
    ensembled_output = np.zeros(shape=(mnn_probs.shape[0], mnn_probs.shape[1]))
    # add the mnn predictions to the ensemble output
    for row, columns in enumerate(mnn_pred):
        for i, column in enumerate(columns):
            ensembled_output[row, column] += mnn_probs[row, i]
    # add the 2D cnn predictions to the ensemble output
    ensembled_output = ensembled_output + cnn_2d_probs
    #for row, columns in enumerate(cnn_2d_pred):
    #    for i, column in enumerate(columns):
    #        ensembled_output[row, column] += cnn_2d_probs[row, i]
    # extract top three predictions
    top3 = ensembled_output.argsort()[:,-3:][:,::-1]
    # return the top 3 results
    return top3

#***********************************************************************************************#
#                                                                                               #
#   Module:                                                                                     #
#   tensor_multilayer_neural_network()                                                          #
#                                                                                               #
#   Description:                                                                                #
#   Using tensorflow library to build a simple multi layer neural network.                      #
#                                                                                               #
#***********************************************************************************************#
def tensor_multilayer_neural_network(tr_features, tr_labels, ts_features, n_classes, training_epochs):
    # initialize the beginning paramters.
    n_dim = tr_features.shape[1]
    n_hidden_units_1 =  200   #280 
    n_hidden_units_2 =  250  #300
    n_hidden_units_3 =  300  #300
    
    sd = 1 / np.sqrt(n_dim)
    
    # one hot encode from training labels 
    tr_labels = to_categorical(tr_labels)  
    
    X = tf.placeholder(tf.float32,[None,n_dim])
    Y = tf.placeholder(tf.float32,[None,n_classes])

    # initializing starting learning rate - will use decaying technique
    global_step = tf.Variable(0, trainable=False)
    learning_rate = tf.train.exponential_decay(0.005, global_step, 500, 0.95, staircase=True)
    
    # initialize layer 1 parameters
    W_1 = tf.Variable(tf.random_normal([n_dim,n_hidden_units_1], mean = 0, stddev=sd))
    b_1 = tf.Variable(tf.random_normal([n_hidden_units_1], mean = 0, stddev=sd))
    h_1 = tf.nn.tanh(tf.matmul(X,W_1) + b_1)

    # initialize layer 2 parameters
    W_2 = tf.Variable(tf.random_normal([n_hidden_units_1,n_hidden_units_2], mean = 0, stddev=sd))
    b_2 = tf.Variable(tf.random_normal([n_hidden_units_2], mean = 0, stddev=sd))
    h_2 = tf.nn.sigmoid(tf.matmul(h_1,W_2) + b_2)

    # initialize layer 3 parameters
    W_3 = tf.Variable(tf.random_normal([n_hidden_units_2,n_hidden_units_3], mean = 0, stddev=sd))
    b_3 = tf.Variable(tf.random_normal([n_hidden_units_3], mean = 0, stddev=sd))
    h_3 = tf.nn.sigmoid(tf.matmul(h_2,W_3) + b_3)
    
    W = tf.Variable(tf.random_normal([n_hidden_units_3,n_classes], mean = 0, stddev=sd))
    b = tf.Variable(tf.random_normal([n_classes], mean = 0, stddev=sd))
    y_ = tf.nn.softmax(tf.matmul(h_3,W) + b)

    cost_function = -tf.reduce_sum(Y * tf.log(y_))
    optimizer = tf.train.AdamOptimizer(learning_rate).minimize(cost_function, global_step=global_step)

    init = tf.global_variables_initializer()
    
    cost_history = np.empty(shape=[1],dtype=float)
    y_pred = None
    with tf.Session() as sess:
        sess.run(init)
        for epoch in range(training_epochs):            
            # print a log message for status update
            utils.write_log_msg("running the mnn training epoch {0}...".format(epoch+1))
            # running the training_epoch numbered epoch
            _,cost = sess.run([optimizer,cost_function],feed_dict={X:tr_features,Y:tr_labels})
            cost_history = np.append(cost_history,cost)
        # predict results based on the trained model
        y_pred = sess.run(tf.argmax(y_,1),feed_dict={X: ts_features})
        y_k_probs, y_k_pred = sess.run(tf.nn.top_k(y_, k=n_classes), feed_dict={X: ts_features})

    # plot cost history
    df = pd.DataFrame(cost_history)
    df.to_csv("../data/cost_history_mnn.csv")

    # return the predicted values back to the calling program
    return y_pred, y_k_probs, y_k_pred

#***********************************************************************************************#
#                                                                                               #
#   Module:                                                                                     #
#   convolution_1D()                                                                            #
#                                                                                               #
#   Description:                                                                                #
#   Building a 1 dimentional convolutional network for training and prediction of audio tags.   #
#                                                                                               #
#***********************************************************************************************#
def convolution_1D(tr_features, tr_labels, ts_features, n_classes, training_epochs):

    # CNN parameters
    feature_size = 2460 #60x41
    num_labels = 10
    num_channels = 2

    batch_size = 50
    kernel_size = 30
    depth = 20
    num_hidden = 200

    learning_rate = 0.01

    # Create CNN model
    X = tf.placeholder(tf.float32, shape=[None,feature_size,num_channels])
    Y = tf.placeholder(tf.float32, shape=[None,num_labels])

    cov = apply_convolution(kernel_size,num_channels,depth,1)

    shape = cov.get_shape().as_list()
    cov_flat = tf.reshape(cov, [-1, shape[1] * shape[2] * shape[3]])

    f_weights = weight_variable([shape[1] * shape[2] * depth, num_hidden])
    f_biases = bias_variable([num_hidden])
    f = tf.nn.sigmoid(tf.add(tf.matmul(cov_flat, f_weights),f_biases))

    out_weights = weight_variable([num_hidden, num_labels])
    out_biases = bias_variable([num_labels])
    y_ = tf.nn.softmax(tf.matmul(f, out_weights) + out_biases)

    loss = -tf.reduce_sum(Y * tf.log(y_))
    optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(loss)
    correct_prediction = tf.equal(tf.argmax(y_,1), tf.argmax(Y,1))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

    # Train CNN
    cost_history = np.empty(shape=[1],dtype=float)
    with tf.Session() as session:
        tf.initialize_all_variables().run()

        for itr in range(training_epochs):    
            offset = (itr * batch_size) % (tr_labels.shape[0] - batch_size)
            batch_x = tr_features[offset:(offset + batch_size), :, :, :]
            batch_y = tr_labels[offset:(offset + batch_size), :]
            
            _, c = session.run([optimizer, loss],feed_dict={X: batch_x, Y : batch_y})
            cost_history = np.append(cost_history,c)

        # predict results based on the trained model
        y_pred = session.run(tf.argmax(y_,1),feed_dict={X: ts_features})
        y_k_probs, y_k_pred = session.run(tf.nn.top_k(y_, k=n_classes), feed_dict={X: ts_features})
        
    # plot cost history
    df = pd.DataFrame(cost_history)
    df.to_csv("../data/cost_history_cnn_1d.csv")

    # return the predicted values back to the calling program
    return y_pred, y_k_probs, y_k_pred

#***********************************************************************************************#
#                                                                                               #
#   Module:                                                                                     #
#   kerass_convolution_2D()                                                                     #
#                                                                                               #
#   Description:                                                                                #
#   Building a 2 dimentional convolutional network for training and prediction of audio tags.   #
#                                                                                               #
#***********************************************************************************************#
def keras_convolution_2D(tr_features, tr_labels, ts_features, n_classes, training_epochs):
    config = Config(sampling_rate=44100, audio_duration=2, n_folds=10, learning_rate=0.001, use_mfcc=True, n_mfcc=40)
    PREDICTION_FOLDER = "predictions_2d_conv"
    if not os.path.exists(PREDICTION_FOLDER):
        os.mkdir(PREDICTION_FOLDER)
    if os.path.exists('logs/' + PREDICTION_FOLDER):
        shutil.rmtree('logs/' + PREDICTION_FOLDER)

    skf = StratifiedKFold(tr_labels, n_folds=config.n_folds)    
    cost_history = np.empty(shape=[1],dtype=float)
    
    # one hot encode from training labels 
    tr_labels = to_categorical(tr_labels)  
    
    # predictions array for each fold of training
    pred_list = []
    
    for i, (train_split, val_split) in enumerate(skf):
        K.clear_session()
        X, y, X_val, y_val = tr_features[train_split], tr_labels[train_split], tr_features[val_split], tr_labels[val_split]
        checkpoint = ModelCheckpoint('best_%d.h5'%i, monitor='val_loss', verbose=1, save_best_only=True)
        early = EarlyStopping(monitor="val_loss", mode="min", patience=5)
        tb = TensorBoard(log_dir='./logs/' + PREDICTION_FOLDER + '/fold_%i'%i, write_graph=True)
        callbacks_list = [checkpoint, early, tb]
        print("#"*50)
        print("Fold: ", i)
        model = get_2d_conv_model(config)
        history = model.fit(X, y, validation_data=(X_val, y_val), callbacks=callbacks_list, batch_size=64, epochs=training_epochs)
        model.load_weights('best_%d.h5'%i)
        # Save test predictions
        predictions = model.predict(ts_features, batch_size=64, verbose=1)
        pred_list.append(predictions)
        # append history
        cost_history = np.append(cost_history,history)

    # final processing to ensemble 2D prediction results    
    prediction = np.ones_like(pred_list[0])
    for pred in pred_list:
        prediction = prediction*pred
    prediction = prediction**(1./len(pred_list))
    
    # plot cost history
    df = pd.DataFrame(cost_history)
    df.to_csv("../data/cost_history_cnn_2d.csv")
    
    # return the predicted values back to the calling program
    return prediction

#***********************************************************************************************#
#                                                                                               #
#   Module:                                                                                     #
#   helper functions                                                                            #
#                                                                                               #
#   Description:                                                                                #
#   Helper functions for building a 2D convolutional network using keras library.               #
#                                                                                               #
#***********************************************************************************************#
def get_2d_conv_model(config):
    
    nclass = config.n_classes
    
    inp = Input(shape=(config.dim[0],config.dim[1],1))
    x = Convolution2D(32, (4,10), padding="same")(inp)
    x = BatchNormalization()(x)
    x = Activation("relu")(x)
    x = MaxPool2D()(x)
    
    x = Convolution2D(32, (4,10), padding="same")(x)
    x = BatchNormalization()(x)
    x = Activation("relu")(x)
    x = MaxPool2D()(x)
    
    x = Convolution2D(32, (4,10), padding="same")(x)
    x = BatchNormalization()(x)
    x = Activation("relu")(x)
    x = MaxPool2D()(x)
    
    x = Convolution2D(32, (4,10), padding="same")(x)
    x = BatchNormalization()(x)
    x = Activation("relu")(x)
    x = MaxPool2D()(x)

    x = Flatten()(x)
    x = Dense(64)(x)
    x = BatchNormalization()(x)
    x = Activation("relu")(x)
    out = Dense(nclass, activation=softmax)(x)

    model = models.Model(inputs=inp, outputs=out)
    opt = optimizers.Adam(config.learning_rate)

    model.compile(optimizer=opt, loss=losses.categorical_crossentropy, metrics=['acc'])
    return model
 
       
#***********************************************************************************************#
#                                                                                               #
#   Module:                                                                                     #
#   helper functions                                                                            #
#                                                                                               #
#   Description:                                                                                #
#   Helper functions for building a 2D convolutional network.                                   #
#                                                                                               #
#***********************************************************************************************#
def weight_variable(shape):
    initial = tf.truncated_normal(shape, stddev = 0.1)
    return tf.Variable(initial)

def bias_variable(shape):
    initial = tf.constant(1.0, shape = shape)
    return tf.Variable(initial)

def apply_convolution(x,kernel_size,num_channels,depth, dimension):
    weights = weight_variable([kernel_size, kernel_size, num_channels, depth])
    biases = bias_variable([depth])
    if(dimension == 1):
        cov_function = tf.nn.conv1d(x,weights,strides=[1,2,2,1], padding='VALID')
    else:
        cov_function = tf.nn.conv2d(x,weights,strides=[1,2,2,1], padding='SAME')
    return tf.nn.relu(tf.add(cov_function,biases))

def apply_max_pool(x,kernel_size,stride_size):
    return tf.nn.max_pool(x, ksize=[1, kernel_size, kernel_size, 1], strides=[1, stride_size, stride_size, 1], padding='SAME')

