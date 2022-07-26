import tensorflow as tf
import tensorflow_probability as tfp
import datetime

# Shortcuts
from Models.VAE_1.VAE_1_parameters import *

tfk = tf.keras
tfkl = tf.keras.layers
tfpl = tfp.layers
tfd = tfp.distributions
tfkb = tfk.backend

log_dir = "./Logs/mse" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
tensorboard_callback = tfk.callbacks.TensorBoard(log_dir=log_dir, update_freq='epoch')

physical_devices = tf.config.experimental.list_physical_devices('GPU')
assert len(physical_devices) > 0, "Not enough GPU hardware devices available"
config = tf.config.experimental.set_memory_growth(physical_devices[0], True)


# function for sampling from mu and log_var
def sampling(mu_log_variance):
    mu = mu_log_variance[0]
    log_variance = mu_log_variance[1]
    epsilon = tf.keras.backend.random_normal(shape=(tf.shape(mu)[0], tf.shape(mu)[1]), mean=0.0, stddev=1.0)
    random_sample = mu + tf.keras.backend.exp(log_variance / 2) * epsilon
    return random_sample


# Encoder
encoder_input_layer = tfkl.Input(shape=(138, 138, 1))
enc_conv_layer_1 = tfkl.Conv2D(filters=32, kernel_size=(2, 2), strides=2, activation='relu')(encoder_input_layer)
enc_conv_layer_2 = tfkl.Conv2D(filters=32, kernel_size=2, strides=1, activation='relu')(enc_conv_layer_1)
enc_conv_layer_3 = tfkl.Conv2D(filters=64, kernel_size=2, strides=2, activation='relu')(enc_conv_layer_2)
enc_conv_layer_4 = tfkl.Conv2D(filters=64, kernel_size=2, strides=2, activation='relu')(enc_conv_layer_3)
enc_conv_layer_5 = tfkl.Conv2D(filters=128, kernel_size=2, strides=1, activation='relu')(enc_conv_layer_4)
enc_conv_layer_6 = tfkl.Conv2D(filters=128, kernel_size=2, strides=2, activation='relu')(enc_conv_layer_5)
encoder_flatten_layer = tfkl.Flatten()(enc_conv_layer_6)
encoder_mu_layer = tfkl.Dense(units=latent_dimensions, name="mu_encoder")(encoder_flatten_layer)
encoder_log_variance_layer = tfkl.Dense(units=latent_dimensions, name="log_var_encoder")(encoder_flatten_layer)
encoder_output_layer = tfkl.Lambda(sampling, name="encoder_output")([encoder_mu_layer, encoder_log_variance_layer])

# Build the encoder model
encoder = tf.keras.Model(encoder_input_layer, encoder_output_layer, name="encoder")
encoder.summary()

# Decoder
decoder_input_layer = tfkl.Input(shape=latent_dimensions)
dec_dense_layer = tfkl.Dense(units=8 * 8 * 128, activation=tf.nn.relu)(decoder_input_layer)
dec_reshape_layer = tfkl.Reshape(target_shape=(8, 8, 128))(dec_dense_layer)
dec_convT_layer_1 = \
    tfkl.Conv2DTranspose(filters=32, kernel_size=2, strides=2, padding="same", activation='relu')(dec_reshape_layer)
dec_convT_layer_2 = \
    tfkl.Conv2DTranspose(filters=32, kernel_size=2, strides=1, padding="valid", activation='relu')(dec_convT_layer_1)
dec_convT_layer_3 = \
    tfkl.Conv2DTranspose(filters=64, kernel_size=2, strides=2, padding='same', activation='relu')(dec_convT_layer_2)
dec_convT_layer_4 = \
    tfkl.Conv2DTranspose(filters=64, kernel_size=2, strides=2, padding='same', activation='relu')(dec_convT_layer_3)
dec_convT_layer_5 = \
    tfkl.Conv2DTranspose(filters=128, kernel_size=2, strides=1, padding='valid', activation='relu')(dec_convT_layer_4)
dec_convT_layer_6 = \
    tfkl.Conv2DTranspose(filters=128, kernel_size=2, strides=2, padding='same', activation='relu')(dec_convT_layer_5)
dec_convT_layer_7 = \
    tfkl.Conv2DTranspose(filters=1, kernel_size=2, strides=1, padding='same', activation='relu')(dec_convT_layer_6)

# Build the decoder model
decoder = tf.keras.Model(decoder_input_layer, dec_convT_layer_7, name="decoder")
decoder.summary()


# Build VAE
VAE_input = tfkl.Input((138, 138, 1))
VAE_enc_output = encoder(VAE_input)

VAE = tfk.Model(VAE_input, decoder(VAE_enc_output))

VAE.summary()


def loss_func(encoder_mu, encoder_log_variance):

    def vae_reconstruction_loss(y_true, y_predict):
        reconstruction_loss_factor = 1000
        reconstruction_loss = tfkb.mean(tfkb.square(y_true-y_predict), axis=[1, 2, 3])
        return reconstruction_loss_factor * reconstruction_loss

    def vae_kl_loss(encoder_mu, encoder_log_variance):
        kl_loss = -0.5 * tfkb.sum(1.0 + encoder_log_variance - tfkb.square(encoder_mu) - tfkb.exp(encoder_log_variance),
                                  axis=1)
        return kl_loss

    def vae_loss(y_true, y_predict):
        reconstruction_loss = vae_reconstruction_loss(y_true, y_predict)
        kl_loss = vae_kl_loss(y_true, y_predict)
        loss = reconstruction_loss + 5*kl_loss
        return loss

    return vae_loss


# Compile model
VAE.compile(optimizer=tfk.optimizers.Adam(learning_rate=learning_rate),
            loss=loss_func(encoder_mu_layer, encoder_log_variance_layer))


early_stopping_kfold = tfk.callbacks.EarlyStopping(monitor="val_loss",
                                                   patience=20,
                                                   verbose=2)
early_stopping_training_db = tfk.callbacks.EarlyStopping(monitor="loss",
                                                         patience=20,
                                                         verbose=2,
                                                         restore_best_weights=True)