# convert ini-files from RADAR to CSV

import configparser
# import os
import os.path
import pandas as pd


def get_all_keys(section) -> list:
    return [k for k in section]


# Name = Type(R/W), [LinkFlag], [LinkMask], Descr, Period(s), Func, [Param1, Param2, ...]
NETBIOS_COLUMNS = [
    'dir_type',
    'link_flag',
    'link_mask',
    'description',
    'period',
    'function',
    'params',
]
NETBIOS_FUNCTION = [
    '&h40',  # чтение ИНР
    '&h00',  # установка входа алгоблока
    '&h10',  # чтение архива
    '&h11',  # чтение часов
    '&h12',  # установка часов
    '&h1A',  # запись ДКМ
]

# %key%=(Mask1, Value1), (Mask2, Value2)
SELECTORS_COLUMNS = [
    'mask_value',
]

# %key%=(TagName),[Parent],(Type),Description,InBuffer,InBufferOffset,[k,b],[Selector/BoolMask/NullZone], \
# [OutBuffer, OutBufferOffset],[Default],[DefaultMin],[DefaultMax],[Hysteresis],[InType],[OutType],[LinkFlag],[LinkMask]
TAGS_COLUMNS = [
    'tag_name',
    'tag_parent',
    'data_type',
    'description',
    'in_buf',
    'in_buf_off',
    'k',  # slope
    'b',  # intercept
    'selector',
    'out_buf',
    'out_buf_off',
    'default',
    'default_min',
    'default_max',
    'hysteresis',
    'in_type',
    'out_type',
    'link_flag',
    'link_mask',
]

OUTPUT_COLUMNS = [
    'tag_full_name',
    'description',
    'data_type',
    'direction',
    'ab_type',
    'ab_addr',
    'ab_off',
    'selector',
    'other',
]


def parse_section_netbios(section) -> pd.DataFrame:
    netbios_data = pd.DataFrame(
        index=get_all_keys(section),
        columns=NETBIOS_COLUMNS,
    )
    for k in netbios_data.index:
        values = section[k].split(',')
        for i in range(min(len(NETBIOS_COLUMNS), len(values))):
            netbios_data.loc[k, NETBIOS_COLUMNS[i]] = values[i].strip()
        if len(values) > len(NETBIOS_COLUMNS):
            netbios_data.loc[k, NETBIOS_COLUMNS[-1]] = ','.join(values[len(NETBIOS_COLUMNS):])
    return netbios_data.fillna('')


def parse_section_selectors(section) -> pd.DataFrame:
    selectors_data = pd.DataFrame(
        index=get_all_keys(section),
        columns=SELECTORS_COLUMNS,
    )
    for k in selectors_data.index:
        selectors_data.loc[k, SELECTORS_COLUMNS[0]] = section[k].strip()
    return selectors_data.fillna('')


def parse_section_tags(section) -> pd.DataFrame:
    tags_data = pd.DataFrame(
        index=get_all_keys(section),
        columns=TAGS_COLUMNS,
    )
    for k in tags_data.index:
        values = section[k].split(',')
        for i in range(min(len(TAGS_COLUMNS), len(values))):
            tags_data.loc[k, TAGS_COLUMNS[i]] = values[i].strip()
        if len(values) > len(TAGS_COLUMNS):
            tags_data.loc[k, TAGS_COLUMNS[-1]] = ','.join(values[len(TAGS_COLUMNS):])
    return tags_data.fillna('')


def gen_output_table(buffers: pd.DataFrame, selectors: pd.DataFrame, tags: pd.DataFrame) -> pd.DataFrame:
    # at first for reading tags
    tags_ = tags.copy()
    tags_['in_buf_off'] = pd.to_numeric(tags_['in_buf_off'])
    tags_ = tags_.sort_values(by=['in_buf', 'in_buf_off'], ignore_index=True)
    output = pd.DataFrame(columns=OUTPUT_COLUMNS, dtype='string')
    # all input tags
    for idx in tags_.index:
        if tags_.loc[idx, 'in_buf'] in buffers.index:
            if tags_.loc[idx, 'selector'] in selectors.index:
                selector = selectors.loc[tags_.loc[idx, 'selector'], 'mask_value']
            else:
                selector = tags_.loc[idx, 'selector']
            next_line = {
                'tag_full_name': tags_.loc[idx, 'tag_parent'] + '.' + tags_.loc[idx, 'tag_name'],
                'description': tags_.loc[idx, 'description'],
                'data_type': tags_.loc[idx, 'data_type'].lower(),
                'direction': buffers.loc[tags_.loc[idx, 'in_buf'], 'dir_type'],
                'ab_type': buffers.loc[tags_.loc[idx, 'in_buf'], 'function'],
                'ab_addr': buffers.loc[tags_.loc[idx, 'in_buf'], 'params'],
                'ab_off': tags_.loc[idx, 'in_buf_off'],
                'selector': selector,
                'other': ', '.join(tags_.loc[idx, ['k', 'b', 'default', 'default_min', 'default_max', 'hysteresis', 'in_type']].to_list())
            }
            output.loc[output.shape[0]] = next_line
        if tags_.loc[idx, 'out_buf'] in buffers.index:
            next_line = {
                'tag_full_name': tags_.loc[idx, 'tag_parent'] + '.' + tags_.loc[idx, 'tag_name'],
                'description': tags_.loc[idx, 'description'],
                'data_type': tags_.loc[idx, 'data_type'].lower(),
                'direction': buffers.loc[tags_.loc[idx, 'out_buf'], 'dir_type'],
                'ab_type': buffers.loc[tags_.loc[idx, 'out_buf'], 'function'],
                'ab_addr': buffers.loc[tags_.loc[idx, 'out_buf'], 'params'],
                'ab_off': tags_.loc[idx, 'out_buf_off'],
                'selector': '',
                'other': ', '.join(tags_.loc[idx, ['k', 'b', 'default', 'default_min', 'default_max', 'hysteresis', 'out_type']].to_list())
            }
            output.loc[output.shape[0]] = next_line
    # readability
    output['data_type'].replace({'single': 'FLOAT (4 bytes)',
                                 'byte': 'INT (1 byte)',
                                 'integer': 'INT (2 bytes)',
                                 'long': 'INT (4 bytes)',
                                 'boolean': 'BOOL (1 bit)',
                                }, inplace=True)
    # output['direction'].replace({'R': 'Read', 'W': 'Write'}, inplace=True)
    output['ab_type'].replace({'&h40': 'ИНР', '&h1A': 'ДКМ', '&h00': 'ANY', '&h11': 'TIME', '&h12': 'TIME'}, inplace=True)
    return output


def parse_radar_ini(path: str) -> pd.DataFrame:
    config = configparser.ConfigParser(
        comment_prefixes=r'//',
        interpolation=None,
    )
    config.read(path)
    for sct in ('NetBios', 'Selectors', 'Tags'):
        if not config.has_section(sct):
            print(f'Section {sct} is missing in {path}')
            return pd.DataFrame()
    buffers = parse_section_netbios(config['NetBios'])
    selectors = parse_section_selectors(config['Selectors'])
    tags = parse_section_tags(config['Tags'])
    output = gen_output_table(buffers, selectors, tags)
    return output


INP_DIR = 'input'
OUT_DIR = 'output'

# scan input directory for ini-files
with os.scandir(INP_DIR) as it:
    for entry in it:
        if entry.is_file() and entry.name.endswith('.ini'):
            print(entry.name)
            out = parse_radar_ini(entry.path)
            # break
            out_name = os.path.join(OUT_DIR, os.path.splitext(entry.name)[0]+'.csv')
            out.to_csv(out_name, sep=';', index=False, encoding='cp1251')
            # break
