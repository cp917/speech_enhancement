"""
Summary:  Prepare data. 
Author:   Qiuqiang Kong
Created:  2017.12.22
Modified: - 
"""
import tensorflow as tf
import librosa
import os
import soundfile
import numpy as np
import argparse
import csv
import time
#import matplotlib.pyplot as plt
from scipy import signal
import pickle
#import pickle as cPickle
import cPickle
import h5py
from sklearn import preprocessing
import random
import prepare_data as pp_data
import config as cfg


def create_folder(fd):
    if not os.path.exists(fd):
        os.makedirs(fd)



    

def parser_function(serialized_example):
    features = tf.parse_single_example(serialized_example,
    features={
        'x': tf.FixedLenFeature([], tf.string),
        'y': tf.FixedLenFeature([], tf.string)
        })
    x = tf.reshape(tf.decode_raw(features['x'], tf.float32), [7, 257])
    y = tf.reshape(tf.decode_raw(features['y'], tf.float32), [257,])
    return x, y


def load_tfrecord(batch, repeat, data_path):
    dataset = tf.data.TFRecordDataset(data_path)
    dataset = dataset.map(parser_function)
    dataset = dataset.shuffle(random.randint(1, 100))
    dataset = dataset.batch(batch)
    dataset = dataset.repeat(repeat)
    iterator = dataset.make_one_shot_iterator()
    tr_x, tr_y  = iterator.get_next()
    return tr_x, tr_y




def scale_on_2d(x2d, scaler):
    """Scale 2D array data. 
    """
    return scaler.transform(x2d)
    
def scale_on_3d(x3d, scaler):
    """Scale 3D array data. 
    """
    (n_segs, n_concat, n_freq) = x3d.shape
    x2d = x3d.reshape((n_segs * n_concat, n_freq))
    x2d = scaler.transform(x2d)
    x3d = x2d.reshape((n_segs, n_concat, n_freq))
    return x3d
    
def inverse_scale_on_2d(x2d, scaler):
    """Inverse scale 2D array data. 
    """
    return x2d * scaler.scale_[None, :] + scaler.mean_[None, :]
    


def load_hdf5(hdf5_path):
    """Load hdf5 data. 
    """
    with h5py.File(hdf5_path, 'r') as hf:
        x = hf.get('x')
        y = hf.get('y')
        x = np.array(x)     # (n_segs, n_concat, n_freq)
        y = np.array(y)     # (n_segs, n_freq)        
    return x, y






def tfrecord_handler():
    workspace = "workspace"
    data_type = "IRM"
    if data_type=="DM":
        tr_hdf5_path = os.path.join(workspace, "packed_features", "spectrogram", "train", "mixdb", "data.h5")
    else:
        tr_hdf5_path = os.path.join(workspace, "packed_features", "spectrogram", "train", "mask_mixdb", "data100000.h5")
    (tr_x, tr_y) = load_hdf5(tr_hdf5_path)
    scaler_path = os.path.join(workspace, "packed_features", "spectrogram", "train", "mixdb", "scaler.p")
    scaler = pickle.load(open(scaler_path, 'rb'))
    tr_x = scale_on_3d(tr_x, scaler)
    if data_type=="DM":
        tr_y = scale_on_2d(tr_y, scaler)
    tfrecords_train_filename = 'workspace/tfrecords/train/mask_mixdb/data_chinese.tfrecords'
    create_folder(os.path.dirname(tfrecords_train_filename))
    writer_train = tf.python_io.TFRecordWriter(tfrecords_train_filename)
    for i in range(tr_x.shape[0]):
        mixed_input = tr_x[i, :, :].astype(np.float32).tostring()
        label = tr_y[i, :].astype(np.float32).tostring()
        example = tf.train.Example(features=tf.train.Features(
                        feature={
                        'x': tf.train.Feature(bytes_list = tf.train.BytesList(value=[mixed_input])),
                        'y': tf.train.Feature(bytes_list = tf.train.BytesList(value=[label]))
                            }))
        writer_train.write(example.SerializeToString())
        if i % 100000 == 0:
            print(i)

    writer_train.close()












def mix_tfrecord():
    tr_hdf5_dir = os.path.join("workspace", "tfrecords", "train", "crn_mixdb")
    tr_hdf5_names = os.listdir(tr_hdf5_dir)
    tr_path_list = [os.path.join(tr_hdf5_dir, i) for i in tr_hdf5_names]
    sess = tf.Session()
    x, y = load_tfrecord(batch = 1, repeat = 1, data_path = tr_path_list)
    tfrecords_train_filename = '/data00/wangjinchao/sednn-master/mixture2clean_dnn/workspace/tfrecords/train/mixdb/data_office.tfrecords'
    create_folder(os.path.dirname(tfrecords_train_filename))
    writer_train = tf.python_io.TFRecordWriter(tfrecords_train_filename)
    try:
        while True:
            [tr_x, tr_y] = sess.run([x, y])
            mixed_input = tr_x.astype(np.float32).tostring()
            label = tr_y.astype(np.float32).tostring()
            example = tf.train.Example(features=tf.train.Features(
                            feature={
                            'x': tf.train.Feature(bytes_list = tf.train.BytesList(value=[mixed_input])),
                            'y': tf.train.Feature(bytes_list = tf.train.BytesList(value=[label]))
                                }))
            writer_train.write(example.SerializeToString())
    except tf.errors.OutOfRangeError:
        writer_train.close()













def compute_gv():
    mean_y = np.mean(tr_y)
    tmp_y= np.power((tr_y - mean_y), 2)
    gv_ref_independent = np.mean(tmp_y)
    
    mean_y = np.mean(tr_y, axis = 0)
    tmp_y = np.power((tr_y - mean_y), 2)
    gv_ref_dependent = np.mean(tmp_y, axis = 0)

    mean_pred_y = np.mean(pred_y)
    tmp_pred_y= np.power((pred_y - mean_pred_y), 2)
    gv_est_independent = np.mean(tmp_pred_y)

    mean_pred_y = np.mean(pred_y, axis = 0)
    tmp_pred_y = np.power((pred_y - mean_pred_y), 2)
    gv_est_dependent = np.mean(tmp_pred_y, axis = 0)








gv_ref_independent = 1.2445884
gv_est_independent = 1.047566

gv_ref_dependent = np.array([0.8188001 , 0.7655154 , 1.0443362 , 1.291341  , 1.3091451 ,
       1.3863533 , 1.3579204 , 1.3562269 , 1.3332679 , 1.3779601 ,
       1.3638331 , 1.4141914 , 1.4132004 , 1.414608  , 1.4191983 ,
       1.3779674 , 1.3744586 , 1.4065691 , 1.405165  , 1.3589902 ,
       1.3695769 , 1.3828198 , 1.399761  , 1.4110584 , 1.4237365 ,
       1.4146262 , 1.4150872 , 1.4020557 , 1.4402065 , 1.4247525 ,
       1.4152107 , 1.3777906 , 1.4041775 , 1.411573  , 1.4258041 ,
       1.4248255 , 1.4343295 , 1.4284252 , 1.3958426 , 1.3800949 ,
       1.394799  , 1.402656  , 1.3995781 , 1.3867273 , 1.4019246 ,
       1.394503  , 1.3876013 , 1.3906093 , 1.3923353 , 1.3908792 ,
       1.3651602 , 1.3789821 , 1.3817782 , 1.3878808 , 1.3868887 ,
       1.389586  , 1.3882133 , 1.3948598 , 1.3833323 , 1.3911697 ,
       1.3947376 , 1.3785598 , 1.3657677 , 1.3754646 , 1.3744026 ,
       1.36841   , 1.3738396 , 1.375986  , 1.3782787 , 1.3705876 ,
       1.3561313 , 1.363172  , 1.3721641 , 1.3663605 , 1.3701444 ,
       1.3718685 , 1.3587731 , 1.3583094 , 1.3632051 , 1.3683681 ,
       1.3819396 , 1.3825235 , 1.378892  , 1.3761448 , 1.3808253 ,
       1.3743024 , 1.367832  , 1.3641973 , 1.3663458 , 1.369809  ,
       1.371535  , 1.3641069 , 1.363354  , 1.3653663 , 1.3578664 ,
       1.3501805 , 1.3377979 , 1.3453208 , 1.3447514 , 1.3466262 ,
       1.3516669 , 1.3419527 , 1.3322309 , 1.3304617 , 1.3314892 ,
       1.3222749 , 1.3076648 , 1.3175845 , 1.3237734 , 1.3146265 ,
       1.3085129 , 1.3097675 , 1.3060361 , 1.299763  , 1.2958938 ,
       1.2963424 , 1.2883214 , 1.2881285 , 1.2870046 , 1.2888812 ,
       1.2778481 , 1.2760473 , 1.2680486 , 1.2644651 , 1.2633371 ,
       1.2600574 , 1.2674776 , 1.2619113 , 1.25404   , 1.2484775 ,
       1.2528795 , 1.2445921 , 1.2449573 , 1.2370106 , 1.240662  ,
       1.2343256 , 1.2296497 , 1.2207483 , 1.2245104 , 1.212012  ,
       1.2099534 , 1.2040404 , 1.2014705 , 1.2012196 , 1.1975276 ,
       1.1931353 , 1.1944716 , 1.1941463 , 1.1930957 , 1.1830707 ,
       1.1817104 , 1.1773063 , 1.1705128 , 1.1806594 , 1.1794373 ,
       1.175316  , 1.1757798 , 1.1782918 , 1.1770912 , 1.1753559 ,
       1.1691241 , 1.1691626 , 1.1616837 , 1.1592903 , 1.1525471 ,
       1.148833  , 1.1445248 , 1.1463698 , 1.1432943 , 1.1372362 ,
       1.1345378 , 1.1331203 , 1.1327978 , 1.1356372 , 1.1281763 ,
       1.117315  , 1.1229038 , 1.1331227 , 1.129955  , 1.1205344 ,
       1.1168914 , 1.1162447 , 1.1205385 , 1.1221027 , 1.1183283 ,
       1.1176765 , 1.1073152 , 1.1065495 , 1.1066844 , 1.1020577 ,
       1.0956546 , 1.0937659 , 1.0824373 , 1.0914868 , 1.0957388 ,
       1.0990036 , 1.0980628 , 1.1037108 , 1.0973698 , 1.0961391 ,
       1.0953025 , 1.09513   , 1.093008  , 1.0896668 , 1.0927784 ,
       1.0900792 , 1.0936061 , 1.0935822 , 1.0972129 , 1.0939381 ,
       1.0888202 , 1.0845745 , 1.0836582 , 1.0842501 , 1.0809636 ,
       1.0757244 , 1.076439  , 1.0760363 , 1.0668286 , 1.0531492 ,
       1.0502294 , 1.0589144 , 1.0721456 , 1.0731709 , 1.0684367 ,
       1.0632014 , 1.0599935 , 1.0586678 , 1.0569472 , 1.0625534 ,
       1.0626838 , 1.0648353 , 1.0663067 , 1.06597   , 1.0638473 ,
       1.0639621 , 1.0637795 , 1.0606909 , 1.0582322 , 1.0517532 ,
       1.0480362 , 1.0479565 , 1.0435289 , 1.0371186 , 1.0334498 ,
       1.0291612 , 1.0249708 , 1.0198319 , 1.0156595 , 1.0108268 ,
       1.0073904 , 1.0044657 , 1.0021349 , 1.0046784 , 1.0016526 ,
       0.99999756, 0.9964546 ])



gv_est_dependent = np.array([0.18696505, 0.34280822, 0.72116977, 1.0536233 , 1.0966913 ,
       1.1637543 , 1.1548996 , 1.1676413 , 1.1474363 , 1.171958  ,
       1.1660068 , 1.2174896 , 1.2271285 , 1.2325336 , 1.2390236 ,
       1.2042515 , 1.2004554 , 1.2231534 , 1.2235614 , 1.1827441 ,
       1.1899538 , 1.1991223 , 1.2111914 , 1.2175452 , 1.2235477 ,
       1.213116  , 1.2148174 , 1.1969019 , 1.221351  , 1.2065829 ,
       1.2010144 , 1.1644497 , 1.1922417 , 1.1955268 , 1.2043128 ,
       1.1993589 , 1.2122489 , 1.2041621 , 1.1712927 , 1.1558433 ,
       1.1670535 , 1.1739376 , 1.171306  , 1.1575273 , 1.1754738 ,
       1.1698086 , 1.1619811 , 1.1717362 , 1.1703048 , 1.1663839 ,
       1.146894  , 1.1596279 , 1.1625977 , 1.1698763 , 1.1666222 ,
       1.1692064 , 1.1689862 , 1.1767648 , 1.1620858 , 1.1627572 ,
       1.167898  , 1.160154  , 1.1409459 , 1.1539472 , 1.1525996 ,
       1.1464965 , 1.144994  , 1.147802  , 1.1467297 , 1.1443332 ,
       1.1305172 , 1.1382952 , 1.1508311 , 1.1470501 , 1.1399091 ,
       1.1442221 , 1.1377715 , 1.1442518 , 1.1429965 , 1.1489736 ,
       1.1564287 , 1.157903  , 1.1531717 , 1.1507055 , 1.1558954 ,
       1.148154  , 1.1464262 , 1.140695  , 1.1445204 , 1.1501266 ,
       1.1467679 , 1.1315886 , 1.1395706 , 1.138759  , 1.1322058 ,
       1.1181237 , 1.11835   , 1.11936   , 1.1205423 , 1.1255524 ,
       1.1306192 , 1.1268992 , 1.113448  , 1.1130816 , 1.1138029 ,
       1.1083379 , 1.0993805 , 1.1055454 , 1.1122226 , 1.1078554 ,
       1.1074036 , 1.100761  , 1.1006709 , 1.1015122 , 1.09618   ,
       1.0973667 , 1.0900112 , 1.085913  , 1.081041  , 1.0914049 ,
       1.0785384 , 1.0716164 , 1.0673122 , 1.0675014 , 1.0644028 ,
       1.0625845 , 1.0691746 , 1.0601567 , 1.0490003 , 1.0468317 ,
       1.0543352 , 1.0443738 , 1.0391475 , 1.0349274 , 1.043713  ,
       1.0387459 , 1.0371169 , 1.0293257 , 1.0260344 , 1.0175334 ,
       1.0159734 , 1.0076747 , 1.0029306 , 1.0055224 , 0.9981165 ,
       0.9971783 , 0.99703634, 0.9997423 , 0.9974254 , 0.98594177,
       0.9810835 , 0.9804084 , 0.9802749 , 0.9853521 , 0.98604727,
       0.9816301 , 0.97491074, 0.9801819 , 0.9790348 , 0.98185617,
       0.97771597, 0.9796749 , 0.9697705 , 0.96665776, 0.9637393 ,
       0.9561936 , 0.94966286, 0.9454328 , 0.94490314, 0.94937634,
       0.9478694 , 0.9447655 , 0.94176424, 0.9403081 , 0.94139105,
       0.9293294 , 0.93296844, 0.9450051 , 0.94217265, 0.9318225 ,
       0.9312917 , 0.93434596, 0.9384418 , 0.93287736, 0.9366608 ,
       0.9325247 , 0.9249665 , 0.9251077 , 0.92365205, 0.920737  ,
       0.9119053 , 0.90590674, 0.9011289 , 0.915063  , 0.9160822 ,
       0.92288536, 0.91581845, 0.92356586, 0.9192137 , 0.918826  ,
       0.9247057 , 0.9222291 , 0.91558635, 0.90998685, 0.9195295 ,
       0.9112585 , 0.9219293 , 0.91975945, 0.918718  , 0.91701937,
       0.917412  , 0.90922654, 0.90436333, 0.9087872 , 0.9071029 ,
       0.90249467, 0.9022592 , 0.90647477, 0.89404655, 0.8869796 ,
       0.8787871 , 0.8882476 , 0.90208715, 0.9047103 , 0.9043998 ,
       0.90141785, 0.8983854 , 0.89462155, 0.90119785, 0.9028099 ,
       0.90848804, 0.91339225, 0.9102626 , 0.9124032 , 0.9146076 ,
       0.9150387 , 0.92100835, 0.9140667 , 0.91219926, 0.91785675,
       0.92215157, 0.9197757 , 0.9274899 , 0.9233789 , 0.9288496 ,
       0.92639154, 0.9255196 , 0.9201056 , 0.9202775 , 0.9202095 ,
       0.92024976, 0.9177347 , 0.9155735 , 0.921838  , 0.91567504,
       0.9140105 , 0.85075736] )




