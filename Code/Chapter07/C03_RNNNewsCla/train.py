"""
文件名: Code/Chapter07/C03_RNNNewsCla/train.py
创建时间: 2023/5/7 11:03 下午
作 者: @空字符
公众号: @月来客栈
知 乎: @月来客栈 https://www.zhihu.com/people/the_lastest
"""

from transformers import optimization
from torch.utils.tensorboard import SummaryWriter
import torch
from copy import deepcopy
import sys
import logging
import os
from NewsRNN import NewsRNN

sys.path.append("../../")
from utils import TouTiaoNews
from utils import logger_init

class ModelConfig(object):
    def __init__(self):
        self.batch_size = 128
        self.epochs = 50
        self.learning_rate = 6e-6
        self.num_classes = 15
        self.num_layers = 2
        self.top_k = 3000
        self.hidden_size = 512
        self.clip_max_norm = 0.02
        self.num_warmup_steps = 100
        self.model_save_path = 'model.pt'
        self.summary_writer_dir = "runs/model"
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        logger_init(log_file_name='log', log_level=logging.INFO, log_dir='log')
        # 判断是否存在GPU设备，其中0表示指定第0块设备
        logging.info("### 将当前配置打印到日志文件中 ")
        for key, value in self.__dict__.items():
            logging.info(f"### {key} = {value}")


def train(config):
    toutiao_news = TouTiaoNews(top_k=config.top_k,
                               batch_size=config.batch_size)
    train_iter, val_iter = toutiao_news.load_train_val_test_data(is_train=True)
    model = NewsRNN(config.top_k, config.hidden_size,
                    config.num_layers, config.num_classes)
    if os.path.exists(config.model_save_path):
        logging.info(f" # 载入模型{config.model_save_path}进行追加训练...")
        checkpoint = torch.load(config.model_save_path)
        model.load_state_dict(checkpoint)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    writer = SummaryWriter(config.summary_writer_dir)
    model = model.to(config.device)
    max_test_acc = 0
    global_steps = 0
    steps = len(train_iter) * config.epochs
    scheduler = optimization.get_cosine_schedule_with_warmup(optimizer, num_warmup_steps=config.num_warmup_steps,
                                                             num_training_steps=steps, num_cycles=2)
    for epoch in range(config.epochs):
        for i, (x, y) in enumerate(train_iter):
            x, y = x.to(config.device), y.to(config.device)
            loss, logits = model(x, y)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.clip_max_norm)
            optimizer.step()  # 执行梯度下降
            scheduler.step()
            global_steps += 1
            if i % 50 == 0:
                acc = (logits.argmax(1) == y).float().mean()
                logging.info(f"Epochs[{epoch + 1}/{config.epochs}]--batch[{i}/{len(train_iter)}]"
                             f"--Acc: {round(acc.item(), 4)}--loss: {round(loss.item(), 4)}")
                writer.add_scalar('Training/Accuracy', acc, global_steps)
            writer.add_scalar('Training/Loss', loss.item(), global_steps)
        test_acc = evaluate(val_iter, model, config.device)
        logging.info(f"Epochs[{epoch + 1}/{config.epochs}]--Acc on val {test_acc}")
        writer.add_scalar('Testing/Accuracy', test_acc, global_steps)
        if test_acc > max_test_acc:
            max_test_acc = test_acc
            state_dict = deepcopy(model.state_dict())
            torch.save(state_dict, config.model_save_path)


def evaluate(data_iter, model, device):
    model.eval()
    with torch.no_grad():
        acc_sum, n = 0.0, 0
        for x, y in data_iter:
            x, y = x.to(device), y.to(device)
            logits = model(x)
            acc_sum += (logits.argmax(1) == y).float().sum().item()
            n += len(y)
        model.train()
        return acc_sum / n


def inference(config, test_iter):
    model = NewsRNN(config.input_size, config.hidden_size,
                    config.num_layers, config.num_classes)
    model.to(config.device)
    model.eval()
    if os.path.exists(config.model_save_path):
        logging.info(f" # 载入模型进行推理……")
        checkpoint = torch.load(config.model_save_path)
        model.load_state_dict(checkpoint)
    else:
        raise ValueError(f" # 模型{config.model_save_path}不存在！")
    first_batch = next(iter(test_iter))
    with torch.no_grad():
        logits = model(first_batch[0].to(config.device))
    y_pred = logits.argmax(1)
    logging.info(f"真实标签为：{first_batch[1]}")
    logging.info(f"预测标签为：{y_pred}")


if __name__ == '__main__':
    config = ModelConfig()
    train(config)

    #   推理
    # toutiao_news = TouTiaoNews(top_k=config.top_k,
    #                            batch_size=config.batch_size)
    # test_iter = toutiao_news.load_train_val_test_data(is_train=False)
    # inference(config, test_iter)
