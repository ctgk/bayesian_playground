import io
from itertools import product

from matplotlib.backends.backend_agg import RendererAgg
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import streamlit as st
from streamlit_drawable_canvas import st_canvas

import bayesian as bs


WIDTH = 400
HEIGHT = 400
TASK_TO_MODELS = {
    '-': ('-',),
    'Regression': (
        '-',
        'Bayesian Linear Regression',
        'Variational Bayesian Linear Regression'
    ),
    'Classification': (
        '-',
        'Bayesian Logistic Regression',
    )
}


@st.cache(allow_output_mutation=True)
def get_cache():
    return {'x': None, 'y': None, 'model': None, 'bg': None}


def get_fig_ax():
    plt.tight_layout()
    fig, ax = plt.subplots(
        subplot_kw={'xlim': (-1, 1), 'ylim': (-1, 1)})
    ax.grid(alpha=0.5)
    ax.tick_params(
        axis='x', which='both', bottom=False, top=False, labelbottom=False)
    ax.tick_params(
        axis='y', which='both', left=False, right=False, labelleft=False)
    return fig, ax


def figure_to_img(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=180, bbox_inches='tight', pad_inches=0)
    buf.seek(0)
    return Image.open(buf)


def get_background():
    cache = get_cache()
    if cache['bg'] is None:
        with RendererAgg.lock:
            fig, ax = get_fig_ax()
            cache['bg'] = figure_to_img(fig)
            plt.clf()
    return cache['bg']


def features_for_regression():
    features = []
    if st.checkbox('Bias', value=True):
        features.append(bs.preprocess.BiasFeature())
    if st.checkbox('Gaussian', value=True):
        num_locs = st.slider('Number of Gaussian kernels', 1, 10, 5)
        scales = list(map(lambda x: f'{x:.2E}', np.logspace(-1, 1, 100)))
        scale = float(st.select_slider(
            'Scale of Gaussian kernels', scales, scales[50]))
        features.extend([
            bs.preprocess.GaussianFeature([loc], scale) for loc
            in np.linspace(-1, 1, 2 * num_locs + 1)[1::2]
        ])
    if st.checkbox('Sigmoid', value=False):
        num_locs = st.slider('Number of sigmoid kernels', 1, 10, 5)
        scales = list(map(lambda x: f'{x:.2E}', np.logspace(0, 1, 100)))
        scale = float(st.select_slider(
            'Scale of sigmoid kernels', scales, scales[50]))
        features.extend([
            bs.preprocess.SigmoidalFeature([loc], scale) for loc
            in np.linspace(-1, 1, 2 * num_locs + 1)[1::2]
        ])
    if st.checkbox('Polynomial', value=False):
        degrees = st.multiselect(
            'Degrees', list(range(1, 10)), default=list(range(1, 10)))
        features.extend([
            bs.preprocess.PolynomialFeature(deg) for deg in degrees])
    return features


def features_for_classification():
    features = []
    if st.checkbox('Bias', value=True):
        features.append(bs.preprocess.BiasFeature())
    if st.checkbox('Gaussian', value=True):
        n = st.slider('Number of Gaussian kernels per axis', 1, 10, 5)
        scales = list(map(lambda x: f'{x:.2E}', np.logspace(-1, 1, 100)))
        scale = float(st.select_slider(
            'Scale of Gaussian kernels', scales, scales[50]))
        features.extend([
            bs.preprocess.GaussianFeature([x1, x2], scale) for x1, x2
            in product(
                np.linspace(-1, 1, 2 * n + 1)[1::2],
                np.linspace(-1, 1, 2 * n + 1)[1::2])
        ])
    if st.checkbox('Polynomial', value=False):
        degrees = st.multiselect(
            'Degrees', list(range(1, 10)), default=list(range(1, 10)))
        features.extend([
            bs.preprocess.PolynomialFeature(deg) for deg in degrees])
    return features


def bayesian_linear_regression(feature):
    alphas = list(map(lambda x: f'{x:.2E}', np.logspace(-6, 1, 100)))
    betas = list(map(lambda x: f'{x:.2E}', np.logspace(-1, 4, 100)))
    return bs.linear.Regression(
        alpha=float(st.select_slider('alpha', alphas, alphas[50])),
        beta=float(st.select_slider('beta', betas, betas[50])),
        feature=feature)


def variational_bayesian_linear_regression(feature):
    a0s = list(map(lambda x: f'{x:.2E}', np.logspace(-6, 1, 100)))
    b0s = list(map(lambda x: f'{x:.2E}', np.logspace(-6, 1, 100)))
    betas = list(map(lambda x: f'{x:.2E}', np.logspace(-1, 4, 100)))
    return bs.linear.VariationalRegression(
        a0=float(st.select_slider('a0', a0s, a0s[50])),
        b0=float(st.select_slider('b0', b0s, b0s[50])),
        beta=float(st.select_slider('beta', betas, betas[50])),
        feature=feature)


def bayesian_logistic_regression(feature):
    alphas = list(map(lambda x: f'{x:.2E}', np.logspace(-6, 2, 100)))
    return bs.linear.Classifier(
        alpha=float(st.select_slider('alpha', alphas, alphas[50])),
        feature=feature)


def get_xy_from_canvas(stroke_color: str, action: str, for_regression: bool):
    canvas = st_canvas(
        stroke_width=10, stroke_color=stroke_color, width=WIDTH, height=HEIGHT,
        background_image=get_background(), update_streamlit=True, key='canvas',
        drawing_mode='circle' if 'add' in action.lower() else 'transform')
    points = [p for p in canvas.json_data['objects'] if p['type'] == 'circle']
    x_train = [2 * p['left'] / WIDTH - 1 for p in points]
    y_train = [1 - 2 * p['top'] / HEIGHT for p in points]
    if not for_regression:
        x_train = [[x, y] for x, y in zip(x_train, y_train)]
        y_train = [int(p['stroke'] == 'yellow') for p in points]
    return x_train, y_train


def regression(model):
    action = st.selectbox('Action:', (
        'Click on the canvas to add data points',
        'Double click points to delete them',))
    x_train, y_train = get_xy_from_canvas('blue', action, True)
    cache = get_cache()
    if ((cache['model'] != model)
            or (cache['x'] != x_train)
            or (cache['y'] != y_train)):
        cache['x'] = x_train
        cache['y'] = y_train
        cache['model'] = model
        with RendererAgg.lock:
            fig, ax = get_fig_ax()
            if len(y_train) > 0:
                model.fit(x_train, y_train)
                cache['model'] = model
                x = np.linspace(-1, 1, 100)
                y, y_std = model.predict(x)
                ax.plot(x, y, c='C1')
                ax.fill_between(x, y - y_std, y + y_std, color='C1', alpha=0.2)
            cache['bg'] = figure_to_img(fig)
            plt.clf()
        st.experimental_rerun()


def classification(model):
    action = st.selectbox('Action:', (
        'Click to add positive data points',
        'Click to add negative data points',
        'Double click to delete data points',
    ))
    x_train, y_train = get_xy_from_canvas(
        'yellow' if 'positive' in action else 'purple', action, False)
    cache = get_cache()
    if ((cache['model'] != model)
            or (cache['x'] != x_train)
            or (cache['y'] != y_train)):
        cache['x'] = x_train
        cache['y'] = y_train
        cache['model'] = model
        with RendererAgg.lock:
            fig, ax = get_fig_ax()
            if len(y_train) > 0:
                model.fit(x_train, y_train)
                cache['model'] = model
                x = np.linspace(-1, 1, 100)
                x1, x2 = np.meshgrid(x, x)
                x = np.array([x1, x2]).reshape(2, -1).T
                y = model.proba(x)
                ax.contourf(x1, x2, y.reshape(100, 100), alpha=0.2)
            cache['bg'] = figure_to_img(fig)
            plt.clf()
        st.experimental_rerun()


if __name__ == "__main__":
    task = st.sidebar.selectbox('Select a task:', tuple(TASK_TO_MODELS.keys()))
    model = st.sidebar.selectbox('Select a model:', TASK_TO_MODELS[task])
    if model == '-':
        st.sidebar.info('Select a task and a model above.')
        st.title('Welcom to Bayesian model playground!')
        st.markdown(
            '**Select a task and a model from the dropdown on the left** '
            'to play around with Bayesian models interactively!')
    else:
        st.title(model)
        try:
            features = eval(f'features_for_{task.lower()}')
            task = eval(task.lower())
            model = eval(model.lower().replace(' ', '_'))
        except NameError:
            st.error('Not Implemented Error')
            st.stop()

        with st.sidebar.beta_expander('Features'):
            features = features()
        if len(features) == 0:
            st.error('Select at least one feature')
            st.stop()
        with st.sidebar.beta_expander('Hyperparameters'):
            model = model(bs.preprocess.StackedFeatures(*features))

        task(model)
        with st.beta_expander('See model explanation'):
            st.markdown(model.__doc__)
