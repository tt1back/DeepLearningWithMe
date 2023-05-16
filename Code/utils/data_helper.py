"""
文件名: Code/utils/data_helper.py
创建时间: 2023/5/6 8:07 下午
作 者: @空字符
公众号: @月来客栈
知 乎: @月来客栈 https://www.zhihu.com/people/the_lastest
"""
import json
import os
from collections import Counter
import torch
from tqdm import tqdm
from torch.utils.data import DataLoader
import logging
import opencc

PROJECT_HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_HOME = os.path.join(PROJECT_HOME, 'data')


class Vocab(object):
    """
    构建词表
    vocab = Vocab()
    print(vocab.itos)  # 得到一个列表，返回词表中的每一个词；
    print(vocab.itos[num])  # 通过索引返回得到词表中对应的词；
    print(vocab.stoi)  # 得到一个字典，返回词表中每个词的索引；
    print(vocab.stoi['[UNK]'])  # 通过单词返回得到词表中对应的索引
    print(len(vocab))  # 返回词表长度
    :param top_k:  取出现频率最高的前top_k个token
    :param data: 为一个列表，每个元素为一句文本
    :return:
    """
    UNK = '[UNK]'  # 0
    PAD = '[PAD]'  # 1

    def __init__(self, top_k=2000, data=None):
        logging.info(f" ## 正在根据训练集构建词表……")
        counter = Counter()
        self.stoi = {Vocab.UNK: 0, Vocab.PAD: 1}
        self.itos = [Vocab.UNK, Vocab.PAD]
        for text in data:
            token = tokenize(text)
            # ['上', '联', '：', '一', '夜', '春', '风', '去', '，', '怎', '么', '对', '下', '联', '？']
            counter.update(token)  # 统计每个token出现的频率
        top_k_words = counter.most_common(top_k - 2)  # 取前top_k - 2 个，加上UNK和PAD，一共top_k个
        for i, word in enumerate(top_k_words):
            self.stoi[word[0]] = i + 2  # 2表示已有了UNK和PAD
            self.itos.append(word[0])
        logging.debug(f" ## 词表构建完毕，前100个词为: {list(self.stoi.items())[:100]}")

    def __getitem__(self, token):
        return self.stoi.get(token, self.stoi.get(Vocab.UNK))

    def __len__(self):
        return len(self.itos)


def tokenize(text):
    """
    tokenize方法
    :param text: 上联：一夜春风去，怎么对下联？
    :return:
    words: 字粒度： ['上', '联', '：', '一', '夜', '春', '风', '去', '，', '怎', '么', '对', '下', '联', '？']
    """
    words = " ".join(text).split()  # 字粒度

    # TODO:  后续这里需要添加词粒度的tokenize方法
    return words


def pad_sequence(sequences, batch_first=False, max_len=None, padding_value=0):
    """
    对一个List中的元素进行padding
    Pad a list of variable length Tensors with ``padding_value``
    a = torch.ones(25)
    b = torch.ones(22)
    c = torch.ones(15)
    pad_sequence([a, b, c],max_len=None).size()
    torch.Size([25, 3])
        sequences:
        batch_first: 是否把batch_size放到第一个维度
        padding_value:
        max_len :
                当max_len = 50时，表示以某个固定长度对样本进行padding，多余的截掉；
                当max_len=None是，表示以当前batch中最长样本的长度对其它进行padding；
    Returns:
    """
    if max_len is None:
        max_len = max([s.size(0) for s in sequences])
    out_tensors = []
    for tensor in sequences:
        if tensor.size(0) < max_len:
            padding_content = [padding_value] * (max_len - tensor.size(0))
            tensor = torch.cat([tensor, torch.tensor(padding_content)], dim=0)
        else:
            tensor = tensor[:max_len]
        out_tensors.append(tensor)
    out_tensors = torch.stack(out_tensors, dim=1)
    if batch_first:
        return out_tensors.transpose(0, 1)
    return out_tensors


class TouTiaoNews(object):
    """
    头条新闻标题数据集，一共15个类别:
    ['故事','文化','娱乐','体育','财经','房产','汽车','教育','科技','军事','旅游','国际','股票','三农','游戏']
    训练集:验证集:测试集 267881:76537:8270
    """
    DATA_DIR = os.path.join(DATA_HOME, 'toutiao')
    FILE_PATH = [os.path.join(DATA_DIR, 'toutiao_train.txt'),
                 os.path.join(DATA_DIR, 'toutiao_val.txt'),
                 os.path.join(DATA_DIR, 'toutiao_test.txt')]

    def __init__(self, top_k=2000,
                 max_sen_len=None,
                 batch_size=4,
                 is_sample_shuffle=True):
        self.top_k = top_k
        raw_data_train, _ = self.load_raw_data(self.FILE_PATH[0])
        self.vocab = Vocab(top_k=self.top_k, data=raw_data_train)
        self.max_sen_len = max_sen_len
        self.batch_size = batch_size
        self.is_sample_shuffle = is_sample_shuffle

    @staticmethod
    def load_raw_data(file_path=None):
        """
        载入原始的文本
        :param file_path:
        :return:
        samples: ['上联：一夜春风去，怎么对下联？', '隋唐五代｜欧阳询《温彦博碑》，书于贞观十一年，是欧最晚的作品']
        labels: ['1','1']
        """
        logging.info(f" ## 载入原始文本 {file_path.split(os.path.sep)[-1]}")
        samples, labels = [], []
        with open(file_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip('\n').split('_!_')
                samples.append(line[0])
                labels.append(line[1])
        return samples, labels

    def data_process(self, file_path):
        samples, labels = self.load_raw_data(file_path)
        data = []
        logging.info(f" ## 处理原始文本 {file_path.split(os.path.sep)[-1]}")
        for i in tqdm(range(len(samples)), ncols=80):
            logging.debug(f" ## 原始输入样本为: {samples[i]}")
            tokens = tokenize(samples[i])
            logging.debug(f" ## 分割后的样本为: {tokens}")
            token_ids = [self.vocab[token] for token in tokens]
            logging.debug(f" ## 向量化后样本为: {token_ids}\n")
            token_ids_tensor = torch.tensor(token_ids, dtype=torch.long)
            l = torch.tensor(int(labels[i]), dtype=torch.long)
            data.append((token_ids_tensor, l))
        return data

    def generate_batch(self, data_batch):
        """
        以小批量为单位对序列进行padding
        :param data_batch:
        :return:
        """
        batch_sentence, batch_label = [], []
        for (sen, label) in data_batch:  # 开始对一个batch中的每一个样本进行处理。
            batch_sentence.append(sen)
            batch_label.append(label)
        batch_sentence = pad_sequence(batch_sentence,  # [batch_size,max_len]
                                      padding_value=self.vocab.stoi[self.vocab.PAD],
                                      batch_first=True,
                                      max_len=self.max_sen_len)
        batch_label = torch.tensor(batch_label, dtype=torch.long)
        return batch_sentence, batch_label

    def load_train_val_test_data(self, is_train=False):
        if not is_train:
            test_data = self.data_process(self.FILE_PATH[2])
            test_iter = DataLoader(test_data, batch_size=self.batch_size,
                                   shuffle=False, collate_fn=self.generate_batch)
            logging.info(f" ## 测试集构建完毕，一共{len(test_data)}个样本")
            return test_iter
        train_data = self.data_process(self.FILE_PATH[0])  # 得到处理好的所有样本
        val_data = self.data_process(self.FILE_PATH[1])
        train_iter = DataLoader(train_data, batch_size=self.batch_size,  # 构造DataLoader
                                shuffle=self.is_sample_shuffle,
                                collate_fn=self.generate_batch)
        val_iter = DataLoader(val_data, batch_size=self.batch_size,
                              shuffle=False, collate_fn=self.generate_batch)
        logging.info(f" ## 训练集和验证集构建完毕，样本数量为{len(train_data)}:{len(val_data)}")
        return train_iter, val_iter


class TangShi(TouTiaoNews):
    """
    全唐诗数据集：
    感谢此仓库收集与整理 https://github.com/chinese-poetry/chinese-poetry
    此处使用的是全唐诗数据，即poet.tang.0.json~poet.tang.57000.json，58个json文件，一共约5.7万首

    """
    DATA_DIR = os.path.join(DATA_HOME, 'peotry_tang')
    FILE_PATH = [os.path.join(DATA_DIR, 'poet.tang.0-40.json'),  # 0~40000 for train 样本数量为: 20521
                 os.path.join(DATA_DIR, 'poet.tang.41-52.json'),  # 41000~52000 for val 样本数量为: 4355
                 os.path.join(DATA_DIR, 'poet.tang.53-57.json')]  # 53000~57000 for test 样本数量为: 762

    def __init__(self, *args, **kwargs):
        super(TangShi, self).__init__(*args, **kwargs)

    def load_raw_data(self, file_path=None):

        def read_json_data(file_path):
            logging.info(f" ## 载入原始文本 {file_path.split(os.path.sep)[-1]}")
            print(f" ## 载入原始文本 {file_path.split(os.path.sep)[-1]}")
            samples, labels = [], []
            with open(file_path, encoding='utf-8') as f:
                data = json.loads(f.read())
                # [{'author': '范成大', 'paragraphs': ['日滿東窗照被堆，宿湯猶自暖如煨。', '尺三汗脚君休笑，曾踏鞾霜待漏來。'], 'title': '戲贈脚婆',...},
                # {'author': '范成大', 'paragraphs': ['雪不成花夜雨來，壠頭一洗定無埃。', '小童却怕溪橋滑，明日先生合探梅。'], 'title': '除夜前二日夜雨', ...},
                for item in data:
                    content = item['paragraphs']  # ['日滿東窗照被堆，宿湯猶自暖如煨。', '尺三汗脚君休笑，曾踏鞾霜待漏來。']
                    content = "".join(content)  # '日滿東窗照被堆，宿湯猶自暖如煨。尺三汗脚君休笑，曾踏鞾霜待漏來。'
                    if not skip(content):
                        samples.append(content)  # ['','日滿東窗照被堆，宿湯猶自暖如煨。', '尺三汗脚君休笑，曾踏鞾霜待漏來。']
                        labels.append(content[1:] + content[-1])  # ['','滿東窗照被堆，宿湯猶自暖如煨。尺三汗脚君休笑，曾踏鞾霜待漏來。。']
            return samples, labels

        def skip(content):
            """
            过滤掉不需要的诗
            :param content:
            :return:
            """
            if len(content) % 12 != 0 and len(content) % 14 != 0:  # 五言 或 七言
                return True
            if '《' in content or '（' in content or len(content) < 12 or '□' in content \
                    or len(content) > 100:  # 太长的诗过略
                return True
            return False

        file_name = file_path.split(os.path.sep)[-1]
        start, end = file_name.split('.')[2].split('-')
        all_samples, all_labels = [], []
        for i in range(int(start), int(end) + 1):
            file_path = os.path.join(self.DATA_DIR, f'poet.tang.{i * 1000}.json')
            samples, labels = read_json_data(file_path)
            all_samples += samples
            all_labels += labels
        logging.info(f" ## {file_name} 样本数量为: {len(all_samples)}")
        return all_samples, all_labels

    def data_process(self, file_path):
        samples, labels = self.load_raw_data(file_path)
        data = []
        logging.info(f" ## 处理原始文本 {file_path.split(os.path.sep)[-1]}")
        for i in tqdm(range(len(samples)), ncols=80):
            logging.debug(f" ## 原始样本为:\n ")
            logging.debug(f" ## 输入为: {samples[i]}")
            x_tokens = tokenize(samples[i])
            logging.debug(f" ## 分割后为: {x_tokens}")
            x_token_ids = [self.vocab[token] for token in x_tokens]
            logging.debug(f" ## 向量化后为: {x_token_ids}\n")

            logging.debug(f" ## 标签为: {labels[i]}")
            y_tokens = tokenize(labels[i])
            logging.debug(f" ## 分割后为: {y_tokens}")
            y_token_ids = [self.vocab[token] for token in y_tokens]
            logging.debug(f" ## 向量化后为: {y_token_ids}\n")

            x_token_ids_tensor = torch.tensor(x_token_ids, dtype=torch.long)
            y_token_ids_tensor = torch.tensor(y_token_ids, dtype=torch.long)
            data.append((x_token_ids_tensor, y_token_ids_tensor))
        return data

    def generate_batch(self, data_batch):
        """
        以小批量为单位对序列进行padding
        :param data_batch:
        :return:
        """
        batch_sentence, batch_label = [], []
        for (sen, label) in data_batch:  # 开始对一个batch中的每一个样本进行处理。
            batch_sentence.append(sen)
            batch_label.append(label)
        x_batch_sentence = pad_sequence(batch_sentence,  # [batch_size,max_len]
                                        padding_value=self.vocab.stoi[self.vocab.PAD],
                                        batch_first=True,
                                        max_len=self.max_sen_len)
        y_batch_sentence = pad_sequence(batch_label,  # [batch_size,max_len]
                                        padding_value=self.vocab.stoi[self.vocab.PAD],
                                        batch_first=True,
                                        max_len=self.max_sen_len)
        return x_batch_sentence, y_batch_sentence

    @staticmethod
    def simplified_traditional_convert(text, type='s2t'):
        """
        繁简体相互转换
        :param text:
        :param type: t2s 繁体转简体， s2t简体转繁体
        :return:
        """
        if type not in ['t2s', 's2t']:
            raise ValueError(" ## 转换类型必须为 't2s' or 's2t'")
        converter = opencc.OpenCC(type + ".json")  # 使用t2s.json配置文件进行繁->简转换
        converted_text = converter.convert(text)
        return converted_text

    def make_infer_sample(self, srcs):
        """

        :param srcs: ["李白乘舟将欲行","朝辞白帝彩"]
        :return:
        """
        all_token_ids = []
        logging.info(f" ## 构造推理样本")
        for src in srcs:
            text = self.simplified_traditional_convert(src, 's2t')
            tokens = tokenize(text)
            logging.debug(f" ## 分割后为: {tokens}")
            token_ids = [self.vocab[token] for token in tokens]
            logging.info(f" ## 向量化后为: {token_ids}")
            all_token_ids.append(torch.tensor(token_ids, dtype=torch.long))
        return all_token_ids


if __name__ == '__main__':
    t = TangShi()
    test_iter = t.load_train_val_test_data(is_train=True)
    # print(t.vocab.itos)
    # for x, y in test_iter:
    #     print(x.shape)
    #     print(y.shape)
    # srcs = ["李白乘舟将欲行", "朝辞白帝彩"]
    # infer_samples = t.make_infer_sample(srcs)
    # print(infer_samples)
