from gensim.models import Word2Vec
from gensim.models import KeyedVectors
import logging
import sys

sys.path.append('../../')
from utils import MyCorpus


class ModelConfig(object):
    def __init__(self):
        self.vector_size = 200
        self.window = 5
        self.min_count = 10
        self.sg = 0  # 1 for skip-gram; else CBOW.
        self.hs = 0  # 1 for hierarchical softmax
        self.negative = 5  # the int for negative specifies how many "noise words" should be drawn (usually between 5-20).
        self.cbow_mean = 1  # If 0, use the sum of the context word vectors. If 1, use the mean, only applies when cbow is used.
        self.epochs = 1
        self.model_save_path = 'word2vec.model'
        self.model_save_path_bin = 'word2vec.bin'

        logging.info("### 将当前配置打印到日志文件中 ")
        for key, value in self.__dict__.items():
            logging.info(f"### {key} = {value}")


def train(config, update=False):
    sentences = MyCorpus()
    if not update:
        model = Word2Vec(sentences=sentences, vector_size=config.vector_size, window=config.window,
                         min_count=config.min_count, sg=config.sg, hs=config.hs,
                         negative=config.negative, cbow_mean=config.cbow_mean, epochs=config.epochs)
    else:
        model = Word2Vec.load(config.model_save_path)
        model.build_vocab(sentences=sentences, update=update)
        model.train(sentences, total_examples=model.corpus_count,epochs=config.epochs)
    model.save(config.model_save_path)
    model.wv.save_word2vec_format(config.model_save_path_bin, binary=True)


def load_sougonews_wv(config):
    model = KeyedVectors.load_word2vec_format(config.model_save_path_bin, binary=True)
    logging.info(f"中国: \n{model['中国']}")


if __name__ == '__main__':
    config = ModelConfig()
    # train(config)
    load_sougonews_wv(config)
