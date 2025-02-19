from collections import defaultdict
import time
import random
import dynet as dy
import numpy as np

# Functions to read in the corpus
w2i = defaultdict(lambda: len(w2i))
t2i = defaultdict(lambda: len(t2i))
UNK = w2i["<unk>"]
def read_dataset(filename):
  with open(filename, "r") as f:
    for line in f:
      tag, words = line.lower().strip().split(" ||| ")
      yield ([w2i[x] for x in words.split(" ")], t2i[tag])

# Read in the data
train = list(read_dataset("../data/classes/train.txt"))
w2i = defaultdict(lambda: UNK, w2i)
dev = list(read_dataset("../data/classes/test.txt"))
nwords = len(w2i)
ntags = len(t2i)

# Start DyNet and define trainer
model = dy.ParameterCollection()
trainer = dy.AdamTrainer(model)

# Define the model
EMB_SIZE = 64
HID_SIZE = 64
HID_LAY = 2
W_emb = model.add_lookup_parameters((nwords, EMB_SIZE)) # Word embeddings
W_h = [model.add_parameters((HID_SIZE, EMB_SIZE if lay == 0 else HID_SIZE)) for lay in range(HID_LAY)]
b_h = [model.add_parameters((HID_SIZE)) for lay in range(HID_LAY)]
W_sm = model.add_parameters((ntags, HID_SIZE))          # Softmax weights
b_sm = model.add_parameters((ntags))                      # Softmax bias

# A function to calculate scores for one value
def calc_scores(words):
  dy.renew_cg()
  h = dy.esum([dy.lookup(W_emb, x) for x in words])
  for W_h_i, b_h_i in zip(W_h, b_h):
    h = dy.tanh( W_h_i * h + b_h_i )
  return W_sm * h + b_sm

for ITER in range(100):
  # Perform training
  random.shuffle(train)
  train_loss = 0.0
  start = time.time()
  for words, tag in train:
    my_loss = dy.pickneglogsoftmax(calc_scores(words), tag)
    train_loss += my_loss.value()
    my_loss.backward()
    trainer.update()
  print("iter %r: train loss/sent=%.4f, time=%.2fs" % (ITER, train_loss/len(train), time.time()-start))
  # Perform training
  test_correct = 0.0
  for words, tag in dev:
    scores = calc_scores(words).npvalue()
    predict = np.argmax(scores)
    if predict == tag:
      test_correct += 1
  print("iter %r: test acc=%.4f" % (ITER, test_correct/len(dev)))
