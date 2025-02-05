"""
文件名: Code/Chapter09/C02_Gensim/train.py
创建时间: 2023/7/13 19:52
作 者: @空字符
公众号: @月来客栈
知 乎: @月来客栈 https://www.zhihu.com/people/the_lastest
"""

from gensim.models import Word2Vec
from gensim.models import KeyedVectors
import logging
import sys

sys.path.append('../../')
from utils import MyCorpus
from utils import logger_init


class ModelConfig(object):
    def __init__(self):
        self.vector_size = 200
        self.window = 5
        self.min_count = 10
        self.sg = 0  # 1 for skip-gram; else CBOW.
        self.hs = 0  # 1 for hierarchical softmax
        self.negative = 5  # the int for negative specifies how many "noise words" should be drawn (usually between 5-20).
        self.cbow_mean = 1  # If 0, use the sum of the context word vectors. If 1, use the mean, only applies when cbow is used.
        self.epochs = 3
        self.model_save_path = 'word2vec.model'
        self.model_save_path_bin = 'word2vec.bin'
        logger_init(log_file_name='log', log_level=logging.INFO, log_dir='log')
        logging.info("### 将当前配置打印到日志文件中 ")
        for key, value in self.__dict__.items():
            logging.info(f"### {key} = {value}")


def train(config, update=False):
    sentences = MyCorpus()
    if not update:
        logging.info(f" \n## 模型开始训练\n")
        model = Word2Vec(sentences=sentences, vector_size=config.vector_size, window=config.window,
                         min_count=config.min_count, sg=config.sg, hs=config.hs,
                         negative=config.negative, cbow_mean=config.cbow_mean, epochs=config.epochs)
    else:
        logging.info(f" \n ## 模型开始进行增量训练\n")
        model = Word2Vec.load(config.model_save_path)
        model.build_vocab(sentences, update=update)
        model.train(sentences, total_examples=model.corpus_count,epochs=config.epochs)
    model.save(config.model_save_path)
    model.wv.save_word2vec_format(config.model_save_path_bin, binary=True)


def load_sougonews_wv(config):
    model = KeyedVectors.load_word2vec_format(config.model_save_path_bin, binary=True)
    logging.info(f"中国: \n{model['中国']}")
    sim_words = model.most_similar(['上海市'], topn=5)
    logging.info(f"与上海市最相似的前5个词为:{sim_words}")
    # [('北京', 0.87215), ('广州', 0.83759), ('深圳',0.81829), ('文广', 0.75451), ('南京', 0.75278)]


if __name__ == '__main__':
    config = ModelConfig()
    train(config)
    load_sougonews_wv(config)
