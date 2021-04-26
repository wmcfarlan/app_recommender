sys.path.append('../models')
from rec_net import *


from zipfile import ZipFile
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from pathlib import Path
import matplotlib.pyplot as plt
from flask import send_file


import pandas as pd
import numpy as np
import itertools
from collections import defaultdict

# visualization libraries
import matplotlib.pyplot as plt


# show images
from PIL import Image
import requests
import json
from io import BytesIO

# keras imports
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from pathlib import Path
from keras.layers import Concatenate, Dense, Dropout
from keras.layers import Add, Activation, Lambda, Input, Embedding
from keras.models import Model
from keras.layers import Input, Reshape, Dot
from keras.layers.embeddings import Embedding
from keras.optimizers import Adam
from keras.regularizers import l2


# sklearn
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

# ignore warnings
import warnings
warnings.filterwarnings("ignore")

# image imports


class get_predictions:
    """
    Creates predictions for each item in pivot_df space to fill out missing data


    Arguments
    ---------
    model: sklearn regressor, the parameters can be user selected


    Returns
    ---------
    Returns a dictionary with the name of each product and predictions for each user

        """
        

    def __init__(self, dataframe):
        self.dataframe = dataframe
        self.original_dataframe = dataframe

    def prepare_dataframe(self):
        self.dataframe = self.dataframe[self.dataframe['title'].notna()]

        # select reviewer and product values
        customers = self.dataframe['reviewerID'].value_counts()
        products = self.dataframe['asin'].value_counts()

        # filter by 10 reviews per product per customer, products with 20 or more reviews
        customers = customers[customers >= 10]
        products = products[products >= 20]

        # set cut down dataframe
        self.dataframe = self.dataframe.merge(pd.DataFrame(
            {'reviewerID': customers.index})).merge(pd.DataFrame({'asin': products.index}))

        # shuffle dataframe
        self.dataframe = self.dataframe.sample(
            frac=1, random_state=42).reset_index(drop=True)

        # set format
        self.dataframe = self.dataframe[['reviewerID', 'asin', 'overall']]

    def get_mappings(self):
        # unique list of uers and product ids
        user_ids = self.dataframe['reviewerID'].unique().tolist()
        product_ids = self.dataframe['asin'].unique().tolist()

        # map correct numerical format and keep in dictionaries to call later
        self.user2user_encoded = {x: i for i, x in enumerate(user_ids)}
        self.userencoded2user = {i: x for i, x in enumerate(user_ids)}

        self.product2product_encoded = {
            x: i for i, x in enumerate(product_ids)}
        self.product_encoded2product = {
            i: x for i, x in enumerate(product_ids)}

    def set_mappings(self):
        self.dataframe['user'] = self.dataframe['reviewerID'].map(
            self.user2user_encoded)
        self.dataframe['product'] = self.dataframe['asin'].map(
            self.product2product_encoded)

        # set number of users and products
        self.num_users = len(self.user2user_encoded)
        self.num_products = len(self.product_encoded2product)

        # ensure correct value format
        self.dataframe['overall'] = self.dataframe['overall'].values.astype(
            np.float32)

        # set min and max ratings
        self.min_rating = min(self.dataframe['overall'])
        self.max_rating = max(self.dataframe['overall'])

    def normalize(self):

        # set x and y with normalization
        self.x = self.dataframe[['user', 'product']].values
        self.y = self.dataframe['overall'].apply(lambda x: (
            x - self.min_rating) / (self.max_rating - self.min_rating)).values

    def train_test(self):
        train_indices = int(0.9 * self.dataframe.shape[0])
        self.x_train, self.x_val, self.y_train, self.y_val = (
            self.x[:train_indices],
            self.x[train_indices:],
            self.y[:train_indices],
            self.y[train_indices:])
        return self.x_train, self.y_train

    def model(self):
        self.model = RecommenderNet(
            num_users=8665, num_products=4342, embedding_size=50)
        self.model.compile(loss=tf.keras.losses.MeanSquaredError(),
                           optimizer=keras.optimizers.Adam(lr=0.001))
        self.model.train_on_batch(self.x_train[:1], self.y_train[:1])
        self.model.load_weights('../models/model_weights')

    def get_user_preds(self, num_id):
        

        user_id = self.userencoded2user[num_id]

        products_bought_by_user = self.dataframe[self.dataframe.reviewerID == user_id]
        x = self.dataframe[self.dataframe.user == user_id]['product'].values
        products_not_bought = self.dataframe[~self.dataframe['asin'].isin(
            x)]['asin'].unique()

        products_not_bought = list(
            set(products_not_bought).intersection(
                set(self.product2product_encoded.keys()))
        )

        products_not_bought = [
            [self.product2product_encoded.get(x)] for x in products_not_bought]

        user_encoder = self.user2user_encoded.get(user_id)
        user_product_array = np.hstack(
            ([[user_encoder]] * len(products_not_bought), products_not_bought)
        )

        ratings = self.model.predict(user_product_array).flatten()
        top_ratings_indices = ratings.argsort()[-10:][::-1]

        recommended_product_ids = [
            self.product_encoded2product.get(products_not_bought[x][0]) for x in top_ratings_indices
        ]

        top_products_user = (
            products_bought_by_user.sort_values(by="overall", ascending=False)
            .head(5)
            .asin.values
        )

        original_df_rows = self.original_dataframe[self.original_dataframe["asin"].isin(
            top_products_user)][['asin', 'title', 'imUrl']].drop_duplicates()
        self.item_dict = defaultdict(list)
        for row in original_df_rows.itertuples():
            title = row['title']
#             url = row.imUrl
            # image = Image.open(requests.get(url, stream=True).raw)
            self.item_dict['bought'].append(title)

        recommended_products = self.original_dataframe[self.original_dataframe["asin"].isin(
            recommended_product_ids)][['asin', 'title', 'imUrl']].drop_duplicates()
        for row in recommended_products.itertuples():
            title = row['title']
#             url = row.imUrl
            # image = Image.open(requests.get(url, stream=True).raw)
            self.item_dict['recommended'].append(title)

    def process(self, num_id):
        self.prepare_dataframe()
        self.get_mappings()
        self.set_mappings()
        self.normalize()
        self.train_test()
        self.model()
        self.get_user_preds(num_id)
        return self.item_dict


def print_imgs(url_list):
    fig = plt.figure(figsize=(10, 7))

    # setting values to rows and column variables
    rows = 1
    columns = 5

    # reading images
    Image1 = Image.open(requests.get(url_list[0], stream=True).raw)
    Image2 = Image.open(requests.get(url_list[1], stream=True).raw)
    Image3 = Image.open(requests.get(url_list[2], stream=True).raw)
    Image4 = Image.open(requests.get(url_list[3], stream=True).raw)
    Image5 = Image.open(requests.get(url_list[4], stream=True).raw)

    # Adds a subplot at the 1st position
    fig.add_subplot(rows, columns, 1)

    # showing image
    plt.imshow(Image1)
    plt.axis('off')

    # Adds a subplot at the 2nd position
    fig.add_subplot(rows, columns, 2)

    # showing image
    plt.imshow(Image2)
    plt.axis('off')

    fig.add_subplot(rows, columns, 3)

    # showing image
    plt.imshow(Image3)
    plt.axis('off')

    fig.add_subplot(rows, columns, 4)

    # showing image
    plt.imshow(Image4)
    plt.axis('off')

    fig.add_subplot(rows, columns, 5)

    # showing image
    plt.imshow(Image5)
    plt.axis('off')

    return plt.show()


def print_imgs_cold(url_list):
    fig = plt.figure(figsize=(10, 7))

    # setting values to rows and column variables
    rows = 2
    columns = 5

    # reading images
    Image1 = Image.open(requests.get(url_list[0], stream=True).raw)
    Image2 = Image.open(requests.get(url_list[1], stream=True).raw)
    Image3 = Image.open(requests.get(url_list[2], stream=True).raw)
    Image4 = Image.open(requests.get(url_list[3], stream=True).raw)
    Image5 = Image.open(requests.get(url_list[4], stream=True).raw)
    Image6 = Image.open(requests.get(url_list[5], stream=True).raw)
    Image7 = Image.open(requests.get(url_list[6], stream=True).raw)
    Image8 = Image.open(requests.get(url_list[7], stream=True).raw)
    Image9 = Image.open(requests.get(url_list[8], stream=True).raw)
    Image10 = Image.open(requests.get(url_list[9], stream=True).raw)

    # Adds a subplot at the 1st position
    fig.add_subplot(rows, columns, 1)

    # showing image
    plt.imshow(Image1)
    plt.axis('off')

    # Adds a subplot at the 2nd position
    fig.add_subplot(rows, columns, 2)

    # showing image
    plt.imshow(Image2)
    plt.axis('off')

    fig.add_subplot(rows, columns, 3)

    # showing image
    plt.imshow(Image3)
    plt.axis('off')

    fig.add_subplot(rows, columns, 4)

    # showing image
    plt.imshow(Image4)
    plt.axis('off')

    fig.add_subplot(rows, columns, 5)

    # showing image
    plt.imshow(Image5)
    plt.axis('off')

    
    fig.add_subplot(rows, columns, 6)

    # showing image
    plt.imshow(Image6)
    plt.axis('off')
    
    fig.add_subplot(rows, columns, 7)

    # showing image
    plt.imshow(Image7)
    plt.axis('off')
    
    fig.add_subplot(rows, columns, 8)

    # showing image
    plt.imshow(Image8)
    plt.axis('off')
    
    fig.add_subplot(rows, columns, 9)

    # showing image
    plt.imshow(Image9)
    plt.axis('off')
    
    fig.add_subplot(rows, columns, 10)

    # showing image
    plt.imshow(Image10)
    plt.axis('off')
    
    return plt.show()


if __name__ == "__main__":
    print('main')

    df = pd.read_csv('../merged_df.csv')

    item_dict = get_predictions(df).process()

    print("Top 5 Purchased Items For User")
    print("------------------------------")
    print_imgs(item_dict['bought'])

    print("Top 5 Recommended Items For User")
    print("--------------------------------")
    print_imgs(item_dict['recommended'])
    
