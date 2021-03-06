"""Credit Scoring Dashboard App

Author: Etienne Lardeur https://github.com/EtienneLardeur
Source: https://github.com/EtienneLardeur/Streamlit_App
launch (local) with command line: streamlit run local_app.py

"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pickle
import urllib
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline
from lime.lime_tabular import LimeTabularExplainer
import shap

# warning on pyplot
st.set_option('deprecation.showPyplotGlobalUse', False)

# path & files to load
MODEL_SAV_FILE = "model.sav"
DESC_PKL_FILE = 'desc.pkl'
FINAL_PKL_FILE = 'final.pkl'
SHAP_EXP_FILE = 'shap.exp'
SHAP_VAL_FILE = 'shap.val'
GITHUB_ROOT = (
    "https://raw.githubusercontent.com/EtienneLardeur/Streamlit_App/main/"
)

# cache means unique function execution at start
# use pickle to load an object

def load_obj(file: str):
    """An instance of an object from the pickle file"""
    github_url = GITHUB_ROOT + file
    with urllib.request.urlopen(github_url) as open_file:  # type: ignore
        return pickle.load(open_file)

@st.cache(suppress_st_warning=True)
def bulk_init():
    
    def initialize_desc():
        # load
        df = load_obj(DESC_PKL_FILE)
        # create the list of features
        dflist = df['Feature'].tolist()
        return df, dflist
    
    desc, field_list = initialize_desc()
    
    def initialize_inputs():
        # load
        df = load_obj(FINAL_PKL_FILE)
        # transform
        inputsdf = df.drop(columns=['RISK_FLAG', 'RISK_PROBA'])
        id_list = df.index.tolist()
        return df, inputsdf, id_list
    
    final, inputs, sk_id_list = initialize_inputs()
    
    def initialize_model():
        # load
        mdl = load_obj(MODEL_SAV_FILE)
        # transform
        pipeline = make_pipeline(mdl)
        return pipeline
    
    pipe = initialize_model()
    
    def initialize_shap():
        # load
        shap_exp = load_obj(SHAP_EXP_FILE)
        shap_val = load_obj(SHAP_VAL_FILE)
        return shap_exp, shap_val
     
    shap_explainer, shap_values = initialize_shap()

    return desc, field_list, final, inputs, sk_id_list, pipe, shap_explainer, shap_values

desc, field_list, final, inputs, sk_id_list, pipe, shap_explainer, shap_values = bulk_init()

# function to apply threshold to positive probabilities to create labels
@st.cache
def to_labels(pos_probs, threshold):
    return (pos_probs >= threshold).astype('int')

# get native mofidiable predictions from "final" and store in a "result" df
@st.cache(allow_output_mutation=True)
def get_native_predictions(final):
    # native labels
    risk_flag = final['RISK_FLAG']
    # native proba
    risk_proba = final['RISK_PROBA']
    # return native failure rate 
    pred_good = (risk_flag == 0).sum()
    pred_fail = (risk_flag == 1).sum()
    failure_rate = round(pred_fail / (pred_good + pred_fail), 2)
    # create the first restults df
    results = final.copy()
    return results, failure_rate, risk_proba

# create original restults df & failure rate
results, failure_rate, risk_proba = get_native_predictions(final)
# features to show
features_to_show = []

# actualize predictions
@st.cache(allow_output_mutation=True)
def actualize_predictions(final, threshold):
    # unchanged native proba
    risk_proba = final['RISK_PROBA']
    # new predictions
    risk_flag = to_labels(risk_proba, threshold)
    # return new failure rate 
    pred_good = (risk_flag == 0).sum()
    pred_fail = (risk_flag == 1).sum()
    failure_rate = round(pred_fail / (pred_good + pred_fail), 2)
    # update results
    results['RISK_FLAG'] = risk_flag
    return results, failure_rate

st.write("""
# Credit scoring of client's applications
""")

# Sidebar ##################################################

st.sidebar.header('Inputs Panel')

### Sidebar - subsection Failure Rate Control ###
st.sidebar.subheader('- *Supervisor Only* Failure Rate Control')
st.sidebar.write('Initial Failure Rate', failure_rate)

def threshold_prediction_component():
    new_threshold = st.sidebar.slider(
        label='Threshold:',
        min_value=0.,
        value=0.5,
        max_value=1.)
    new_failure_rate = failure_rate
    results, new_failure_rate = actualize_predictions(
        final,
        new_threshold)
    st.sidebar.write('Current Failure Rate', new_failure_rate)
    return new_threshold

curr_threshold = threshold_prediction_component()

### Sidebar - subsection Client selection ###
st.sidebar.subheader('- Client selection')
def client_input_features():
    sk_id_curr = st.sidebar.selectbox('Please select Client ID', sk_id_list, 0)
    sk_row = results.loc[[sk_id_curr]]
    return sk_row, sk_id_curr

select_sk_row, select_sk_id = client_input_features()

### Sidebar - subsection tune ###
st.sidebar.subheader('- *tbd* Tune Application')


### Sidebar - subsection feature description ###

st.sidebar.subheader('- *tbc* Get full description of a feature')

def field_description():

    field = st.sidebar.selectbox('Please select a feature', field_list, 0)
    
    Description = desc[desc['Feature'] == field]['Description']
    pd.options.display.max_colwidth = len(Description)
    return Description

txt_field_desc = field_description()

st.sidebar.text(txt_field_desc)

# Main page ##################################################

st.subheader('- __*Demo only*__ Generate applications sample')

def application_samples_component():
    ''' display samples
    '''
    if st.button('Samples'):
        st.markdown('predicted __without__ difficulty to repay - sample')
        st.write(results[results['RISK_FLAG'] == 0].sample(3))
        st.markdown('predicted __with__ difficulty to repay - sample')
        st.write(results[results['RISK_FLAG'] == 1].sample(3))

application_samples_component()
    
st.subheader('Selected Client')

st.write(select_sk_row)

# SHAP section #################################################
st.subheader(' __*Experiment:*__ Generate SHAP explainer')

def shap_explaination(sk_id_curr):
    ''' compute and display explainer
    '''
    if st.button("Explain Results by SHAP"):
        with st.spinner('Calculating...'):
            st.write('__SH__apley __A__dditive ex__P__lanations provide an overview of how most important features impacts Class prediction')
            # st.write('*__Summary plot__ shows, considering __any application__, the distribution of features values colored by Class prediction*')
            st.write('*__Force plot__ shows, __depending on the ground data selected__, how opposite are the features strenghs*')
            st.write('*Green means feature value makes Default Risk lower while Red means feature value makes Default Risk higher*')
            # recover index position of sk_id_curr
            idx = inputs.index.get_loc(sk_id_curr)
            # create individual fig
            ind_fig = shap.force_plot(
                shap_explainer.expected_value[1],
                shap_values[1][idx],
                inputs.iloc[[idx]], plot_cmap="PkYg")
            ind_fig_html = f"<head>{shap.getjs()}</head><body>{ind_fig.html()}</body>"
            # create collective fig
            col_fig = shap.force_plot(
                shap_explainer.expected_value[1],
                shap_values[1][0,:],
                inputs.iloc[0,:], plot_cmap="PkYg")
            col_fig_html = f"<head>{shap.getjs()}</head><body>{col_fig.html()}</body>"
            # create 
            feat_fig = shap.force_plot(
                shap_explainer.expected_value[1],
                shap_values[1][:500,:],
                inputs.iloc[:500,:], plot_cmap="PkYg")
            feat_fig_html = f"<head>{shap.getjs()}</head><body>{feat_fig.html()}</body>"
            # Display the summary plot
            # st.write('__ - SHAP Summary plot of Class 1: Failure Risk__')
            # st.write('*Blue means negative impact to Risk while Red means positive impact*')
            # st.write('__*Red*__ means Class 1: Failure Risk')
            # st.write('__*Blue*__ means opposite')
            # shap.summary_plot(shap_values[1], inputs, show=False)
            # st.pyplot(bbox_inches='tight')
            # Display explainer HTML object col_fig
            st.write('__ - SHAP Force plot considering entire new Applications data (test)__')
            # st.write('*Green means feature value makes Risk lower while Red means feature value makes Risk higher*')
            components.html(col_fig_html, height=120)
            # Display explainer HTML object ind_fig
            st.write('__ - SHAP Force plot for the selected Application__')
            # st.write('*Green means feature value makes Risk lower while Red means feature value makes Risk higher*')
            components.html(ind_fig_html, height=120)
            # Display explainer HTML object feat_fig
            st.write('__ - SHAP Force plot to provide feature analysis along a sample of Applications (here 10% of test set)__')
            # st.write('*Green means feature value makes Risk lower while Red means feature value makes Risk higher*')
            components.html(feat_fig_html, height=350)

shap_explaination(select_sk_id)

# Lime section ################################################
st.subheader('__*Actionable:*__ Generate LIME explainer')
st.write('__ - L__ocal __I__nterpretable __M__odel-agnostic __E__xplanations:')

def lime_explaination(inputs, results, select_sk_id):
    ''' compute and display explainer
    '''
    st.write('*Please set the number of __features__ you want to analyse (LIME will grab most important first)*')
    nb_features = st.slider(
        label='Number of Features to analyse',
        min_value=7,
        value=10,
        max_value=15)
    st.write('*Please set the number of __similar applications__ you want to compare with (similarity according to most important features)*')
    nb_neighbors = st.slider(
        label='Number of similar applications to consider',
        min_value=10,
        value=20,
        max_value=50)
    
    if st.button("Explain Results by LIME"):
        with st.spinner('Calculating...'):
            lime_explainer = LimeTabularExplainer(
                training_data = inputs.values,
                mode='classification',
                training_labels = results[['RISK_FLAG']],
                feature_names = inputs.columns)
            exp = lime_explainer.explain_instance(
                inputs.loc[select_sk_id].values,
                pipe.predict_proba,
                num_features=nb_features)
            # introduce next step
            st.write('__ - LIME explaination for the selected Client:__')
            st.write('*Positive value __Red__ means __Support__ the Class 1: Failure Risk*')
            st.write('*Negative value __Green__ means __Contradict__ the Class 1: Failure Risk*')
            # Get features_to_show list
            id_cols = [item[0] for item in exp.as_map()[1]]
            # Create inputs restricted to the features_to_show
            df_lime = inputs.filter(
                inputs.columns[id_cols].tolist())
            # sk_id_row = df_lime.loc[[select_sk_id]]
            # compute inputs for plots
            exp_list= exp.as_list()
            vals = [x[1] for x in exp_list]
            names = [x[0] for x in exp_list]
            axisgb_colors = ['#fee0d2' if x > 0 else '#c7e9c0' for x in vals]
            vals.reverse()
            names.reverse()
            colors = ['red' if x > 0 else 'green' for x in vals]
            pos = np.arange(len(exp_list)) + .5
            # create tab plot
            tab = plt.figure()
            plt.barh(pos, vals, align='center', color=colors)
            plt.yticks(pos, names)
            plt.title('Local explanation for Class 1: Failure Risk')
            st.pyplot(tab)
            # st.write(sk_id_row)
            # find nb_neighbors nearest neighbors to catch anomaly
            nearest_neighbors = NearestNeighbors(
                n_neighbors=nb_neighbors,
                radius=0.4)
            nearest_neighbors.fit(df_lime)
            neighbors = nearest_neighbors.kneighbors(
                df_lime.loc[[select_sk_id]],
                nb_neighbors + 1,
                return_distance=False)[0]
            neighbors = np.delete(neighbors, 0)
            # compute values for neighbors, class0 and class1
            df_lime['RISK_FLAG'] = results['RISK_FLAG']
            neighbors_values = pd.DataFrame(
                df_lime.iloc[neighbors].mean(),
                index=df_lime.columns,
                columns=['Neighbors_Mean'])
            st.write('__- Neighbors Risk Flag averaged__',
                     neighbors_values.Neighbors_Mean.tail(1).values[0])
            st.write('*Nb. Neighborood __do not__ take Risk prediction values into account*')
            client_values = df_lime.loc[[select_sk_id]].T
            client_values.columns = ['Client_Value']
            class1_values = pd.DataFrame(
                df_lime[df_lime['RISK_FLAG'] == 1].mean(),
                index=df_lime.columns,
                columns=['Class_1_Mean'])
            class0_values = pd.DataFrame(
                df_lime[df_lime['RISK_FLAG'] == 0].mean(),
                index=df_lime.columns,
                columns=['Class_0_Mean'])
            any_values = pd.concat(
                [class0_values.iloc[:-1],
                 class1_values.iloc[:-1],
                 neighbors_values.iloc[:-1],
                 client_values],
                axis=1)
            colorsList = ('tab:green', 'tab:red', 'tab:cyan', 'tab:blue')
            fig, axs = plt.subplots(nb_features, sharey='row', figsize=(8, 4 * nb_features))
            for i in np.arange(0, nb_features):
                axs[i].barh(any_values.T.index,
                any_values.T.iloc[:, i],
                color=colorsList)
                axs[i].set_title(str(any_values.index[i]), fontweight="bold")
                axs[i].patch.set_facecolor(axisgb_colors[i])
            st.write('__ - Details of LIME explaination for each features: __')
            st.write('*Nb. You may compare Client value with mean of its Neighbors, Class 1 & Class 0*')
            st.write('*Colored lightred / lightgreen foreground is related to Class 1: Failure Risk Support / Contradict*')
            st.pyplot(fig)
            
lime_explaination(inputs, results, select_sk_id)

