from __future__ import print_function
import time

from collections import defaultdict
import random
import math
import sys
import argparse

import dynet as dy
import numpy as np
import pdb

#much of the beginning is the same as the text retrieval
# format of files: each line is "word1 word2 ..." aligned line-by-line
train_src_file = "../data/parallel/train.ja"
train_trg_file = "../data/parallel/train.en"
dev_src_file = "../data/parallel/dev.ja"
dev_trg_file = "../data/parallel/dev.en"
test_src_file = "../data/parallel/test.ja"
test_trg_file = "../data/parallel/test.en"


w2i_src = defaultdict(lambda: len(w2i_src))
w2i_trg = defaultdict(lambda: len(w2i_trg))

def read(fname_src, fname_trg):
    """
    Read parallel files where each line lines up
    """
    with open(fname_src, "r") as f_src, open(fname_trg, "r") as f_trg:
        for line_src, line_trg in zip(f_src, f_trg):
            #need to append EOS tags to at least the target sentence
            sent_src = [w2i_src[x] for x in line_src.strip().split() + ['</s>']] 
            sent_trg = [w2i_trg[x] for x in ['<s>'] + line_trg.strip().split() + ['</s>']] 
            yield (sent_src, sent_trg)

# Read the data
train = list(read(train_src_file, train_trg_file))
unk_src = w2i_src["<unk>"]
eos_src = w2i_src['</s>']
w2i_src = defaultdict(lambda: unk_src, w2i_src)
unk_trg = w2i_trg["<unk>"]
eos_trg = w2i_trg['</s>']
sos_trg = w2i_trg['<s>']
w2i_trg = defaultdict(lambda: unk_trg, w2i_trg)
i2w_trg = {v: k for k, v in w2i_trg.items()}

nwords_src = len(w2i_src)
nwords_trg = len(w2i_trg)
dev = list(read(dev_src_file, dev_trg_file))
test = list(read(test_src_file, test_trg_file))
# DyNet Starts
model = dy.Model()
trainer = dy.AdamTrainer(model)

# Model parameters
EMBED_SIZE = 64
HIDDEN_SIZE = 128
BATCH_SIZE = 16

#Especially in early training, the model can generate basically infinitly without generating an EOS
#have a max sent size that you end at
MAX_SENT_SIZE = 50

# Lookup parameters for word embeddings
LOOKUP_SRC = model.add_lookup_parameters((nwords_src, EMBED_SIZE))
LOOKUP_TRG = model.add_lookup_parameters((nwords_trg, EMBED_SIZE))

# Word-level LSTMs
LSTM_SRC_BUILDER = dy.LSTMBuilder(1, EMBED_SIZE, HIDDEN_SIZE, model)
LSTM_TRG_BUILDER = dy.LSTMBuilder(1, EMBED_SIZE, HIDDEN_SIZE, model)

#the softmax from the hidden size 
W_sm_p = model.add_parameters((nwords_trg, HIDDEN_SIZE))         # Weights of the softmax
b_sm_p = model.add_parameters((nwords_trg))                   # Softmax bias

def calc_loss(sent):
    dy.renew_cg()

    # Transduce all batch elements with an LSTM
    src = sent[0]
    trg = sent[1]


    #initialize the LSTM
    init_state_src = LSTM_SRC_BUILDER.initial_state()

    #get the output of the first LSTM
    src_output = init_state_src.add_inputs([LOOKUP_SRC[x] for x in src])[-1].output()
    #now step through the output sentence
    all_losses = []

    current_state = LSTM_TRG_BUILDER.initial_state().set_s([src_output, dy.tanh(src_output)])
    prev_word = trg[0]
    W_sm = dy.parameter(W_sm_p)
    b_sm = dy.parameter(b_sm_p)

    for next_word in trg[1:]:
        #feed the current state into the 
        current_state = current_state.add_input(LOOKUP_TRG[prev_word])
        output_embedding = current_state.output()

        s = dy.affine_transform([b_sm, W_sm, output_embedding])
        all_losses.append(dy.pickneglogsoftmax(s, next_word))

        prev_word = next_word
    return dy.esum(all_losses)

def generate(sent):
    dy.renew_cg()

    src = sent


    #initialize the LSTM
    init_state_src = LSTM_SRC_BUILDER.initial_state()

    #get the output of the first LSTM
    src_output = init_state_src.add_inputs([LOOKUP_SRC[x] for x in src])[-1].output()

    #generate until a eos tag or max is reached
    current_state = LSTM_TRG_BUILDER.initial_state().set_s([src_output, dy.tanh(src_output)])

    prev_word = sos_trg
    trg_sent = []
    W_sm = dy.parameter(W_sm_p)
    b_sm = dy.parameter(b_sm_p)

    for i in range(MAX_SENT_SIZE):
        #feed the previous word into the lstm, calculate the most likely word, add it to the sentence
        current_state = current_state.add_input(LOOKUP_TRG[prev_word])
        output_embedding = current_state.output()
        s = dy.affine_transform([b_sm, W_sm, output_embedding])
        probs = (-dy.log_softmax(s)).value()
        next_word = np.argmax(probs)

        if next_word == eos_trg:
            break
        prev_word = next_word
        trg_sent.append(i2w_trg[next_word])
    return trg_sent

for ITER in range(100):
  # Perform training
  random.shuffle(train)
  train_words, train_loss = 0, 0.0
  start = time.time()
  for sent_id, sent in enumerate(train):
    my_loss = calc_loss(sent)
    train_loss += my_loss.value()
    train_words += len(sent)
    my_loss.backward()
    trainer.update()
    if (sent_id+1) % 1000 == 0:
      print("--finished %r sentences" % (sent_id+1))
  print("iter %r: train loss/word=%.4f, ppl=%.4f, time=%.2fs" % (ITER, train_loss/train_words, math.exp(train_loss/train_words), time.time()-start))
  # Evaluate on dev set
  dev_words, dev_loss = 0, 0.0
  start = time.time()
  for sent_id, sent in enumerate(dev):
    my_loss = calc_loss(sent)
    dev_loss += my_loss.value()
    dev_words += len(sent)
    trainer.update()
  print("iter %r: dev loss/word=%.4f, ppl=%.4f, time=%.2fs" % (ITER, dev_loss/dev_words, math.exp(dev_loss/dev_words), time.time()-start))

#this is how you generate, can replace with desired sentenced to generate  
sentences = []
for sent_id, sent in enumerate(test):
    translated_sent = generate(sent[0])
    sentences.append(translated_sent)
for sent in sentences:
    print(sent)
