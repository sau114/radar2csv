import configparser
import pandas as pd

config = configparser.ConfigParser(
    comment_prefixes=r'//',
    interpolation=None,
)
config.sections()

config.read(r'input\001_KO1_8_Контактный осветлитель 1.ini')

config.sections()

config['NetBios']

for key in config['NetBios']:
    print(key, config['NetBios'][key])

for key in config['Tags']:
    print(key, config['Tags'][key])

len(config['Tags']['tag4'].split(','))

len(config['Tags']['tag20'].split(','))

csv = pd.read_csv(
    'ko1.csv',
    sep=';',
    header=None,
)

csv.dropna(axis='columns', how='all')
