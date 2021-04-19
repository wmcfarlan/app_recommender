import gzip
import pandas as pd

def parse(path):
    """
    Opens gzipped file for getDF to read
    """
    g = gzip.open(path, 'rb')
    for l in g:
        yield eval(l)

def getDF(path):
    """
    getDF will use parse to fill a dictionary with key value pairs in parsed json file
    
    Returns
    -------
    Pandas Dataframe object
    """
    i = 0
    df = {}
    for d in parse(path):
        df[i] = d
        i += 1
    return pd.DataFrame.from_dict(df, orient='index')


if __name__ == '__main__':
    print('main')
    
    
#             """
#         Info HERE
        
#         Arguments
#         ---------

#         arg_1: just info
#                 about args
#         arg_2: more info

#         Returns
#         -------

#         here is what is
#             retruned
#         """