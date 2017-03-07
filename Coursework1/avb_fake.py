import matplotlib
matplotlib.use('Agg')
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os
from tensorflow.examples.tutorials.mnist import input_data


mnist = input_data.read_data_sets('./MNIST_data', one_hot=True)
mb_size = 32
z_dim = 256
eps_dim = 32
X_dim = mnist.train.images.shape[1]
y_dim = mnist.train.labels.shape[1]
h_dim = 128
c = 0
lr = 1e-3


def plot(samples):
    fig = plt.figure(figsize=(4, 4))
    gs = gridspec.GridSpec(4, 4)
    gs.update(wspace=0.05, hspace=0.05)

    for i, sample in enumerate(samples):
        ax = plt.subplot(gs[i])
        plt.axis('off')
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.set_aspect('equal')
        plt.imshow(sample.reshape(28, 28), cmap='Greys_r')

    return fig


def xavier_init(size):
    in_dim = size[0]
    xavier_stddev = 1. / tf.sqrt(in_dim / 2.)
    return tf.random_normal(shape=size, stddev=xavier_stddev)


""" Q(z|X,eps) """
X = tf.placeholder(tf.float32, shape=[None, X_dim])
X_eps = tf.placeholder(tf.float32, shape=[None, z_dim], name='X_eps')
eps = tf.placeholder(tf.float32, shape=[None, eps_dim])

Q_W1 = tf.Variable(xavier_init([X_dim + eps_dim, h_dim]))
Q_b1 = tf.Variable(tf.zeros(shape=[h_dim]))

Q_W2 = tf.Variable(xavier_init([h_dim, z_dim]))
Q_b2 = tf.Variable(tf.zeros(shape=[z_dim]))

theta_Q = [Q_W1, Q_W2, Q_b1, Q_b2]


def Q(X, eps):
    inputs = tf.concat([X, eps], 1)
    h = tf.nn.elu(tf.matmul(inputs, Q_W1) + Q_b1)
    z = tf.matmul(h, Q_W2) + Q_b2
    return z


""" P(X|z) """
P_W1 = tf.Variable(xavier_init([z_dim, h_dim]))
P_b1 = tf.Variable(tf.zeros(shape=[h_dim]))

P_W2 = tf.Variable(xavier_init([h_dim, X_dim]))
P_b2 = tf.Variable(tf.zeros(shape=[X_dim]))

theta_P = [P_W1, P_W2, P_b1, P_b2]


def P(z):
    h = tf.nn.elu(tf.matmul(z, P_W1) + P_b1)
    logits = tf.matmul(h, P_W2) + P_b2
    prob = tf.nn.sigmoid(logits)
    return prob, logits


""" D(z) """
D_W1 = tf.Variable(xavier_init([z_dim, h_dim]))
D_b1 = tf.Variable(tf.zeros(shape=[h_dim]))

D_W2 = tf.Variable(xavier_init([h_dim, 1]))
D_b2 = tf.Variable(tf.zeros(shape=[1]))

theta_D = [D_W1, D_W2, D_b1, D_b2]

def D(z):
    h = tf.nn.elu(tf.matmul(z, D_W1) + D_b1)
    logits = tf.matmul(h, D_W2) + D_b2
    return logits

### TRAINING
z_sample = Q(X, eps)
recon, logits = P(z_sample)

# Sample from random z
X_samples, _ = P(X_eps)

# E[log P(X|z)]
recon_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=logits,labels=X))

# Adversarial loss to approx. Q(z|X)
D_real = D(X_eps)
D_fake = D(z_sample)

D_loss = tf.reduce_mean(
    tf.nn.sigmoid_cross_entropy_with_logits(logits=D_real, labels=tf.ones_like(D_real)) +
    tf.nn.sigmoid_cross_entropy_with_logits(logits=D_fake, labels=tf.zeros_like(D_fake)))
G_loss = -tf.reduce_mean(tf.log(D_fake))

AE_solver = tf.train.AdamOptimizer().minimize(recon_loss, var_list=theta_P + theta_Q)
D_solver = tf.train.AdamOptimizer().minimize(D_loss, var_list=theta_D)
G_solver = tf.train.AdamOptimizer().minimize(G_loss, var_list=theta_Q)

sess = tf.Session()
sess.run(tf.initialize_all_variables())


sess = tf.Session()
sess.run(tf.global_variables_initializer())

if not os.path.exists('out/'):
    os.makedirs('out/')

i = 0

for it in range(1000000):
    X_mb, _ = mnist.train.next_batch(mb_size)
    eps_mb = np.random.randn(mb_size, eps_dim)
    z_mb = np.random.randn(mb_size, z_dim)

    _, recon_loss_curr = sess.run([AE_solver, recon_loss],
                                  feed_dict={X: X_mb, eps: eps_mb})
    _, g_loss_curr = sess.run([G_solver, G_loss],
                                  feed_dict={X: X_mb, eps: eps_mb})
    _, D_loss_curr = sess.run([D_solver, D_loss],
                              feed_dict={X: X_mb, eps: eps_mb, X_eps: z_mb})

    if it % 500 == 0:
        print('Iter: {}; G_loss: {:.4}; D_loss: {:.4}, Recon_loss: {:.4}'
              .format(it, g_loss_curr, D_loss_curr, recon_loss_curr))

        eps_mb = np.random.randn(16, eps_dim)
        X_mb, _ = mnist.train.next_batch(4)

        samples = sess.run(X_samples, feed_dict={X_eps: np.random.randn(16, z_dim), eps: eps_mb})

        fig = plot(samples)
        plt.savefig('out/{}.png'.format(str(i).zfill(3)), bbox_inches='tight')
        plt.close(fig)

        eps_mb = np.random.randn(4, eps_dim)
        X_mb, _ = mnist.train.next_batch(4)

        reconstructed, latent_rep = sess.run([recon, z_sample], feed_dict={X: X_mb, eps: eps_mb})
        n_examples = 4
        fig, axs = plt.subplots(3, n_examples, figsize=(4, 3))
        for example_i in range(n_examples):
            axs[0][example_i].imshow(
                np.reshape(X_mb[example_i, :], (28, 28)))
            axs[1][example_i].imshow(
                np.reshape(latent_rep[example_i, :], (16, 16)))
            axs[2][example_i].imshow(
                np.reshape([reconstructed[example_i, :]], (28, 28)))
        plt.savefig('out2/{}.png'.format(str(i).zfill(3)), bbox_inches='tight')
        plt.close(fig)
        i += 1